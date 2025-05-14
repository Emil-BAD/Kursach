# api/services/user.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.sql import func
from api.db.database import get_db
from api.db.models import User, Dormitory, Room, Role, UserViolation
from api.schemas.user import PaginatedUserResponse, UserResponse, UserUpdate
from api.core.dependencies import get_current_admin

router = APIRouter()

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

        # Расчёт текущих баллов на основе нарушений
        total_penalty = db.query(UserViolation).filter(UserViolation.user_id == user.id).with_entities(func.sum(UserViolation.penalty_points)).scalar() or 0
        current_points = {"total": max(0, 100 - total_penalty)}  # Пример: начальные 100 баллов минус штрафы

        user_responses.append(
            UserResponse(
                id=user.id,
                student_card=user.student_card,
                full_name=user.full_name,
                contact_number=user.contact_number,
                dormitory_id=user.dormitory_id,
                dormitory_name=dormitory.name if dormitory else None,
                room_id=user.room_id,
                room_number=room.room_number if room else None,
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
                points=current_points
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

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверка связанных сущностей только для переданных значений
    if user_update.role_id is not None:
        role = db.query(Role).filter(Role.id == user_update.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")

    if user_update.dormitory_id is not None:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user_update.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    if user_update.room_id is not None:
        room = db.query(Room).filter(Room.id == user_update.room_id).first()
        if not room:
            raise HTTPException(status_code=400, detail="Комната с указанным ID не найдена")

    # Обновление только переданных полей, исключая None
    update_data = user_update.dict(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    # Расчёт текущих баллов на основе нарушений
    total_penalty = db.query(UserViolation).filter(UserViolation.user_id == db_user.id).with_entities(func.sum(UserViolation.penalty_points)).scalar() or 0
    current_points = {"total": max(0, 100 - total_penalty)}  # Пример: начальные 100 баллов минус штрафы
    db_user.points = current_points  # Обновляем поле points в базе
    db.commit()

    # Получаем связанные данные для ответа
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
        points=current_points
    )

@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    db.delete(db_user)
    db.commit()

    return {"message": "Пользователь успешно удалён", "user_id": user_id}