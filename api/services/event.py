# api/services/event.py
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from api.db.database import get_db
from api.db.models import Event, User, Category, Dormitory
from api.schemas.event import PaginatedEventResponse, EventResponse
from api.core.dependencies import get_current_admin, get_current_user
import cloudinary.uploader

router = APIRouter()

@router.get("/events", response_model=PaginatedEventResponse)
def get_events(
    page: int = 1,
    size: int = 10,
    category_id: int = None,
    dormitory_id: int = None,
    is_private: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
                "is_private": event.is_private,
                "requirements": event.requirements
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
    title: str = Form(...),
    description: str = Form(...),
    event_date: str = Form(...),  # Принимаем как строку, конвертируем в datetime
    location: str = Form(...),
    category_id: int = Form(...),
    dormitory_id: Optional[int] = Form(None),
    status: str = Form("open"),
    is_private: bool = Form(False),
    requirements: Optional[str] = Form(None),
    image_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from datetime import datetime
    try:
        event_date_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте ISO формат (например, 2025-05-15T12:00:00)")

    # Проверка существования категории
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития (если указано)
    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Загрузка изображений в Cloudinary
    image_urls = {}
    if image_files:
        for i, file in enumerate(image_files):
            if file and file.filename:
                try:
                    response = cloudinary.uploader.upload(
                        file.file,
                        folder="events",
                        resource_type="image",
                        public_id=f"event_{category_id}_{i+1}"
                    )
                    image_urls[f"image_{i+1}"] = response["secure_url"]
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")

    # Создание нового мероприятия
    db_event = Event(
        title=title,
        description=description,
        event_date=event_date_dt,
        location=location,
        organizer_id=current_user.id,
        image_urls=image_urls if image_urls else None,
        category_id=category_id,
        dormitory_id=dormitory_id,
        status=status,
        is_private=is_private,
        requirements=requirements
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
        "requirements": db_event.requirements,
        "message": "Мероприятие успешно создано"
    }

@router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    event_date: Optional[str] = Form(None),  # Принимаем как строку, конвертируем в datetime
    location: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    dormitory_id: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    is_private: Optional[bool] = Form(None),
    requirements: Optional[str] = Form(None),
    image_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    from datetime import datetime

    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка прав: только организатор или администратор может редактировать
    if db_event.organizer_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования")

    # Проверка существования категории
    if category_id:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития (если указано)
    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Обновление полей
    if title is not None:
        db_event.title = title
    if description is not None:
        db_event.description = description
    if event_date is not None:
        try:
            event_date_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            db_event.event_date = event_date_dt
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте ISO формат (например, 2025-05-15T12:00:00)")
    if location is not None:
        db_event.location = location
    if category_id is not None:
        db_event.category_id = category_id
    if dormitory_id is not None:
        db_event.dormitory_id = dormitory_id
    if status is not None:
        db_event.status = status
    if is_private is not None:
        db_event.is_private = is_private
    if requirements is not None:
        db_event.requirements = requirements

    # Загрузка новых изображений
    if image_files:
        image_urls = db_event.image_urls or {}
        for i, file in enumerate(image_files, len(image_urls) + 1):
            if file and file.filename:
                try:
                    response = cloudinary.uploader.upload(
                        file.file,
                        folder="events",
                        resource_type="image",
                        public_id=f"event_{db_event.id}_image_{i}"
                    )
                    image_urls[f"image_{i}"] = response["secure_url"]
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")
        db_event.image_urls = image_urls

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
        "requirements": db_event.requirements,
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