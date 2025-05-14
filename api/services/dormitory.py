from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from api.db.database import get_db
from api.db.models import User, Dormitory, Room, Role
from api.schemas.user import UserResponse
from api.schemas.dormitory import DormitoryResponse, DormitoryWithRoomsResponse
from api.core.dependencies import get_current_admin, get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post("/dormitories", response_model=DormitoryResponse)
def create_dormitory(
    name: str,
    address: str,
    image_urls: List[str] | None = None,  # Обновляем параметр в соответствии со схемой
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    dormitory = Dormitory(name=name, address=address, image_urls=image_urls)
    db.add(dormitory)
    db.commit()
    db.refresh(dormitory)
    return dormitory

# Маршрут: Получение списка всех общежитий
@router.get("/dormitories", response_model=List[DormitoryResponse])
def get_dormitories(
    db: Session = Depends(get_db)
):
    dormitories = db.query(Dormitory).all()
    if not dormitories:
        raise HTTPException(status_code=404, detail="Общежития не найдены")
    return dormitories

# Новый маршрут: Получение общежития по ID
@router.get("/dormitories/{dormitory_id}", response_model=DormitoryResponse)
def get_dormitory_by_id(
    dormitory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")
    return dormitory

@router.get("/dormitories/{dormitory_id}/rooms", response_model=DormitoryWithRoomsResponse)
def get_dormitory_rooms(
    dormitory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    dormitory = db.query(Dormitory).options(joinedload(Dormitory.rooms)).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")
    return dormitory

# Маршрут: Получение списка студентов в заданной комнате
@router.get("/rooms/{room_id}/users", response_model=List[UserResponse])
def get_users_in_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    users = db.query(User).filter(User.room_id == room_id).all()
    user_responses = []
    for user in users:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user.dormitory_id).first() if user.dormitory_id else None
        role = db.query(Role).filter(Role.id == user.role_id).first()

        user_responses.append(
            UserResponse(
                id=user.id,
                student_card=user.student_card,
                full_name=user.full_name,
                contact_number=user.contract_number,
                dormitory_id=user.dormitory_id or 0,
                dormitory_name=dormitory.name if dormitory else None,
                room_id=user.room_id or 0,
                room_number=room.room_number if room else 0,
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
                points={}
            )
        )

    return user_responses

@router.put("/dormitories/{dormitory_id}", response_model=DormitoryResponse)
def update_dormitory(
    dormitory_id: int,
    name: str | None = None,
    address: str | None = None,
    image_urls: List[str] | None = None,  # Обновляем параметр в соответствии со схемой
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")

    if name is not None:
        dormitory.name = name
    if address is not None:
        dormitory.address = address
    if image_urls is not None:
        dormitory.image_urls = image_urls

    db.commit()
    db.refresh(dormitory)
    return dormitory