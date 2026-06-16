from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.auth import get_password_hash
from api.core.dependencies import get_current_admin
from api.db.database import get_db
from api.db.models import Dormitory, Product, Role, Room, User
from api.schemas.user import PaginatedUserResponse, UserCreate, UserResponse
from api.services.user_helpers import build_user_response, sync_user_points

router = APIRouter()


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.dormitory), joinedload(User.room))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


def _validate_role(db: Session, role_id: int) -> Role:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Роль с указанным ID не найдена")
    return role


def _validate_dormitory(db: Session, dormitory_id: Optional[int]) -> Optional[Dormitory]:
    if dormitory_id is None:
        return None
    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")
    return dormitory


def _validate_room(db: Session, room_id: Optional[int], dormitory_id: Optional[int]) -> Optional[Room]:
    if room_id is None:
        return None

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=400, detail="Комната с указанным ID не найдена")
    if dormitory_id is not None and room.dormitory_id != dormitory_id:
        raise HTTPException(status_code=400, detail="Комната не относится к выбранному общежитию")
    return room


def _parse_birth_date(raw_value: Optional[str]) -> Optional[date]:
    if raw_value is None or raw_value == "":
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте ISO формат, например 2000-05-15",
        )


def _update_user_products_contacts(db: Session, user: User) -> None:
    """
    Синхронизирует контакты продавца в уже опубликованных товарах.

    Это нужно, потому что в текущем API `products` хранят контакты отдельно
    от профиля пользователя.
    """
    telegram = user.social_links.get("telegram") if user.social_links else None
    vk = user.social_links.get("vk") if user.social_links else None

    products = db.query(Product).filter(Product.seller_id == user.id).all()
    for product in products:
        product.seller_telegram = telegram
        product.seller_vk = vk


@router.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Создать пользователя (только администратор).

    Что делает:
    Создаёт нового пользователя в системе, валидирует роль, общежитие и комнату,
    а пароль из поля `password_hash` хеширует перед записью в БД.

    Что принимает:
    ```json
    {
      "student_card": "AB12345",
      "password_hash": "MySecret123",
      "full_name": "Иван Иванов",
      "contact_number": 79001234567,
      "dormitory_id": 1,
      "room_id": 2,
      "group_number": 101,
      "specialization": "ИСиТ",
      "role_id": 1,
      "email": "a@b.ru",
      "phone": "+79991234567",
      "birth_date": "2000-05-01",
      "course": 2,
      "faculty": "ФИТ",
      "social_links": {"telegram": "@ivan"}
    }
    ```

    Что возвращает:
    Полный профиль пользователя в формате `UserResponse`.
    """
    _validate_role(db, user.role_id)
    _validate_dormitory(db, user.dormitory_id)
    _validate_room(db, user.room_id, user.dormitory_id)

    if db.query(User).filter(User.student_card == user.student_card).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким студенческим билетом уже существует")

    db_user = User(
        student_card=user.student_card,
        password_hash=get_password_hash(user.password_hash),
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
        social_links=user.social_links,
        points={"total": 100},
    )
    db.add(db_user)
    db.commit()

    created_user = _get_user_or_404(db, db_user.id)
    return build_user_response(db, created_user)


@router.get("/users", response_model=PaginatedUserResponse)
def get_users(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Получить список пользователей с пагинацией.

    Что делает:
    Возвращает пользователей постранично с профилями, ролью, комнатой и общежитием.

    Что принимает:
    Query-параметры:
    - `page` — номер страницы
    - `size` — размер страницы

    Что возвращает:
    ```json
    {
      "items": [...],
      "total": 100,
      "page": 1,
      "size": 10,
      "total_pages": 10
    }
    ```
    """
    skip = (page - 1) * size
    total = db.query(User).count()
    users = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.dormitory), joinedload(User.room))
        .order_by(User.id)
        .offset(skip)
        .limit(size)
        .all()
    )

    return PaginatedUserResponse(
        items=[build_user_response(db, user, include_violations=False, include_activities=False) for user in users],
        total=total,
        page=page,
        size=size,
        total_pages=(total + size - 1) // size,
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
    social_links_telegram: Optional[str] = Form(None, alias="social_links[telegram]"),
    social_links_vk: Optional[str] = Form(None, alias="social_links[vk]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Обновить пользователя (админ). Принимает `multipart/form-data`.

    Что делает:
    Меняет профиль пользователя, общежитие, комнату, роль и контакты.

    Что принимает:
    Form-data, например:
    - `full_name=Иван Петров`
    - `dormitory_id=1`
    - `room_id=3`
    - `social_links[telegram]=@ivan`
    - `social_links[vk]=https://vk.com/ivan`

    Что возвращает:
    Полный обновлённый профиль пользователя.
    """
    db_user = _get_user_or_404(db, user_id)

    target_dormitory_id = db_user.dormitory_id if dormitory_id is None else dormitory_id
    target_room_id = db_user.room_id if room_id is None else room_id

    if role_id is not None:
        _validate_role(db, role_id)
    _validate_dormitory(db, target_dormitory_id)
    _validate_room(db, target_room_id, target_dormitory_id)

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
        db_user.birth_date = _parse_birth_date(birth_date)
    if course is not None:
        db_user.course = course
    if faculty is not None:
        db_user.faculty = faculty

    social_links = dict(db_user.social_links or {})
    if social_links_telegram is not None:
        social_links["telegram"] = social_links_telegram
    if social_links_vk is not None:
        social_links["vk"] = social_links_vk
    if social_links_telegram is not None or social_links_vk is not None:
        db_user.social_links = social_links
        _update_user_products_contacts(db, db_user)

    sync_user_points(db, db_user)
    db.commit()

    updated_user = _get_user_or_404(db, user_id)
    return build_user_response(db, updated_user)


@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Удалить пользователя (админ).

    Что делает:
    Удаляет пользователя по ID. Связанные записи удаляются по правилам внешних ключей.

    Что принимает:
    Path-параметр `user_id`.

    Что возвращает:
    ```json
    {"message": "Пользователь с ID 5 успешно удалён"}
    ```
    """
    db_user = _get_user_or_404(db, user_id)
    db.delete(db_user)
    db.commit()
    return {"message": f"Пользователь с ID {user_id} успешно удалён"}

