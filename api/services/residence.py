# -*- coding: utf-8 -*-
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import Dormitory, ResidenceHistory, Room, User
from api.schemas.residence import (
    CheckInCreate,
    CheckOutUpdate,
    DormitoryOccupancyResponse,
    ResidenceHistoryListResponse,
    ResidenceHistoryResponse,
    RoomOccupancyResponse,
)

router = APIRouter(prefix="/residence")


def _build_residence_response(item: ResidenceHistory) -> ResidenceHistoryResponse:
    return ResidenceHistoryResponse(
        id=item.id,
        user_id=item.user_id,
        user_name=item.user.full_name if item.user else "Unknown",
        dormitory_id=item.dormitory_id,
        dormitory_name=item.dormitory.name if item.dormitory else "Unknown",
        room_id=item.room_id,
        room_number=item.room.room_number if item.room else 0,
        check_in_date=item.check_in_date,
        check_out_date=item.check_out_date,
        eviction_reason=item.eviction_reason,
        comment=item.comment,
        created_at=item.created_at,
        is_active=item.check_out_date is None,
    )


def _get_residence_or_404(db: Session, residence_id: int) -> ResidenceHistory:
    residence = (
        db.query(ResidenceHistory)
        .options(
            joinedload(ResidenceHistory.user),
            joinedload(ResidenceHistory.dormitory),
            joinedload(ResidenceHistory.room),
        )
        .filter(ResidenceHistory.id == residence_id)
        .first()
    )
    if not residence:
        raise HTTPException(status_code=404, detail="Запись проживания не найдена")
    return residence


