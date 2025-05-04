from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from api.db.database import get_db
from api.db.models import Event, User, Category, Dormitory
from api.schemas.event import PaginatedEventResponse, EventCreate, EventUpdate
from api.core.dependencies import get_current_admin

router = APIRouter()

@router.get("/events", response_model=PaginatedEventResponse)
def get_events(
    page: int = 1,
    size: int = 10,
    category_id: int = None,
    dormitory_id: int = None,
    is_private: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    skip = (page - 1) * size
    query = db.query(Event)

    if category_id:
        query = query.filter(Event.category_id == category_id)
    if dormitory_id:
        query = query.filter(Event.dormitory_id == dormitory_id)
    if is_private is not None:
        query = query.filter(Event.is_private == is_private)

    total = query.count()
    events = query.offset(skip).limit(size).all()

    event_responses = []
    for event in events:
        category = db.query(Category).filter(Category.id == event.category_id).first()
        dormitory = db.query(Dormitory).filter(Dormitory.id == event.dormitory_id).first() if event.dormitory_id else None
        organizer = db.query(User).filter(User.id == event.organizer_id).first()

        event_responses.append(
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_date": event.event_date,
                "location": event.location,
                "created_at": event.created_at,
                "organizer_id": event.organizer_id,
                "organizer_name": organizer.full_name if organizer else "Unknown",
                "image_urls": event.image_urls,
                "category_id": event.category_id,
                "category_name": category.name if category else "Unknown",
                "status": event.status,
                "dormitory_id": event.dormitory_id,
                "dormitory_name": dormitory.name if dormitory else None,
                "is_private": event.is_private
            }
        )

    total_pages = (total + size - 1) // size

    return PaginatedEventResponse(
        items=event_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.post("/events", response_model=dict)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Проверка существования категории
    category = db.query(Category).filter(Category.id == event.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития (если указано)
    if event.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == event.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Создание нового мероприятия
    db_event = Event(
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        location=event.location,
        organizer_id=current_user.id,  # Организатор — текущий авторизованный пользователь
        image_urls=event.image_urls,
        category_id=event.category_id,
        dormitory_id=event.dormitory_id,
        status=event.status,
        is_private=event.is_private
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    category = db.query(Category).filter(Category.id == db_event.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_event.dormitory_id).first() if db_event.dormitory_id else None
    organizer = db.query(User).filter(User.id == db_event.organizer_id).first()

    return {
        "id": db_event.id,
        "title": db_event.title,
        "description": db_event.description,
        "event_date": db_event.event_date,
        "location": db_event.location,
        "created_at": db_event.created_at,
        "organizer_id": db_event.organizer_id,
        "organizer_name": organizer.full_name if organizer else "Unknown",
        "image_urls": db_event.image_urls,
        "category_id": db_event.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_event.status,
        "dormitory_id": db_event.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_event.is_private,
        "message": "Мероприятие успешно создано"
    }

@router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка прав: только организатор или администратор может редактировать
    if db_event.organizer_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования")

    # Проверка существования категории
    if event_update.category_id:
        category = db.query(Category).filter(Category.id == event_update.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития (если указано)
    if event_update.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == event_update.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Обновление полей
    for key, value in event_update.dict(exclude_unset=True).items():
        setattr(db_event, key, value)

    db.commit()
    db.refresh(db_event)

    category = db.query(Category).filter(Category.id == db_event.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_event.dormitory_id).first() if db_event.dormitory_id else None
    organizer = db.query(User).filter(User.id == db_event.organizer_id).first()

    return {
        "id": db_event.id,
        "title": db_event.title,
        "description": db_event.description,
        "event_date": db_event.event_date,
        "location": db_event.location,
        "created_at": db_event.created_at,
        "organizer_id": db_event.organizer_id,
        "organizer_name": organizer.full_name if organizer else "Unknown",
        "image_urls": db_event.image_urls,
        "category_id": db_event.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_event.status,
        "dormitory_id": db_event.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_event.is_private,
        "message": "Мероприятие успешно обновлено"
    }

@router.delete("/events/{event_id}", response_model=dict)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка прав: только организатор или администратор может удалять
    if db_event.organizer_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления")

    db.delete(db_event)
    db.commit()

    return {"message": "Мероприятие успешно удалено", "event_id": event_id}