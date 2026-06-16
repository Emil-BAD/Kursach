from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import CleanlinessHistory, Room, User
from api.schemas.cleanliness import CleanlinessHistoryCreate, CleanlinessHistoryResponse
from api.services.user_helpers import can_manage_cleanliness

router = APIRouter()


def check_user_role(user: User):
    """
    Проверка прав для административных операций по чистоте.

    Доступ имеют:
    - admin
    - commandant
    - sanitary_commission_member
    - sanitary_commission_head
    """
    if not can_manage_cleanliness(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этой операции",
        )


def _get_record_or_404(db: Session, record_id: int) -> CleanlinessHistory:
    record = (
        db.query(CleanlinessHistory)
        .options(joinedload(CleanlinessHistory.assigned_by_user))
        .filter(CleanlinessHistory.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return record


def _serialize_record(record: CleanlinessHistory) -> dict:
    inspector_name = (
        record.assigned_by_user.full_name
        if record.assigned_by_user
        else None
    )
    return {
        "id": record.id,
        "room_id": record.room_id,
        "score": record.score,
        "assigned_by": record.assigned_by,
        "assigned_at": record.assigned_at,
        "inspector_name": inspector_name,
        "assigned_by_name": inspector_name,
    }


@router.post("/cleanliness", response_model=CleanlinessHistoryResponse)
def create_cleanliness_record(
    cleanliness_data: CleanlinessHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создать запись проверки чистоты.

    Что делает:
    Сохраняет результат проверки комнаты с оценкой и автором проверки.

    Что принимает:
    ```json
    {
      "room_id": 7,
      "score": 4
    }
    ```

    Что возвращает:
    ```json
    {
      "id": 1,
      "room_id": 7,
      "score": 4,
      "assigned_by": 2,
      "assigned_at": "2026-04-29T12:00:00"
    }
    ```
    """
    check_user_role(current_user)

    room = db.query(Room).filter(Room.id == cleanliness_data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    new_record = CleanlinessHistory(
        room_id=cleanliness_data.room_id,
        score=cleanliness_data.score,
        assigned_by=current_user.id,
        assigned_at=datetime.utcnow(),
    )
    db.add(new_record)

    room.cleanliness_points = cleanliness_data.score
    db.commit()
    db.refresh(new_record)
    new_record.assigned_by_user = current_user
    return _serialize_record(new_record)


@router.get("/cleanliness", response_model=List[CleanlinessHistoryResponse])
def get_cleanliness_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Получить общий список проверок чистоты.

    Что делает:
    Возвращает историю всех проверок комнат для админских ролей.

    Что принимает:
    Query-параметры:
    - `skip`
    - `limit`

    Что возвращает:
    Список записей `CleanlinessHistoryResponse`.
    """
    check_user_role(current_user)

    records = (
        db.query(CleanlinessHistory)
        .options(joinedload(CleanlinessHistory.assigned_by_user))
        .order_by(CleanlinessHistory.assigned_at.desc(), CleanlinessHistory.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_record(record) for record in records]


@router.get("/cleanliness/my-room", response_model=List[CleanlinessHistoryResponse])
def get_my_room_cleanliness_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Получить историю чистоты своей комнаты.

    Что делает:
    Возвращает проверки только по комнате текущего пользователя.

    Что принимает:
    Query-параметры:
    - `skip`
    - `limit`

    Что возвращает:
    Список проверок по комнате пользователя.
    """
    if current_user.dormitory_id is None:
        raise HTTPException(status_code=400, detail="У вас не указано общежитие")
    if current_user.room_id is None:
        raise HTTPException(status_code=400, detail="У вас не указана комната")

    room = db.query(Room).filter(Room.id == current_user.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room.dormitory_id != current_user.dormitory_id:
        raise HTTPException(status_code=403, detail="Комната не относится к вашему общежитию")

    records = (
        db.query(CleanlinessHistory)
        .options(joinedload(CleanlinessHistory.assigned_by_user))
        .filter(CleanlinessHistory.room_id == current_user.room_id)
        .order_by(CleanlinessHistory.assigned_at.desc(), CleanlinessHistory.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_record(record) for record in records]


@router.get("/cleanliness/{record_id}", response_model=CleanlinessHistoryResponse)
def get_cleanliness_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить одну запись проверки чистоты.

    Что делает:
    Возвращает одну запись по ID.

    Что принимает:
    Path-параметр `record_id`.

    Что возвращает:
    Объект `CleanlinessHistoryResponse`.
    """
    check_user_role(current_user)
    return _serialize_record(_get_record_or_404(db, record_id))