@router.post("/check-in", response_model=ResidenceHistoryResponse)
def check_in_user(
    check_in_data: CheckInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Заселяет студента в комнату, создаёт запись истории проживания и обновляет текущую комнату пользователя.

    Что принимает:
    {
      "user_id": 5,
      "dormitory_id": 1,
      "room_id": 7,
      "check_in_date": "2026-04-22",
      "comment": "Первичное заселение"
    }

    Что возвращает:
    {
      "id": 3,
      "user_id": 5,
      "room_id": 7,
      "check_in_date": "2026-04-22",
      "is_active": true
    }
    """
    user = db.query(User).filter(User.id == check_in_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    dormitory = db.query(Dormitory).filter(Dormitory.id == check_in_data.dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")

    room = db.query(Room).filter(Room.id == check_in_data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room.dormitory_id != dormitory.id:
        raise HTTPException(status_code=400, detail="Комната не относится к указанному общежитию")

    active_record = (
        db.query(ResidenceHistory)
        .filter(ResidenceHistory.user_id == user.id, ResidenceHistory.check_out_date.is_(None))
        .first()
    )
    if active_record or user.room_id is not None:
        raise HTTPException(status_code=400, detail="Пользователь уже заселён. Сначала оформите выселение")

    occupied_places = db.query(User).filter(User.room_id == room.id).count()
    if occupied_places >= room.capacity:
        raise HTTPException(status_code=400, detail="В комнате нет свободных мест")

    residence = ResidenceHistory(
        user_id=user.id,
        dormitory_id=dormitory.id,
        room_id=room.id,
        check_in_date=check_in_data.check_in_date,
        comment=check_in_data.comment,
    )
    db.add(residence)

    user.dormitory_id = dormitory.id
    user.room_id = room.id

    db.commit()
    return _build_residence_response(_get_residence_or_404(db, residence.id))


@router.put("/{residence_id}/check-out", response_model=ResidenceHistoryResponse)
def check_out_user(
    residence_id: int,
    check_out_data: CheckOutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Оформляет выселение, сохраняет дату выезда и причину выселения, после чего освобождает комнату у пользователя.

    Что принимает:
    {
      "check_out_date": "2026-06-01",
      "eviction_reason": "Окончание семестра",
      "comment": "Осмотр комнаты проведён"
    }

    Что возвращает:
    {
      "id": 3,
      "user_id": 5,
      "check_out_date": "2026-06-01",
      "eviction_reason": "Окончание семестра",
      "is_active": false
    }
    """
    residence = _get_residence_or_404(db, residence_id)
    if residence.check_out_date is not None:
        raise HTTPException(status_code=400, detail="Выселение по этой записи уже оформлено")
    if check_out_data.check_out_date < residence.check_in_date:
        raise HTTPException(status_code=400, detail="Дата выселения не может быть раньше даты заселения")

    residence.check_out_date = check_out_data.check_out_date
    residence.eviction_reason = check_out_data.eviction_reason
    residence.comment = check_out_data.comment or residence.comment

    user = db.query(User).filter(User.id == residence.user_id).first()
    if user and user.room_id == residence.room_id:
        user.room_id = None
        user.dormitory_id = None

    db.commit()
    return _build_residence_response(_get_residence_or_404(db, residence.id))


@router.get("/history", response_model=ResidenceHistoryListResponse)
def get_residence_history(
    user_id: int | None = None,
    dormitory_id: int | None = None,
    room_id: int | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает историю проживания студентов. Администратор видит всё, студент — только свою историю.

    Что принимает:
    Query-параметры, например:
    {
      "user_id": 5,
      "active_only": true
    }

    Что возвращает:
    {
      "items": [
        {
          "id": 3,
          "user_id": 5,
          "check_in_date": "2026-04-22",
          "check_out_date": null
        }
      ],
      "total": 1
    }
    """
    query = db.query(ResidenceHistory).options(
        joinedload(ResidenceHistory.user),
        joinedload(ResidenceHistory.dormitory),
        joinedload(ResidenceHistory.room),
    )

    is_admin = bool(current_user.role and current_user.role.role_name == "admin")
    if not is_admin:
        query = query.filter(ResidenceHistory.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(ResidenceHistory.user_id == user_id)

    if dormitory_id is not None:
        query = query.filter(ResidenceHistory.dormitory_id == dormitory_id)
    if room_id is not None:
        query = query.filter(ResidenceHistory.room_id == room_id)
    if active_only:
        query = query.filter(ResidenceHistory.check_out_date.is_(None))

    items = query.order_by(ResidenceHistory.check_in_date.desc(), ResidenceHistory.id.desc()).all()
    return ResidenceHistoryListResponse(
        items=[_build_residence_response(item) for item in items],
        total=len(items),
    )


@router.get("/occupancy/rooms", response_model=list[RoomOccupancyResponse])
def get_room_occupancy_report(
    dormitory_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Возвращает заполненность комнат: вместимость, занятые места, свободные места и процент заполнения.

    Что принимает:
    Query-параметры, например:
    {
      "dormitory_id": 1
    }

    Что возвращает:
    [
      {
        "room_id": 7,
        "room_number": 215,
        "capacity": 3,
        "occupied_places": 2,
        "free_places": 1,
        "occupancy_percent": 66.67
      }
    ]
    """
    query = db.query(Room).options(joinedload(Room.dormitory))
    if dormitory_id is not None:
        query = query.filter(Room.dormitory_id == dormitory_id)

    rooms = query.order_by(Room.dormitory_id, Room.room_number).all()
    result = []
    for room in rooms:
        occupied_places = db.query(User).filter(User.room_id == room.id).count()
        free_places = max(room.capacity - occupied_places, 0)
        occupancy_percent = round((occupied_places / room.capacity) * 100, 2) if room.capacity else 0
        result.append(
            RoomOccupancyResponse(
                room_id=room.id,
                room_number=room.room_number,
                dormitory_id=room.dormitory_id,
                dormitory_name=room.dormitory.name if room.dormitory else "Unknown",
                capacity=room.capacity,
                occupied_places=occupied_places,
                free_places=free_places,
                occupancy_percent=occupancy_percent,
            )
        )
    return result


@router.get("/occupancy/dormitories", response_model=list[DormitoryOccupancyResponse])
def get_dormitory_occupancy_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Возвращает сводку по общежитиям: число комнат, мест, занятых мест и процент заполнения.

    Что принимает:
    Пустой запрос без тела.

    Что возвращает:
    [
      {
        "dormitory_id": 1,
        "dormitory_name": "Общежитие №1",
        "total_rooms": 20,
        "total_places": 60,
        "occupied_places": 41,
        "free_places": 19,
        "occupancy_percent": 68.33
      }
    ]
    """
    dormitories = db.query(Dormitory).options(joinedload(Dormitory.rooms)).order_by(Dormitory.id).all()
    result = []
    for dormitory in dormitories:
        total_rooms = len(dormitory.rooms)
        total_places = sum(room.capacity for room in dormitory.rooms)
        occupied_places = db.query(User).filter(User.dormitory_id == dormitory.id, User.room_id.is_not(None)).count()
        free_places = max(total_places - occupied_places, 0)
        occupancy_percent = round((occupied_places / total_places) * 100, 2) if total_places else 0
        result.append(
            DormitoryOccupancyResponse(
                dormitory_id=dormitory.id,
                dormitory_name=dormitory.name,
                total_rooms=total_rooms,
                total_places=total_places,
                occupied_places=occupied_places,
                free_places=free_places,
                occupancy_percent=occupancy_percent,
            )
        )
    return result
