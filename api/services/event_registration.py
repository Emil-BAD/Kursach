from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from api.db.database import get_db
from api.db.models import EventRegistration, Event, User
from api.schemas.event import EventRegistrationCreate, EventRegistrationResponse, PaginatedEventRegistrationResponse, EventRegistrationUpdate
from api.core.dependencies import get_current_user, get_current_admin

router = APIRouter()

@router.post("/event-registrations", response_model=EventRegistrationResponse)
def register_for_event(
    registration: EventRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка существования мероприятия
    event = db.query(Event).filter(Event.id == registration.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка статуса мероприятия
    if event.status != "open":
        raise HTTPException(status_code=400, detail="Мероприятие закрыто для регистрации")

    # Проверка, не зарегистрирован ли пользователь уже
    existing_registration = db.query(EventRegistration).filter(
        EventRegistration.event_id == registration.event_id,
        EventRegistration.user_id == current_user.id
    ).first()
    if existing_registration:
        raise HTTPException(status_code=400, detail="Вы уже зарегистрированы на это мероприятие")

    # Создание новой регистрации
    db_registration = EventRegistration(
        event_id=registration.event_id,
        user_id=current_user.id,
        status="pending"
    )
    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)

    event = db.query(Event).filter(Event.id == db_registration.event_id).first()
    user = db.query(User).filter(User.id == db_registration.user_id).first()

    return {
        "id": db_registration.id,
        "event_id": db_registration.event_id,
        "event_title": event.title,
        "user_id": db_registration.user_id,
        "user_name": user.full_name,
        "status": db_registration.status,
        "registered_at": db_registration.registered_at,
        "message": "Регистрация на мероприятие успешно выполнена"
    }

@router.get("/event-registrations", response_model=PaginatedEventRegistrationResponse)
def get_event_registrations(
    page: int = 1,
    size: int = 10,
    event_id: int = None,
    user_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    skip = (page - 1) * size
    query = db.query(EventRegistration)

    if event_id:
        query = query.filter(EventRegistration.event_id == event_id)
    if user_id:
        query = query.filter(EventRegistration.user_id == user_id)
    if status:
        query = query.filter(EventRegistration.status == status)

    # Доступ: администраторы, члены совета или организатор мероприятия
    if current_user.role_id not in [1, 2, 3]:  # Administrator, CouncilPresident, CouncilMember
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event or event.organizer_id != current_user.id:
                raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра регистраций")
        else:
            raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра регистраций")

    total = query.count()
    registrations = query.offset(skip).limit(size).all()

    registration_responses = []
    for reg in registrations:
        event = db.query(Event).filter(Event.id == reg.event_id).first()
        user = db.query(User).filter(User.id == reg.user_id).first()
        registration_responses.append(
            {
                "id": reg.id,
                "event_id": reg.event_id,
                "event_title": event.title if event else "Unknown",
                "user_id": reg.user_id,
                "user_name": user.full_name if user else "Unknown",
                "status": reg.status,
                "registered_at": reg.registered_at
            }
        )

    total_pages = (total + size - 1) // size

    return PaginatedEventRegistrationResponse(
        items=registration_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.put("/event-registrations/{registration_id}", response_model=EventRegistrationResponse)
def update_event_registration(
    registration_id: int,
    registration_update: EventRegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_registration = db.query(EventRegistration).filter(EventRegistration.id == registration_id).first()
    if not db_registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена")

    event = db.query(Event).filter(Event.id == db_registration.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка прав: только администратор или организатор мероприятия может модерировать
    if current_user.role_id != 1 and event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для модерации регистрации")

    # Проверка статуса мероприятия
    if event.status != "open":
        raise HTTPException(status_code=400, detail="Мероприятие закрыто для изменений")

    # Обновление статуса регистрации
    db_registration.status = registration_update.status
    db.commit()
    db.refresh(db_registration)

    user = db.query(User).filter(User.id == db_registration.user_id).first()

    return {
        "id": db_registration.id,
        "event_id": db_registration.event_id,
        "event_title": event.title,
        "user_id": db_registration.user_id,
        "user_name": user.full_name if user else "Unknown",
        "status": db_registration.status,
        "registered_at": db_registration.registered_at,
        "message": f"Статус регистрации обновлён на {db_registration.status}"
    }

@router.delete("/event-registrations/{registration_id}", response_model=dict)
def delete_event_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_registration = db.query(EventRegistration).filter(EventRegistration.id == registration_id).first()
    if not db_registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена")

    event = db.query(Event).filter(Event.id == db_registration.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка прав: пользователь может удалить свою регистрацию, администратор или организатор — любую
    if db_registration.user_id != current_user.id and current_user.role_id != 1 and event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления регистрации")

    db.delete(db_registration)
    db.commit()

    return {"message": "Регистрация успешно удалена", "registration_id": registration_id}