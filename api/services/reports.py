# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin
from api.db.database import get_db
from api.db.models import Dormitory, User, UserActivity, UserViolation
from api.schemas.report import DisciplineSummaryResponse, DisciplineUserReportResponse, DormitorySummaryResponse

router = APIRouter(prefix="/reports")


@router.get("/dormitories/summary", response_model=list[DormitorySummaryResponse])
def get_dormitory_summary_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Возвращает агрегаты по общежитиям: число комнат, число мест, занятые места и процент заполненности.

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
            DormitorySummaryResponse(
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


@router.get("/discipline", response_model=DisciplineSummaryResponse)
def get_discipline_report(
    dormitory_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Возвращает отчёт по баллам и нарушениям: количество нарушений, штрафные баллы, активности и итоговые баллы по студентам.

    Что принимает:
    Query-параметры, например:
    {
      "dormitory_id": 1
    }

    Что возвращает:
    {
      "items": [
        {
          "user_id": 5,
          "full_name": "Иван Иванов",
          "total_points": 92,
          "violation_count": 2,
          "penalty_points": 10,
          "activity_count": 1,
          "earned_points": 2
        }
      ],
      "total_users": 1,
      "total_violations": 2,
      "total_penalty_points": 10,
      "total_earned_points": 2
    }
    """
    violation_rows = (
        db.query(
            UserViolation.user_id,
            func.count(UserViolation.id),
            func.coalesce(func.sum(UserViolation.penalty_points), 0),
        )
        .group_by(UserViolation.user_id)
        .all()
    )
    activity_rows = (
        db.query(
            UserActivity.user_id,
            func.count(UserActivity.id),
            func.coalesce(func.sum(UserActivity.earned_points), 0),
        )
        .group_by(UserActivity.user_id)
        .all()
    )

    violation_map = {row[0]: {"count": int(row[1]), "points": int(row[2])} for row in violation_rows}
    activity_map = {row[0]: {"count": int(row[1]), "points": int(row[2])} for row in activity_rows}

    user_query = db.query(User)
    if dormitory_id is not None:
        user_query = user_query.filter(User.dormitory_id == dormitory_id)

    users = user_query.order_by(User.full_name).all()
    items = []
    total_violations = 0
    total_penalty_points = 0
    total_earned_points = 0

    for user in users:
        user_violation = violation_map.get(user.id, {"count": 0, "points": 0})
        user_activity = activity_map.get(user.id, {"count": 0, "points": 0})
        total_points = max(0, 100 + user_activity["points"] - user_violation["points"])

        total_violations += user_violation["count"]
        total_penalty_points += user_violation["points"]
        total_earned_points += user_activity["points"]

        items.append(
            DisciplineUserReportResponse(
                user_id=user.id,
                full_name=user.full_name,
                dormitory_id=user.dormitory_id,
                dormitory_name=user.dormitory.name if user.dormitory else None,
                room_id=user.room_id,
                room_number=user.room.room_number if user.room else None,
                total_points=total_points,
                violation_count=user_violation["count"],
                penalty_points=user_violation["points"],
                activity_count=user_activity["count"],
                earned_points=user_activity["points"],
            )
        )

    return DisciplineSummaryResponse(
        items=items,
        total_users=len(items),
        total_violations=total_violations,
        total_penalty_points=total_penalty_points,
        total_earned_points=total_earned_points,
    )
