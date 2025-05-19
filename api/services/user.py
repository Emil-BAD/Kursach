from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date
from sqlalchemy.sql import func
from api.db.database import get_db
from api.db.models import User, Dormitory, Room, Role, UserViolation
from api.schemas.user import PaginatedUserResponse, UserResponse, UserCreate, UserUpdate
from api.core.dependencies import get_current_admin
import hashlib
import json

router = APIRouter()


@router.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Проверка существования общежития
    if user.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Проверка существования комнаты
    if user.room_id:
        room = db.query(Room).filter(Room.id == user.room_id).first()
        if not room:
            raise HTTPException(status_code=400, detail="Комната с указанным ID не найдена")

    # Проверка существования роли
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")

    # Проверка уникальности студенческого билета
    if db.query(User).filter(User.student_card == user.student_card).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким номером студенческого билета уже существует")

    # Простое хеширование пароля (замени на реальный метод, например, bcrypt)
    password_hash = hashlib.sha256(user.student_card.encode() + "salt".encode()).hexdigest()  # Пример, не используй в продакшене без нормального хеширования

    # Создание нового пользователя
    db_user = User(
        student_card=user.student_card,
        password_hash=password_hash,
        full_name=user.full_name,
        contact_number=user.contact_number,
        dormitory_id=user.dormitory_id,
        room_id=user.room_id,
        group_number=user.group_number,
        specialization=user.specialization,
        role_id=user.role_id,
        email=user.email,
        phone=user.phone,
        birth_date=user.birth_date,
        course=user.course,
        faculty=user.faculty,
        social_links=user.social_links
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Инициализация начальных баллов
    current_points = {"total": 100}
    db_user.points = current_points

    # Сохранение изменений
    db.commit()

    # Получение связанных данных
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_user.dormitory_id).first() if db_user.dormitory_id else None
    room = db.query(Room).filter(Room.id == db_user.room_id).first() if db_user.room_id else None
    role = db.query(Role).filter(Role.id == db_user.role_id).first()

    # Подсчет начальных нарушений и активности (на момент создания пусто)
    total_penalty = 0  # Нет нарушений при создании
    current_points = {"total": max(0, 100 - total_penalty)}
    db_user.points = current_points
    db.commit()

    # Формирование ответа
    return UserResponse(
        id=db_user.id,
        student_card=db_user.student_card,
        full_name=db_user.full_name,
        contact_number=db_user.contact_number,
        dormitory_id=db_user.dormitory_id,
        dormitory_name=dormitory.name if dormitory else None,
        room_id=db_user.room_id,
        room_number=room.room_number if room else None,
        group_number=db_user.group_number,
        specialization=db_user.specialization,
        role_id=db_user.role_id,
        role_name=role.role_name if role else "Unknown",
        email=db_user.email,
        phone=db_user.phone,
        birth_date=db_user.birth_date,
        course=db_user.course,
        faculty=db_user.faculty,
        created_at=db_user.created_at,
        points=current_points,
        social_links=db_user.social_links,
        violations=[],  # Пустой список при создании
        room_violation_frequency=0,  # Начальное значение
        activities=[]  # Пустой список при создании
    )


