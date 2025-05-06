from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.db.models import CleanlinessHistory, User, Room
from api.schemas.cleanliness import CleanlinessHistoryCreate, CleanlinessHistoryResponse
from api.core.dependencies import get_current_user
from typing import List
from datetime import datetime
import logging

router = APIRouter()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Роли, которым разрешён доступ к админским эндпоинтам
ALLOWED_ROLES = {1, 3, 4}  # 1: Администратор, 3: Член санкомиссии, 4: Глава санкомиссии

def check_user_role(user: User):
    if user.role_id not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этой операции"
        )

@router.post("/cleanliness", response_model=CleanlinessHistoryResponse)
def create_cleanliness_record(
    cleanliness_data: CleanlinessHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем роль пользователя
    check_user_role(current_user)

    # Проверяем, существует ли комната
    room = db.query(Room).filter(Room.id == cleanliness_data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Создаём новую запись
    new_record = CleanlinessHistory(
        room_id=cleanliness_data.room_id,
        score=cleanliness_data.score,
        assigned_by=current_user.id,
        assigned_at=datetime.utcnow()
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record

@router.get("/cleanliness", response_model=List[CleanlinessHistoryResponse])
def get_cleanliness_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    # Проверяем роль пользователя
    check_user_role(current_user)

    # Получаем записи
    records = (
        db.query(CleanlinessHistory)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records

@router.get("/cleanliness/my-room", response_model=List[CleanlinessHistoryResponse])
def get_my_room_cleanliness_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    logger.info(f"User {current_user.id} requesting records with skip={skip}, limit={limit}")
    logger.info(f"User dormitory_id={current_user.dormitory_id}, room_id={current_user.room_id}")

    # Проверяем, что у пользователя есть общежитие и комната
    if current_user.dormitory_id is None:
        logger.error("User has no dormitory_id")
        raise HTTPException(status_code=400, detail="У вас не указано общежитие")
    if current_user.room_id is None:
        logger.error("User has no room_id")
        raise HTTPException(status_code=400, detail="У вас не указана комната")

    # Проверяем, что комната принадлежит общежитию пользователя
    room = db.query(Room).filter(Room.id == current_user.room_id).first()
    if not room:
        logger.error(f"Room {current_user.room_id} not found")
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room.dormitory_id != current_user.dormitory_id:
        logger.error(f"Room dormitory_id {room.dormitory_id} does not match user dormitory_id {current_user.dormitory_id}")
        raise HTTPException(
            status_code=403,
            detail="Ваша комната не соответствует указанному общежитию"
        )

    # Получаем записи для комнаты текущего пользователя
    records = (
    db.query(CleanlinessHistory)
    .filter(CleanlinessHistory.room_id == current_user.room_id)
    .order_by(CleanlinessHistory.assigned_at.desc())
    .offset(skip)
    .limit(limit)
    .all()
    )
    logger.info(f"Found {len(records)} records for room {current_user.room_id}")

    # Проверяем, что все записи валидны перед возвратом
    if not records:
        return []
    return records

@router.get("/cleanliness/{record_id}", response_model=CleanlinessHistoryResponse)
def get_cleanliness_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем роль пользователя
    check_user_role(current_user)

    # Проверяем, существует ли запись
    record = db.query(CleanlinessHistory).filter(CleanlinessHistory.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    return record