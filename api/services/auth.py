# -*- coding: utf-8 -*-
"""
Роутер авторизации: логин, refresh, выход из всех сессий, регистрация.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from api.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from api.core.config import settings
from api.core.exceptions import DatabaseUnavailableError
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import RefreshToken, Role, User
from api.schemas.user import UserRegister
from api.services.user_helpers import build_user_response

router = APIRouter()


def _access_token_delta() -> timedelta:
    """Срок жизни access-токена из настроек (в минутах)."""
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def _refresh_token_delta() -> timedelta:
    """Срок жизни refresh-токена из настроек (в днях)."""
    return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


@router.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Вход по студенческому билету и паролю.

    Принимает (form-urlencoded, как у OAuth2, не JSON):
      username = номер студенческого билета
      password = пароль

    Пример для Postman / curl (не JSON-тело):
      username=AB12345&password=mypass

    Возвращает JSON:
      {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
    """
    try:
        user = db.query(User).filter(User.student_card == form_data.username).first()
    except OperationalError:
        raise DatabaseUnavailableError()
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

    access_token_expires = _access_token_delta()
    refresh_token_expires = _refresh_token_delta()

    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )

    refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + refresh_token_expires,
    )
    db.add(refresh)
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        raise DatabaseUnavailableError()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить сессию, попробуйте позже",
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/auth/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    """
    Выдать новую пару токенов по действительному refresh (ротация: старый refresh удаляется).

    Принимает (query-параметр, не JSON в теле):
      GET/POST ... ?refresh_token=...

    Пример:
      /auth/refresh?refresh_token=eyJ...

    Возвращает JSON:
      {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
    """
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Неверный refresh токен")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh токен истёк")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный refresh токен")

    try:
        stored_token = (
            db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        )
    except OperationalError:
        raise DatabaseUnavailableError()
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh токен недействителен")

    db.delete(stored_token)
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        raise DatabaseUnavailableError()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при обновлении сессии, попробуйте войти заново",
        )

    access_token = create_access_token(
        data={"sub": str(user_id)}, expires_delta=_access_token_delta()
    )
    new_refresh = create_refresh_token(
        data={"sub": str(user_id)}, expires_delta=_refresh_token_delta()
    )

    new_row = RefreshToken(
        user_id=int(user_id),
        token=new_refresh,
        expires_at=datetime.utcnow() + _refresh_token_delta(),
    )
    db.add(new_row)
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        raise DatabaseUnavailableError()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить новую сессию",
        )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/auth/invalidate")
def invalidate_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Удалить все refresh-токены текущего пользователя (выйти везде, кроме текущего access до истечения).

    Принимает:
      Заголовок Authorization: Bearer <access_token>
      Тело запроса пустое.

    Возвращает JSON:
      {"message": "Все токены аннулированы"}
    """
    try:
        db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete(
            synchronize_session=False
        )
        db.commit()
    except OperationalError:
        db.rollback()
        raise DatabaseUnavailableError()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось аннулировать сессии",
        )
    return {"message": "Все токены аннулированы"}


@router.post("/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя по студенческому билету.

    Принимает JSON (пример):
      {
        "student_card": "AB12345",
        "password": "SecurePass1",
        "full_name": "Иван Иванов",
        "contract_number": 79001234567,
        "role_id": 10,
        "dormitory_id": 1,
        "room_id": 5
      }

    Возвращает JSON (профиль созданного пользователя):
      {
        "id": 5,
        "student_card": "AB12345",
        "full_name": "Иван Иванов",
        "role_name": "student"
      }
    """
    try:
        existing_user = db.query(User).filter(User.student_card == user_data.student_card).first()
    except OperationalError:
        raise DatabaseUnavailableError()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким студенческим билетом уже существует",
        )

    hashed_password = get_password_hash(user_data.password)

    birth_date = None
    if user_data.birth_date:
        try:
            birth_date = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты рождения, ожидается YYYY-MM-DD",
            )

    try:
        role = db.query(Role).filter(Role.id == user_data.role_id).first()
    except OperationalError:
        raise DatabaseUnavailableError()
    if not role:
        raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")

    new_user = User(
        student_card=user_data.student_card,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        contact_number=user_data.contract_number,
        dormitory_id=user_data.dormitory_id,
        room_id=user_data.room_id,
        group_number=user_data.group_number,
        specialization=user_data.specialization,
        role_id=user_data.role_id,
        email=user_data.email,
        phone=user_data.phone,
        birth_date=birth_date,
        course=user_data.course,
        faculty=user_data.faculty,
        created_at=datetime.utcnow(),
        points={"total": 100},
        social_links=user_data.social_links,
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except OperationalError:
        db.rollback()
        raise DatabaseUnavailableError()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось создать пользователя",
        )

    return build_user_response(db, new_user)
