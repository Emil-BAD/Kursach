# -*- coding: utf-8 -*-
"""
API v1 - Auth роутер (тонкий слой)
Только валидация входных данных и вызов service слоя.
"""
import logging

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.core.config import settings
from api.db.database import get_db
from api.services.auth_service import AuthService
from api.schemas.user import UserRegister
from api.core.exceptions import APIException
from api.services.user_helpers import build_user_response


router = APIRouter(prefix="/api/v1", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Вход по студенческому билету и паролю.
    
    **Принимает:**
    - username (form-data): номер студенческого билета (например "AB12345")
    - password (form-data): пароль
    
    **Возвращает:**
    ```json
    {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
    ```
    """
    try:
        service = AuthService(db)
        result = service.login(form_data.username, form_data.password)
        return result
    except APIException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in v1 login for student_card=%s", form_data.username)
        if settings.DEBUG:
            raise
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.post("/auth/register")
def register(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Регистрация нового пользователя (студента).
    
    **Принимает:**
    ```json
    {
      "student_card": "AB12345",
      "password": "SecurePass123",
      "full_name": "Иван Иванов",
      "phone": "+79001234567",
      "role_id": 1,
      "group_number": 101,
      "email": "ivan@example.com"
    }
    ```
    
    **Возвращает:**
    Полный профиль созданного пользователя.
    """
    try:
        service = AuthService(db)
        user = service.register(
            student_card=data.student_card,
            password=data.password,
            full_name=data.full_name,
            contact_number=data.contract_number,
            role_id=data.role_id,
            dormitory_id=data.dormitory_id,
            room_id=data.room_id,
            group_number=data.group_number,
            specialization=data.specialization,
            email=data.email,
            phone=data.phone,
            birth_date=data.birth_date,
            course=data.course,
            faculty=data.faculty,
            social_links=data.social_links,
        )
        return build_user_response(db, user)
    except APIException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in v1 register for student_card=%s", data.student_card)
        if settings.DEBUG:
            raise
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.post("/auth/refresh")
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Обновить access token используя refresh token.
    
    **Принимает query параметр:**
    - refresh_token: действительный refresh token
    
    **Возвращает:**
    ```json
    {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
    ```
    """
    try:
        service = AuthService(db)
        result = service.refresh_access_token(refresh_token)
        return result
    except APIException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in v1 refresh token")
        if settings.DEBUG:
            raise
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.post("/auth/logout")
def logout(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Выход (удаление refresh token).
    
    **Принимает query параметр:**
    - refresh_token: refresh token для удаления
    
    **Возвращает:**
    ```json
    {
      "success": true,
      "message": "Успешно вышли из системы"
    }
    ```
    """
    try:
        service = AuthService(db)
        service.logout(refresh_token)
        return {"success": True, "message": "Успешно вышли из системы"}
    except APIException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in v1 logout")
        if settings.DEBUG:
            raise
        from api.core.exceptions import InternalServerError
        raise InternalServerError()
