from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from db.database import get_db
from db.models import UserViolation, User, ViolationType
from schemas.user_violations import UserViolationCreate, UserViolationUpdate, UserViolationResponse, PaginatedUserViolationResponse
from core.dependencies import get_current_user, get_current_admin

router = APIRouter()

@router.get("/user-violations", response_model=PaginatedUserViolationResponse)
def get_user_violations(
    page: int = 1,
    per_page: int = 10,
    user_id: int = None,
    violation_type_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * per_page
    query = db.query(UserViolation).options(
        joinedload(UserViolation.user),
        joinedload(UserViolation.violation_type)
    )

    # Фильтрация
    if user_id:
        query = query.filter(UserViolation.user_id == user_id)
    if violation_type_id:
        query = query.filter(UserViolation.violation_type_id == violation_type_id)

    # Ограничение доступа
    if current_user.role_id not in [1, 2, 3]:
        query = query.filter(UserViolation.user_id == current_user.id)

    total = query.count()
    violations = query.offset(skip).limit(per_page).all()

    violation_responses = []
    for violation in violations:
        violation_responses.append({
            "id": violation.id,
            "user_id": violation.user_id,
            "user_name": violation.user.full_name if violation.user else "Unknown",
            "violation_type_id": violation.violation_type_id,
            "violation_type_name": violation.violation_type.name if violation.violation_type else "Unknown",
            "violation_type_description": violation.violation_type.description if violation.violation_type else None,
            "violation_type_default_penalty_points": violation.violation_type.default_penalty_points if violation.violation_type else None,
            "violation_date": violation.violation_date.isoformat(),
            "penalty_points": violation.penalty_points,
            "description": violation.description,
            "created_at": violation.created_at.isoformat()
        })

    total_pages = (total + per_page - 1) // per_page

    return PaginatedUserViolationResponse(
        items=violation_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/user-violations/{violation_id}", response_model=UserViolationResponse)
def get_user_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    violation = db.query(UserViolation).options(
        joinedload(UserViolation.user),
        joinedload(UserViolation.violation_type)
    ).filter(UserViolation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")

    if current_user.role_id not in [1, 2, 3] and violation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра нарушения")

    return {
        "id": violation.id,
        "user_id": violation.user_id,
        "user_name": violation.user.full_name if violation.user else "Unknown",
        "violation_type_id": violation.violation_type_id,
        "violation_type_name": violation.violation_type.name if violation.violation_type else "Unknown",
        "violation_type_description": violation.violation_type.description if violation.violation_type else None,
        "violation_type_default_penalty_points": violation.violation_type.default_penalty_points if violation.violation_type else None,
        "violation_date": violation.violation_date.isoformat(),
        "penalty_points": violation.penalty_points,
        "description": violation.description,
        "created_at": violation.created_at.isoformat()
    }

@router.post("/user-violations", response_model=UserViolationResponse)
def create_user_violation(
    violation: UserViolationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
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
        description=violation.description
    )
    db.add(db_violation)
    db.commit()
    db.refresh(db_violation)

    user = db.query(User).filter(User.id == db_violation.user_id).first()
    violation_type = db.query(ViolationType).filter(ViolationType.id == db_violation.violation_type_id).first()

    return {
        "id": db_violation.id,
        "user_id": db_violation.user_id,
        "user_name": user.full_name if user else "Unknown",
        "violation_type_id": db_violation.violation_type_id,
        "violation_type_name": violation_type.name if violation_type else "Unknown",
        "violation_type_description": violation_type.description if violation_type else None,
        "violation_type_default_penalty_points": violation_type.default_penalty_points if violation_type else None,
        "violation_date": db_violation.violation_date.isoformat(),
        "penalty_points": db_violation.penalty_points,
        "description": db_violation.description,
        "created_at": db_violation.created_at.isoformat()
    }

@router.put("/user-violations/{violation_id}", response_model=UserViolationResponse)
def update_user_violation(
    violation_id: int,
    violation_update: UserViolationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_violation = db.query(UserViolation).filter(UserViolation.id == violation_id).first()
    if not db_violation:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")

    for key, value in violation_update.dict(exclude_unset=True).items():
        setattr(db_violation, key, value)

    db.commit()
    db.refresh(db_violation)

    user = db.query(User).filter(User.id == db_violation.user_id).first()
    violation_type = db.query(ViolationType).filter(ViolationType.id == db_violation.violation_type_id).first()

    return {
        "id": db_violation.id,
        "user_id": db_violation.user_id,
        "user_name": user.full_name if user else "Unknown",
        "violation_type_id": db_violation.violation_type_id,
        "violation_type_name": violation_type.name if violation_type else "Unknown",
        "violation_type_description": violation_type.description if violation_type else None,
        "violation_type_default_penalty_points": violation_type.default_penalty_points if violation_type else None,
        "violation_date": db_violation.violation_date.isoformat(),
        "penalty_points": db_violation.penalty_points,
        "description": db_violation.description,
        "created_at": db_violation.created_at.isoformat()
    }

@router.delete("/user-violations/{violation_id}", response_model=dict)
def delete_user_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_violation = db.query(UserViolation).filter(UserViolation.id == violation_id).first()
    if not db_violation:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")

    db.delete(db_violation)
    db.commit()

    return {"message": "Нарушение успешно удалено", "violation_id": violation_id}