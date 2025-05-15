from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from api.db.database import get_db
from api.db.models import UserActivity, User, ActivityType
from api.schemas.user_activity import UserActivityCreate, UserActivityUpdate, UserActivityResponse, PaginatedUserActivityResponse
from api.core.dependencies import get_current_user, get_current_admin
from sqlalchemy.sql import func

router = APIRouter()

@router.get("/activities", response_model=PaginatedUserActivityResponse)
def get_activities(
    page: int = 1,
    per_page: int = 10,
    user_id: int = None,
    activity_type_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * per_page
    query = db.query(UserActivity).options(
        joinedload(UserActivity.user),
        joinedload(UserActivity.activity_type)
    )

    # Фильтрация
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    if activity_type_id:
        query = query.filter(UserActivity.activity_type_id == activity_type_id)

    # Ограничение доступа: только администраторы или собственные активности
    if current_user.role_id not in [2, 7, 8, 9]:  # Предполагаем роли 1, 2, 3 как администраторы
        query = query.filter(UserActivity.user_id == current_user.id)

    total = query.count()
    activities = query.offset(skip).limit(per_page).all()

    activity_responses = []
    for activity in activities:
        activity_responses.append({
            "id": activity.id,
            "user_id": activity.user_id,
            "user_name": activity.user.full_name if activity.user else "Unknown",
            "activity_type_id": activity.activity_type_id,
            "activity_type_name": activity.activity_type.activity_name if activity.activity_type else "Unknown",
            "activity_date": activity.activity_date,
            "earned_points": activity.earned_points,
            "description": activity.description,
            "notes": activity.notes
        })

    total_pages = (total + per_page - 1) // per_page

    return PaginatedUserActivityResponse(
        items=activity_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/activities/{activity_id}", response_model=UserActivityResponse)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = db.query(UserActivity).options(
        joinedload(UserActivity.user),
        joinedload(UserActivity.activity_type)
    ).filter(UserActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Активность не найдена")

    if current_user.role_id not in [2, 7, 8, 9] and activity.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра активности")

    return {
        "id": activity.id,
        "user_id": activity.user_id,
        "user_name": activity.user.full_name if activity.user else "Unknown",
        "activity_type_id": activity.activity_type_id,
        "activity_type_name": activity.activity_type.activity_name if activity.activity_type else "Unknown",
        "activity_date": activity.activity_date,
        "earned_points": activity.earned_points,
        "description": activity.description,
        "notes": activity.notes
    }

@router.post("/activities", response_model=UserActivityResponse)
def create_activity(
    activity: UserActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == activity.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь с указанным ID не найден")

    activity_type = db.query(ActivityType).filter(ActivityType.id == activity.activity_type_id).first()
    if not activity_type:
        raise HTTPException(status_code=400, detail="Тип активности с указанным ID не найден")

    db_activity = UserActivity(
        user_id=activity.user_id,
        activity_type_id=activity.activity_type_id,
        activity_date=activity.activity_date,
        earned_points=activity.earned_points,
        description=activity.description,
        notes=activity.notes
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)

    # Обновление баллов пользователя
    total_points = db.query(UserActivity).filter(UserActivity.user_id == user.id).with_entities(func.sum(UserActivity.earned_points)).scalar() or 0
    user.points = {"total": max(100, 100 + total_points)}  # Начинаем с 100 и прибавляем очки
    db.commit()

    user = db.query(User).filter(User.id == db_activity.user_id).first()
    activity_type = db.query(ActivityType).filter(ActivityType.id == db_activity.activity_type_id).first()

    return {
        "id": db_activity.id,
        "user_id": db_activity.user_id,
        "user_name": user.full_name if user else "Unknown",
        "activity_type_id": db_activity.activity_type_id,
        "activity_type_name": activity_type.activity_name if activity_type else "Unknown",
        "activity_date": db_activity.activity_date,
        "earned_points": db_activity.earned_points,
        "description": db_activity.description,
        "notes": db_activity.notes
    }

@router.delete("/activities/{activity_id}", response_model=dict)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_activity = db.query(UserActivity).filter(UserActivity.id == activity_id).first()
    if not db_activity:
        raise HTTPException(status_code=404, detail="Активность не найдена")

    user = db.query(User).filter(User.id == db_activity.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")

    # Удаление активности
    db.delete(db_activity)
    db.commit()

    # Пересчёт баллов пользователя после удаления
    total_points = db.query(UserActivity).filter(UserActivity.user_id == user.id).with_entities(func.sum(UserActivity.earned_points)).scalar() or 0
    user.points = {"total": max(100, 100 + total_points)}  # Обновляем с минимальным значением 100
    db.commit()

    return {"message": "Активность успешно удалена", "activity_id": activity_id}