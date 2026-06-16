# -*- coding: utf-8 -*-
"""
API v1 - Users роутер (тонкий слой)
Управление пользователями: создание, обновление, удаление, получение списков.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db.models import User
from api.core.dependencies import get_current_user
from api.core.rbac import require_role, Role
from api.services.user_service import UserService
from api.schemas.user import UserResponse, UserCreate, UserUpdate
from api.schemas.common import paginate_response, PaginatedResponse
from api.core.exceptions import APIException
from api.services.user_helpers import build_user_response

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить профиль текущего пользователя.
    
    **Принимает:**
    - Authorization: Bearer {access_token}
    
    **Возвращает:**
    Полный профиль пользователя (ID, ФИО, общежитие, комната, баллы и т.д.)
    """
    try:
        # Keep /me lightweight: profile fields first, heavy history endpoints separately.
        return build_user_response(
            db,
            current_user,
            include_violations=False,
            include_activities=False,
            include_room_violation_frequency=False,
        )
    except APIException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /api/v1/me for user_id=%s", current_user.id)
        # Emergency fallback: return minimal profile instead of 500
        # so client screens can keep working during transient DB failures.
        return UserResponse(
            id=current_user.id,
            student_card=current_user.student_card,
            full_name=current_user.full_name,
            contact_number=current_user.contact_number or 0,
            dormitory_id=current_user.dormitory_id,
            dormitory_name=None,
            room_id=current_user.room_id,
            room_number=None,
            group_number=current_user.group_number,
            specialization=current_user.specialization,
            role_id=current_user.role_id,
            role_name="Unknown",
            role_description=None,
            email=current_user.email,
            phone=current_user.phone,
            birth_date=current_user.birth_date,
            course=current_user.course,
            faculty=current_user.faculty,
            created_at=current_user.created_at or datetime.utcnow(),
            points=current_user.points if isinstance(current_user.points, dict) else {"total": 0},
            social_links=current_user.social_links if isinstance(current_user.social_links, dict) else {},
            violations=[],
            room_violation_frequency=None,
            room_cleanliness_points=None,
            activities=[],
        )


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Обновить свой профиль.
    
    **Принимает:**
    ```json
    {
      "full_name": "Иван Петров",
      "phone": "+79001234567",
      "email": "ivan@example.com",
      "social_links": {"telegram": "@ivan", "vk": "https://vk.com/ivan"}
    }
    ```
    
    **Возвращает:**
    Обновленный профиль пользователя.
    """
    try:
        # Очищаем данные: берём только те поля которые не None
        update_fields = {k: v for k, v in data.dict().items() if v is not None}
        
        service = UserService(db)
        updated_user = service.update_user(current_user.id, **update_fields)
        return build_user_response(db, updated_user)
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/users", response_model=dict)
def list_all_users(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(require_role(Role.ADMIN, Role.COMMANDANT)),
    db: Session = Depends(get_db),
):
    """
    Получить список всех пользователей (админ и комендант).
    
    **Параметры:**
    - page: номер страницы (по умолчанию 1)
    - page_size: размер страницы (по умолчанию 20, макс 100)
    
    **Возвращает:**
    ```json
    {
      "items": [...],
      "page": 1,
      "page_size": 20,
      "total": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
    ```
    """
    try:
        service = UserService(db)
        users, total = service.get_all_users(page=page, page_size=page_size)
        result = paginate_response(
            [build_user_response(db, user, include_violations=False, include_activities=False) for user in users],
            page,
            page_size,
            total,
        )
        return result
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_role(Role.ADMIN, Role.COMMANDANT)),
    db: Session = Depends(get_db),
):
    """
    Получить профиль пользователя по ID (админ и комендант).
    
    **Параметры:**
    - user_id: ID пользователя
    
    **Возвращает:**
    Полный профиль пользователя.
    """
    try:
        service = UserService(db)
        user = service.get_user_by_id(user_id)
        return build_user_response(db, user)
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.post("/users", response_model=UserResponse)
def create_new_user(
    data: UserCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Создать нового пользователя (только админ).
    
    **Принимает:**
    ```json
    {
      "student_card": "AB12345",
      "password_hash": "SecurePass123",
      "full_name": "Иван Иванов",
      "contact_number": 79001234567,
      "role_id": 1,
      "dormitory_id": 1,
      "room_id": 2,
      "group_number": 101,
      "email": "ivan@example.com",
      "birth_date": "2000-05-01",
      "course": 2,
      "faculty": "ФИТ",
      "specialization": "ИСиТ"
    }
    ```
    
    **Возвращает:**
    Профиль созданного пользователя.
    """
    try:
        service = UserService(db)
        user = service.create_user(
            student_card=data.student_card,
            password=data.password_hash,  # Примечание: в схеме password_hash, но это открытый пароль
            full_name=data.full_name,
            contact_number=data.contact_number,
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
        )
        return build_user_response(db, user)
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Обновить данные пользователя (только админ).
    
    **Принимает:**
    ```json
    {
      "full_name": "Иван Петров",
      "role_id": 2,
      "dormitory_id": 1,
      "room_id": 3
    }
    ```
    
    **Возвращает:**
    Обновленный профиль пользователя.
    """
    try:
        update_fields = {k: v for k, v in data.dict().items() if v is not None}
        
        service = UserService(db)
        updated_user = service.update_user(user_id, **update_fields)
        return build_user_response(db, updated_user)
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Удалить пользователя (только админ).
    
    **Параметры:**
    - user_id: ID пользователя для удаления
    
    **Возвращает:**
    ```json
    {
      "success": true,
      "message": "Пользователь успешно удален"
    }
    ```
    """
    try:
        service = UserService(db)
        service.delete_user(user_id)
        return {"success": True, "message": "Пользователь успешно удален"}
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/dormitories/{dorm_id}/users", response_model=dict)
def list_users_in_dormitory(
    dorm_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(Role.ADMIN, Role.COMMANDANT)),
    db: Session = Depends(get_db),
):
    """
    Получить список пользователей в общежитии (админ и комендант).
    
    **Параметры:**
    - dorm_id: ID общежития
    - page: номер страницы
    - page_size: размер страницы
    
    **Возвращает:**
    Paginated список пользователей в общежитии.
    """
    try:
        service = UserService(db)
        users, total = service.get_users_by_dormitory(dorm_id, page=page, page_size=page_size)
        result = paginate_response(
            [build_user_response(db, user, include_violations=False, include_activities=False) for user in users],
            page,
            page_size,
            total,
        )
        return result
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/rooms/{room_id}/users", response_model=dict)
def list_users_in_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить список пользователей в комнате.
    
    **Параметры:**
    - room_id: ID комнаты
    
    **Возвращает:**
    ```json
    {
      "items": [...],
      "total": 2
    }
    ```
    """
    try:
        service = UserService(db)
        users = service.get_users_by_room(room_id)
        return {
            "items": [build_user_response(db, user, include_violations=False, include_activities=False) for user in users],
            "total": len(users),
        }
    except APIException:
        raise
    except Exception as e:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()
