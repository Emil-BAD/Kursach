from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import User, UserViolation, ViolationType
from api.schemas.user_violations import (
    PaginatedUserViolationResponse,
    UserViolationCreate,
    UserViolationResponse,
    UserViolationUpdate,
)
from api.services.user_helpers import can_view_discipline_for_all, sync_user_points

router = APIRouter()


def _get_violation_or_404(db: Session, violation_id: int) -> UserViolation:
    violation = (
        db.query(UserViolation)
        .options(joinedload(UserViolation.user), joinedload(UserViolation.violation_type))
        .filter(UserViolation.id == violation_id)
        .first()
    )
    if not violation:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")
    return violation


def _build_violation_response(item: UserViolation) -> UserViolationResponse:
    return UserViolationResponse(
        id=item.id,
        user_id=item.user_id,
        user_name=item.user.full_name if item.user else "Unknown",
        violation_type_id=item.violation_type_id,
        violation_type_name=item.violation_type.name if item.violation_type else "Unknown",
        violation_date=item.violation_date,
        penalty_points=item.penalty_points,
        description=item.description,
        created_at=item.created_at,
    )


@router.get("/user-violations", response_model=PaginatedUserViolationResponse)
def get_user_violations(
    page: int = 1,
    per_page: int = 10,
    user_id: int = None,
    violation_type_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список нарушений.

    Что делает:
    Админские роли видят общий список, студент — только свои нарушения.

    Что принимает:
    Query-параметры:
    - `page`
    - `per_page`
    - `user_id`
    - `violation_type_id`

    Что возвращает:
    Пагинированный список нарушений.
    """
    skip = (page - 1) * per_page
    query = db.query(UserViolation).options(
        joinedload(UserViolation.user),
        joinedload(UserViolation.violation_type),
    )

    if user_id:
        query = query.filter(UserViolation.user_id == user_id)
    if violation_type_id:
        query = query.filter(UserViolation.violation_type_id == violation_type_id)

    if not can_view_discipline_for_all(current_user):
        query = query.filter(UserViolation.user_id == current_user.id)

    total = query.count()
    violations = (
        query.order_by(UserViolation.violation_date.desc(), UserViolation.id.desc())
        .offset(skip)
        .limit(per_page)
        .all()
    )

    return PaginatedUserViolationResponse(
        items=[_build_violation_response(item) for item in violations],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.get("/user-violations/{violation_id}", response_model=UserViolationResponse)
def get_user_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить одно нарушение по ID.
    """
    violation = _get_violation_or_404(db, violation_id)
    if not can_view_discipline_for_all(current_user) and violation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра нарушения")
    return _build_violation_response(violation)


@router.post("/user-violations", response_model=UserViolationResponse)
def create_user_violation(
    violation: UserViolationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Создать нарушение пользователя.

    Что делает:
    Добавляет нарушение, затем пересчитывает баллы студента.

    Что принимает:
    ```json
    {
      "user_id": 5,
      "violation_type_id": 1,
      "violation_date": "2026-04-29T10:00:00",
      "penalty_points": 10,
      "description": "Шум после 23:00"
    }
    ```

    Что возвращает:
    Объект созданного нарушения.
    """
    user = db.query(User).filter(User.id == violation.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь с указанным ID не найден")

    violation_type = db.query(ViolationType).filter(ViolationType.id == violation.violation_type_id).first()
    if not violation_type:
        raise HTTPException(status_code=400, detail="Тип нарушения с указанным ID не найден")

    db_violation = UserViolation(
        user_id=violation.user_id,
        violation_type_id=violation.violation_type_id,
        violation_date=violation.violation_date,
        penalty_points=violation.penalty_points,
        description=violation.description,
    )
    db.add(db_violation)
    sync_user_points(db, user)
    db.commit()

    return _build_violation_response(_get_violation_or_404(db, db_violation.id))


@router.put("/user-violations/{violation_id}", response_model=UserViolationResponse)
def update_user_violation(
    violation_id: int,
    violation_update: UserViolationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Обновить нарушение пользователя.
    """
    db_violation = _get_violation_or_404(db, violation_id)

    for key, value in violation_update.model_dump(exclude_unset=True).items():
        setattr(db_violation, key, value)

    user = db.query(User).filter(User.id == db_violation.user_id).first()
    if user:
        sync_user_points(db, user)
    db.commit()

    return _build_violation_response(_get_violation_or_404(db, db_violation.id))


@router.delete("/user-violations/{violation_id}", response_model=dict)
def delete_user_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Удалить нарушение пользователя.
    """
    db_violation = _get_violation_or_404(db, violation_id)
    user = db.query(User).filter(User.id == db_violation.user_id).first()

    db.delete(db_violation)
    if user:
        sync_user_points(db, user)
    db.commit()

    return {"message": "Нарушение успешно удалено", "violation_id": violation_id}
