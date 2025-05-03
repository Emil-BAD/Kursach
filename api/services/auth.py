# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from typing import Dict
from db.database import get_db
from schemas.user import UserRegister
from db.models import User, Role, Dormitory, Room
from passlib.context import CryptContext
from pydantic import BaseModel
from core.dependencies import get_current_admin

from core.auth import create_access_token, ALGORITHM, verify_password
from core.config import settings
from db.database import get_db
from db.models import User

router = APIRouter(tags=["auth"])

@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.student_card == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный student_card или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный student_card или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

@router.post("/register", response_model=Dict)
def register_user(
    user: UserRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Ограничиваем доступ только админам
):
    # Проверка, существует ли пользователь с таким student_card
    existing_user = db.query(User).filter(User.student_card == user.student_card).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким студенческим билетом уже существует")

    # Проверка существования роли
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")

    # Проверка существования общежития, если указано
    if user.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Проверка существования комнаты, если указано
    if user.room_id:
        room = db.query(Room).filter(Room.id == user.room_id).first()
        if not room:
            raise HTTPException(status_code=400, detail="Комната с указанным ID не найдена")

    # Хешируем пароль
    hashed_password = hash_password(user.password)

    # Создаем нового пользователя
    db_user = User(
        student_card=user.student_card,
        password_hash=hashed_password,
        full_name=user.full_name,
        contract_number=user.contract_number,
        role_id=user.role_id,
        dormitory_id=user.dormitory_id,
        room_id=user.room_id,
        group_number=user.group_number,
        specialization=user.specialization,
        email=user.email,
        phone=user.phone,
        birth_date=user.birth_date,
        course=user.course,
        faculty=user.faculty,
        device_token=None
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "id": db_user.id,
        "student_card": db_user.student_card,
        "full_name": db_user.full_name,
        "message": "Пользователь успешно зарегистрирован"
    }