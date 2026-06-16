from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import Event, EventRegistration, User
from api.schemas.event import (
    EventRegistrationCreate,
    EventRegistrationResponse,
    EventRegistrationUpdate,
    PaginatedEventRegistrationResponse,
)
from api.services.user_helpers import can_manage_events, is_admin

router = APIRouter()


def _get_registration_or_404(db: Session, registration_id: int) -> EventRegistration:
    registration = (
        db.query(EventRegistration)
        .options(joinedload(EventRegistration.event), joinedload(EventRegistration.user))
        .filter(EventRegistration.id == registration_id)
        .first()
    )
    if not registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена")
    return registration


def _build_registration_response(registration: EventRegistration, message: str | None = None) -> EventRegistrationResponse:
    return EventRegistrationResponse(
        id=registration.id,
        event_id=registration.event_id,
        event_title=registration.event.title if registration.event else "Unknown",
        user_id=registration.user_id,
        user_name=registration.user.full_name if registration.user else "Unknown",
        status=registration.status,
        registered_at=registration.registered_at,
        message=message,
    )


@router.post("/event-registrations", response_model=EventRegistrationResponse)
def register_for_event(
    registration: EventRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Зарегистрироваться на мероприятие.
    """
    event = db.query(Event).filter(Event.id == registration.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    if event.status != "open":
        raise HTTPException(status_code=400, detail="Мероприятие закрыто для регистрации")

    existing = (
        db.query(EventRegistration)
        .filter(
            EventRegistration.event_id == registration.event_id,
            EventRegistration.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Вы уже зарегистрированы на это мероприятие")

    db_registration = EventRegistration(
        event_id=registration.event_id,
        user_id=current_user.id,
        status="pending",
    )
    db.add(db_registration)
    db.commit()

    created = _get_registration_or_404(db, db_registration.id)
    return _build_registration_response(created, "Регистрация на мероприятие успешно выполнена")


@router.get("/event-registrations", response_model=PaginatedEventRegistrationResponse)
def get_event_registrations(
    page: int = 1,
    size: int = 10,
    event_id: int = None,
    user_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список регистраций на мероприятия.
    """
    skip = (page - 1) * size
    query = db.query(EventRegistration).options(
        joinedload(EventRegistration.event),
        joinedload(EventRegistration.user),
    )

    if event_id:
        query = query.filter(EventRegistration.event_id == event_id)
    if user_id:
        query = query.filter(EventRegistration.user_id == user_id)
    if status:
        query = query.filter(EventRegistration.status == status)

    if not any([is_admin(current_user), can_manage_events(current_user)]):
        query = query.filter(EventRegistration.user_id == current_user.id)
    elif event_id and not is_admin(current_user):
        event = db.query(Event).filter(Event.id == event_id).first()
        if event and event.organizer_id != current_user.id:
            query = query.filter(EventRegistration.user_id == current_user.id)

    total = query.count()
    registrations = (
        query.order_by(EventRegistration.registered_at.desc(), EventRegistration.id.desc())
        .offset(skip)
        .limit(size)
        .all()
    )

    return PaginatedEventRegistrationResponse(
        items=[_build_registration_response(item) for item in registrations],
        total=total,
        page=page,
        size=size,
        total_pages=(total + size - 1) // size,
    )


@router.put("/event-registrations/{registration_id}", response_model=EventRegistrationResponse)
def update_event_registration(
    registration_id: int,
    registration_update: EventRegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить статус регистрации на мероприятие.
    """
    db_registration = _get_registration_or_404(db, registration_id)
    event = db_registration.event

    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    if current_user.id != event.organizer_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Недостаточно прав для модерации регистрации")
    if event.status != "open":
        raise HTTPException(status_code=400, detail="Мероприятие закрыто для изменений")

    db_registration.status = registration_update.status
    db.commit()

    updated = _get_registration_or_404(db, db_registration.id)
    return _build_registration_response(updated, f"Статус регистрации обновлён на {updated.status}")


@router.delete("/event-registrations/{registration_id}", response_model=dict)
def delete_event_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отменить регистрацию на мероприятие.
    """
    db_registration = _get_registration_or_404(db, registration_id)
    event = db_registration.event

    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    if db_registration.user_id != current_user.id and not is_admin(current_user) and event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления регистрации")

    db.delete(db_registration)
    db.commit()
    return {"message": "Регистрация успешно удалена", "registration_id": registration_id}
