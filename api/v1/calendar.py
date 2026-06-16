import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.core.exceptions import APIException, InternalServerError
from api.db.database import get_db
from api.db.models import User
from api.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CancelCalendarEventRequest,
    DormitoryBlockCreate,
    DormitoryBlockRoomBindRequest,
    DormitoryBlockRoomUpdateRequest,
    DormitoryBlockUpdate,
    KitchenDutyPlanCreate,
)
from api.services.calendar_service import CalendarService


router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])
logger = logging.getLogger(__name__)


@router.get("", response_model=dict)
def list_calendar_events(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    event_kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    dormitory_id: int | None = Query(default=None),
    block_id: int | None = Query(default=None),
    room_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).list_events(
            current_user=current_user,
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            event_kind=event_kind,
            status=status,
            scope_type=scope_type,
            dormitory_id=dormitory_id,
            block_id=block_id,
            room_id=room_id,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while listing calendar events")
        raise InternalServerError()


@router.get("/month", response_model=dict)
def get_calendar_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).get_month_view(
            current_user=current_user,
            year=year,
            month=month,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting calendar month view year=%s month=%s", year, month)
        raise InternalServerError()


@router.get("/my-duty", response_model=dict)
def get_my_duty(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).get_my_duty(
            current_user=current_user,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting my duty")
        raise InternalServerError()


@router.post("/events", response_model=dict)
def create_calendar_event(
    payload: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).create_event(current_user=current_user, data=payload)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating calendar event by user_id=%s", current_user.id)
        raise InternalServerError()


@router.patch("/events/{event_id}", response_model=dict)
def update_calendar_event(
    event_id: int,
    payload: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).update_event(
            current_user=current_user,
            event_id=event_id,
            data=payload,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while updating calendar event event_id=%s", event_id)
        raise InternalServerError()


@router.post("/events/{event_id}/cancel", response_model=dict)
def cancel_calendar_event(
    event_id: int,
    payload: CancelCalendarEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).cancel_event(
            current_user=current_user,
            event_id=event_id,
            reason=payload.reason,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while cancelling calendar event event_id=%s", event_id)
        raise InternalServerError()


@router.get("/blocks", response_model=dict)
def list_dormitory_blocks(
    dormitory_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).list_blocks(
            current_user=current_user,
            dormitory_id=dormitory_id,
            is_active=is_active,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while listing dormitory blocks")
        raise InternalServerError()


@router.post("/blocks", response_model=dict)
def create_dormitory_block(
    payload: DormitoryBlockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).create_block(current_user=current_user, data=payload)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating dormitory block")
        raise InternalServerError()


@router.patch("/blocks/{block_id}", response_model=dict)
def update_dormitory_block(
    block_id: int,
    payload: DormitoryBlockUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).update_block(
            current_user=current_user,
            block_id=block_id,
            data=payload,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while updating dormitory block block_id=%s", block_id)
        raise InternalServerError()


@router.post("/blocks/{block_id}/rooms", response_model=dict)
def bind_room_to_block(
    block_id: int,
    payload: DormitoryBlockRoomBindRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).add_room_to_block(
            current_user=current_user,
            block_id=block_id,
            room_id=payload.room_id,
            rotation_order=payload.rotation_order,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while binding room to block block_id=%s room_id=%s", block_id, payload.room_id)
        raise InternalServerError()


@router.patch("/blocks/{block_id}/rooms/{room_id}", response_model=dict)
def update_room_binding(
    block_id: int,
    room_id: int,
    payload: DormitoryBlockRoomUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).update_block_room(
            current_user=current_user,
            block_id=block_id,
            room_id=room_id,
            rotation_order=payload.rotation_order,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while updating room binding block_id=%s room_id=%s", block_id, room_id)
        raise InternalServerError()


@router.delete("/blocks/{block_id}/rooms/{room_id}", response_model=dict)
def remove_room_binding(
    block_id: int,
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).remove_room_from_block(
            current_user=current_user,
            block_id=block_id,
            room_id=room_id,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while removing room binding block_id=%s room_id=%s", block_id, room_id)
        raise InternalServerError()


@router.post("/duty-plans", response_model=dict)
def create_kitchen_duty_plan(
    payload: KitchenDutyPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).create_duty_plan(current_user=current_user, data=payload)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating kitchen duty plan")
        raise InternalServerError()


@router.post("/duty-plans/{plan_id}/generate", response_model=dict)
def generate_kitchen_duty_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).generate_duty_plan(current_user=current_user, plan_id=plan_id)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while generating kitchen duty plan plan_id=%s", plan_id)
        raise InternalServerError()


@router.get("/duty-plans", response_model=dict)
def list_kitchen_duty_plans(
    dormitory_id: int | None = Query(default=None),
    block_id: int | None = Query(default=None),
    month: date | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).list_duty_plans(
            current_user=current_user,
            dormitory_id=dormitory_id,
            block_id=block_id,
            month=month,
            status=status,
        )
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while listing kitchen duty plans")
        raise InternalServerError()


@router.get("/duty-plans/{plan_id}", response_model=dict)
def get_kitchen_duty_plan_detail(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).get_duty_plan_detail(current_user=current_user, plan_id=plan_id)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting kitchen duty plan detail plan_id=%s", plan_id)
        raise InternalServerError()


@router.post("/duty-plans/{plan_id}/cancel", response_model=dict)
def cancel_kitchen_duty_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).cancel_duty_plan(current_user=current_user, plan_id=plan_id)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while cancelling kitchen duty plan plan_id=%s", plan_id)
        raise InternalServerError()


@router.get("/{event_id}", response_model=dict)
def get_calendar_event_detail(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CalendarService(db).get_event_detail(current_user=current_user, event_id=event_id)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting calendar event detail event_id=%s", event_id)
        raise InternalServerError()
