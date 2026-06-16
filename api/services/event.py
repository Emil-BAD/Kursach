from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import Category, Dormitory, Event, User
from api.schemas.event import EventCreate, EventResponse, EventUpdate, PaginatedEventResponse
from api.services.calendar_content_sync_service import CalendarContentSyncService
from api.services.user_helpers import can_manage_events, is_admin

router = APIRouter()


def _get_event_or_404(db: Session, event_id: int) -> Event:
    event = (
        db.query(Event)
        .options(joinedload(Event.organizer), joinedload(Event.category), joinedload(Event.dormitory))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return event


def _build_event_response(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_date": event.event_date,
        "location": event.location,
        "created_at": event.created_at,
        "organizer_id": event.organizer_id,
        "organizer_name": event.organizer.full_name if event.organizer else "Unknown",
        "category_id": event.category_id,
        "category_name": event.category.name if event.category else "Unknown",
        "status": event.status,
        "dormitory_id": event.dormitory_id,
        "dormitory_name": event.dormitory.name if event.dormitory else None,
        "is_private": event.is_private,
        "requirements": event.requirements,
    }


@router.get("/events", response_model=PaginatedEventResponse)
def get_events(
    page: int = 1,
    size: int = 10,
    category_id: int = None,
    dormitory_id: int = None,
    is_private: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список мероприятий.
    """
    skip = (page - 1) * size
    query = db.query(Event).options(
        joinedload(Event.organizer),
        joinedload(Event.category),
        joinedload(Event.dormitory),
    )

    if category_id:
        query = query.filter(Event.category_id == category_id)
    if dormitory_id:
        query = query.filter(Event.dormitory_id == dormitory_id)
    if is_private is not None:
        query = query.filter(Event.is_private == is_private)
    if not is_admin(current_user):
        query = query.filter(Event.is_private.is_(False))

    total = query.count()
    events = (
        query.order_by(Event.event_date.desc(), Event.id.desc())
        .offset(skip)
        .limit(size)
        .all()
    )

    return PaginatedEventResponse(
        items=[_build_event_response(event) for event in events],
        total=total,
        page=page,
        size=size,
        total_pages=(total + size - 1) // size,
    )


@router.post("/events", response_model=dict)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать мероприятие.
    """
    if not can_manage_events(current_user):
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания мероприятия")

    category = db.query(Category).filter(Category.id == event.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    if event.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == event.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    db_event = Event(
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        location=event.location,
        organizer_id=current_user.id,
        category_id=event.category_id,
        dormitory_id=event.dormitory_id,
        status=event.status,
        is_private=event.is_private,
        requirements=event.requirements,
    )
    try:
        db.add(db_event)
        db.flush()
        CalendarContentSyncService(db).sync_event(db_event, actor_id=current_user.id)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании мероприятия")

    created_event = _get_event_or_404(db, db_event.id)
    return {**_build_event_response(created_event), "message": "Мероприятие успешно создано"}


@router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: int,
    event: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить мероприятие.
    """
    db_event = _get_event_or_404(db, event_id)
    if db_event.organizer_id != current_user.id and not can_manage_events(current_user):
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования")

    if event.category_id:
        category = db.query(Category).filter(Category.id == event.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    if event.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == event.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    for field_name, value in event.model_dump(exclude_unset=True).items():
        setattr(db_event, field_name, value)

    try:
        CalendarContentSyncService(db).sync_event(db_event, actor_id=current_user.id)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновлении мероприятия")
    updated_event = _get_event_or_404(db, db_event.id)
    return {**_build_event_response(updated_event), "message": "Мероприятие успешно обновлено"}


@router.delete("/events/{event_id}", response_model=dict)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить мероприятие.
    """
    db_event = _get_event_or_404(db, event_id)
    if db_event.organizer_id != current_user.id and not can_manage_events(current_user):
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления")

    try:
        CalendarContentSyncService(db).remove_event_calendar_projection(db_event.id)
        db.delete(db_event)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при удалении мероприятия")
    return {"message": "Мероприятие успешно удалено", "event_id": event_id}
