from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin
from api.db.database import get_db
from api.db.models import Dormitory, Room, User
from api.schemas.dormitory import DormitoryResponse, DormitoryWithRoomsResponse
from api.schemas.user import UserResponse
from api.services.user_helpers import build_user_response

router = APIRouter()


def _get_dormitory_or_404(db: Session, dormitory_id: int) -> Dormitory:
    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")
    return dormitory


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return room


@router.post("/dormitories", response_model=DormitoryResponse)
def create_dormitory(
    name: str,
    address: str,
    image_urls: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Создать общежитие.

    Что делает:
    Создаёт новую запись общежития.

    Что принимает:
    Query или form параметры:
    - `name`
    - `address`
    - `image_urls` — список ссылок на изображения

    Что возвращает:
    Объект общежития.
    """
    dormitory = Dormitory(name=name, address=address, image_urls=image_urls or [])
    db.add(dormitory)
    db.commit()
    db.refresh(dormitory)
    return dormitory


@router.get("/dormitories", response_model=List[DormitoryResponse])
def get_dormitories(db: Session = Depends(get_db)):
    """
    Получить список общежитий.

    Что делает:
    Возвращает все общежития без пагинации.

    Что принимает:
    Ничего.

    Что возвращает:
    Список общежитий.
    """
    return db.query(Dormitory).order_by(Dormitory.id).all()


@router.get("/dormitories/{dormitory_id}", response_model=DormitoryResponse)
def get_dormitory_by_id(
    dormitory_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить общежитие по ID.

    Что делает:
    Возвращает одну запись общежития.

    Что принимает:
    Path-параметр `dormitory_id`.

    Что возвращает:
    Объект общежития.
    """
    return _get_dormitory_or_404(db, dormitory_id)


@router.get("/dormitories/{dormitory_id}/rooms", response_model=DormitoryWithRoomsResponse)
def get_dormitory_rooms(
    dormitory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Получить общежитие вместе с комнатами.

    Что делает:
    Возвращает общежитие и вложенный список комнат.

    Что принимает:
    Path-параметр `dormitory_id`.

    Что возвращает:
    ```json
    {
      "id": 1,
      "name": "Общежитие №1",
      "rooms": [...]
    }
    ```
    """
    dormitory = (
        db.query(Dormitory)
        .options(joinedload(Dormitory.rooms))
        .filter(Dormitory.id == dormitory_id)
        .first()
    )
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")
    return dormitory


@router.get("/rooms/{room_id}/users", response_model=List[UserResponse])
def get_users_in_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Получить жильцов комнаты.

    Что делает:
    Возвращает всех пользователей, привязанных к комнате.

    Что принимает:
    Path-параметр `room_id`.

    Что возвращает:
    Список профилей пользователей.
    """
    _get_room_or_404(db, room_id)
    users = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.dormitory), joinedload(User.room))
        .filter(User.room_id == room_id)
        .order_by(User.full_name)
        .all()
    )
    return [build_user_response(db, user) for user in users]


@router.put("/dormitories/{dormitory_id}", response_model=DormitoryResponse)
def update_dormitory(
    dormitory_id: int,
    name: Optional[str] = None,
    address: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Обновить общежитие.

    Что делает:
    Меняет название, адрес и изображения общежития.

    Что принимает:
    Query или form параметры:
    - `name`
    - `address`
    - `image_urls`

    Что возвращает:
    Обновлённый объект общежития.
    """
    dormitory = _get_dormitory_or_404(db, dormitory_id)

    if name is not None:
        dormitory.name = name
    if address is not None:
        dormitory.address = address
    if image_urls is not None:
        dormitory.image_urls = image_urls

    db.commit()
    db.refresh(dormitory)
    return dormitory
