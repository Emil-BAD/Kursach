from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import ActivityType, User, UserActivity
from api.schemas.user_activity import (
    PaginatedUserActivityResponse,
    UserActivityCreate,
    UserActivityResponse,
)
from api.services.user_helpers import can_manage_activities, sync_user_points

router = APIRouter()


def _get_activity_or_404(db: Session, activity_id: int) -> UserActivity:
    activity = (
        db.query(UserActivity)
        .options(joinedload(UserActivity.user), joinedload(UserActivity.activity_type))
        .filter(UserActivity.id == activity_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Активность не найдена")
    return activity


def _build_activity_response(item: UserActivity) -> UserActivityResponse:
    return UserActivityResponse(
        id=item.id,
        user_id=item.user_id,
        user_name=item.user.full_name if item.user else "Unknown",
        activity_type_id=item.activity_type_id,
        activity_type_name=item.activity_type.activity_name if item.activity_type else "Unknown",
        activity_date=item.activity_date,
        earned_points=item.earned_points,
        description=item.description,
        notes=item.notes,
    )


@router.get("/activities", response_model=PaginatedUserActivityResponse)
def get_activities(
    page: int = 1,
    per_page: int = 10,
    user_id: int = None,
    activity_type_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить активности пользователей.

    Что делает:
    Возвращает список активностей. Студент видит только свои записи,
    сотрудники — записи всех пользователей.

    Что принимает:
    Query-параметры:
    - `page`
    - `per_page`
    - `user_id`
    - `activity_type_id`

    Что возвращает:
    Пагинированный список активностей.
    """
    skip = (page - 1) * per_page
    query = db.query(UserActivity).options(
        joinedload(UserActivity.user),
        joinedload(UserActivity.activity_type),
    )

    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    if activity_type_id:
        query = query.filter(UserActivity.activity_type_id == activity_type_id)

    if not can_manage_activities(current_user):
        query = query.filter(UserActivity.user_id == current_user.id)

    total = query.count()
    activities = (
        query.order_by(UserActivity.activity_date.desc(), UserActivity.id.desc())
        .offset(skip)
        .limit(per_page)
        .all()
    )

    return PaginatedUserActivityResponse(
        items=[_build_activity_response(item) for item in activities],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.get("/activities/{activity_id}", response_model=UserActivityResponse)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить одну активность по ID.
    """
    activity = _get_activity_or_404(db, activity_id)
    if not can_manage_activities(current_user) and activity.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра активности")
    return _build_activity_response(activity)


@router.post("/activities", response_model=UserActivityResponse)
def create_activity(
    activity: UserActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Создать активность пользователя.

    Что делает:
    Добавляет активность и пересчитывает итоговые баллы пользователя.

    Что принимает:
    ```json
    {
      "user_id": 5,
      "activity_type_id": 2,
      "activity_date": "2026-04-29T11:00:00",
      "earned_points": 10,
      "description": "Участие в мероприятии",
      "notes": "Помощь в организации"
    }
    ```

    Что возвращает:
    Объект созданной активности.
    """
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
        notes=activity.notes,
    )
    db.add(db_activity)
    sync_user_points(db, user)
    db.commit()

    return _build_activity_response(_get_activity_or_404(db, db_activity.id))


@router.delete("/activities/{activity_id}", response_model=dict)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Удалить активность пользователя.
    """
    db_activity = _get_activity_or_404(db, activity_id)
    user = db.query(User).filter(User.id == db_activity.user_id).first()

    db.delete(db_activity)
    if user:
        sync_user_points(db, user)
    db.commit()

    return {"message": "Активность успешно удалена", "activity_id": activity_id}