@router.get("/users", response_model=PaginatedUserResponse)
def get_users(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    skip = (page - 1) * size
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(size).all()

    user_responses = []
    for user in users:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user.dormitory_id).first() if user.dormitory_id else None
        room = db.query(Room).filter(Room.id == user.room_id).first() if user.room_id else None
        role = db.query(Role).filter(Role.id == user.role_id).first()

        total_penalty = db.query(UserViolation).filter(UserViolation.user_id == user.id).with_entities(func.sum(UserViolation.penalty_points)).scalar() or 0
        current_points = {"total": max(0, 100 - total_penalty)}

        user_responses.append(
            UserResponse(
                id=user.id,
                student_card=user.student_card,
                full_name=user.full_name,
                contact_number=user.contact_number,
                dormitory_id=user.dormitory_id,
                dormitory_name=dormitory.name if dormitory else None,
                room_id=user.room_id,  # Может быть None
                room_number=room.room_number if room else None,  # Проверяем, есть ли room
                group_number=user.group_number,
                specialization=user.specialization,
                role_id=user.role_id,
                role_name=role.role_name if role else "Unknown",
                email=user.email,
                phone=user.phone,
                birth_date=user.birth_date,
                course=user.course,
                faculty=user.faculty,
                created_at=user.created_at,
                points=current_points,
                social_links=user.social_links
            )
        )

    total_pages = (total + size - 1) // size

    return PaginatedUserResponse(
        items=user_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    full_name: Optional[str] = Form(None),
    contact_number: Optional[int] = Form(None),
    dormitory_id: Optional[int] = Form(None),
    room_id: Optional[int] = Form(None),
    group_number: Optional[int] = Form(None),
    specialization: Optional[str] = Form(None),
    role_id: Optional[int] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    course: Optional[int] = Form(None),
    faculty: Optional[str] = Form(None),
    social_links_tg: Optional[str] = Form(None, alias="social_links[tg]"),  # Псевдоним для social_links[tg]
    social_links_vk: Optional[str] = Form(None, alias="social_links[vk]"),  # Псевдоним для social_links[vk]
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверка существования роли
    if role_id is not None:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")

    # Проверка существования общежития
    if dormitory_id is not None:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Проверка существования комнаты
    if room_id is not None:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=400, detail="Комната с указанным ID не найдена")

    # Обновление полей
    if full_name is not None:
        db_user.full_name = full_name
    if contact_number is not None:
        db_user.contact_number = contact_number
    if dormitory_id is not None:
        db_user.dormitory_id = dormitory_id
    if room_id is not None:
        db_user.room_id = room_id
    if group_number is not None:
        db_user.group_number = group_number
    if specialization is not None:
        db_user.specialization = specialization
    if role_id is not None:
        db_user.role_id = role_id
    if email is not None:
        db_user.email = email
    if phone is not None:
        db_user.phone = phone
    if birth_date is not None:
        try:
            db_user.birth_date = date.fromisoformat(birth_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте ISO формат (например, 2000-05-15)")
    if course is not None:
        db_user.course = course
    if faculty is not None:
        db_user.faculty = faculty

    # Обновление social_links
    social_links_dict = db_user.social_links or {}
    if social_links_tg is not None:
        social_links_dict["tg"] = social_links_tg
    if social_links_vk is not None:
        social_links_dict["vk"] = social_links_vk
    if social_links_tg is not None or social_links_vk is not None:
        db_user.social_links = social_links_dict

    # Обновление всех товаров пользователя
    if social_links_tg is not None or social_links_vk is not None:
        products = db.query(Product).filter(Product.seller_id == user_id).all()
        for product in products:
            product.seller_telegram = social_links_dict.get("tg")
            product.seller_vk = social_links_dict.get("vk")
        db.commit()

    db.commit()
    db.refresh(db_user)

    # Пересчёт баллов
    total_penalty = db.query(UserViolation).filter(UserViolation.user_id == db_user.id).with_entities(func.sum(UserViolation.penalty_points)).scalar() or 0
    current_points = {"total": max(0, 100 - total_penalty)}
    db_user.points = current_points
    db.commit()

    # Формирование ответа
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_user.dormitory_id).first() if db_user.dormitory_id else None
    room = db.query(Room).filter(Room.id == db_user.room_id).first() if db_user.room_id else None
    role = db.query(Role).filter(Role.id == db_user.role_id).first()

    return UserResponse(
        id=db_user.id,
        student_card=db_user.student_card,
        full_name=db_user.full_name,
        contact_number=db_user.contact_number,
        dormitory_id=db_user.dormitory_id,
        dormitory_name=dormitory.name if dormitory else None,
        room_id=db_user.room_id,
        room_number=room.room_number if room else None,
        group_number=db_user.group_number,
        specialization=db_user.specialization,
        role_id=db_user.role_id,
        role_name=role.role_name if role else "Unknown",
        email=db_user.email,
        phone=db_user.phone,
        birth_date=db_user.birth_date,
        course=db_user.course,
        faculty=db_user.faculty,
        created_at=db_user.created_at,
        points=current_points,
        social_links=db_user.social_links,
        violations=[],
        room_violation_frequency=0,
        activities=[]
    )


@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Поиск пользователя
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Удаление пользователя (связанные записи удалятся автоматически)
    db.delete(db_user)
    db.commit()

    return {"message": f"Пользователь с ID {user_id} успешно удалён"}
