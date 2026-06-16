# -*- coding: utf-8 -*-
"""
Общие helper-функции для профиля пользователя и проверок ролей.

Здесь нет "магии" и сложных абстракций:
- простые функции для проверки ролей;
- сборка UserResponse в одном месте;
- единый пересчёт баллов пользователя.
"""
from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from api.db.models import (
    ActivityType,
    CleanlinessHistory,
    User,
    UserActivity,
    UserViolation,
    ViolationType,
)
from api.schemas.user import ActivityResponse, UserResponse, ViolationResponse

logger = logging.getLogger(__name__)


def user_has_role(user: User | None, *role_names: str) -> bool:
    """Проверяет роль пользователя по role.role_name."""
    return bool(user and user.role and user.role.role_name in set(role_names))


def is_admin(user: User | None) -> bool:
    return user_has_role(user, "admin")


def is_student(user: User | None) -> bool:
    return user_has_role(user, "student")


def can_manage_cleanliness(user: User | None) -> bool:
    return user_has_role(
        user,
        "admin",
        "commandant",
        "sanitary_commission_member",
        "sanitary_commission_head",
    )


def can_manage_news(user: User | None) -> bool:
    return user_has_role(user, "admin", "commandant", "educator", "council_president", "council_member")


def can_manage_events(user: User | None) -> bool:
    return user_has_role(
        user,
        "admin",
        "commandant",
        "educator",
        "council_president",
        "council_member",
    )


def can_manage_activities(user: User | None) -> bool:
    return user_has_role(
        user,
        "admin",
        "commandant",
        "educator",
        "council_president",
        "council_member",
    )


def can_view_discipline_for_all(user: User | None) -> bool:
    return user_has_role(user, "admin", "commandant", "educator")


def can_moderate_products(user: User | None) -> bool:
    return user_has_role(user, "admin", "commandant", "moderator")


def calculate_user_points(db: Session, user_id: int) -> dict:
    """
    Считает итоговые баллы студента.

    Базовая логика:
    - стартовое значение: 100;
    - минус штрафные баллы за нарушения;
    - плюс баллы за активности.
    """
    total_penalty = (
        db.query(func.coalesce(func.sum(UserViolation.penalty_points), 0))
        .filter(UserViolation.user_id == user_id)
        .scalar()
        or 0
    )
    total_earned = (
        db.query(func.coalesce(func.sum(UserActivity.earned_points), 0))
        .filter(UserActivity.user_id == user_id)
        .scalar()
        or 0
    )
    return {"total": max(0, 100 + int(total_earned) - int(total_penalty))}


def sync_user_points(db: Session, user: User) -> dict:
    """
    Пересчитывает и записывает баллы пользователя в поле users.points.

    Коммит здесь не делаем, чтобы вызывающий код сам управлял транзакцией.
    """
    user.points = calculate_user_points(db, user.id)
    return user.points


def _get_room_violation_frequency(db: Session, room_id: int | None) -> int | None:
    if room_id is None:
        return None

    room_user_ids = [
        row[0]
        for row in db.query(User.id).filter(User.room_id == room_id).all()
    ]
    if not room_user_ids:
        return 0

    return db.query(UserViolation).filter(UserViolation.user_id.in_(room_user_ids)).count()


def _build_violation_responses(db: Session, user_id: int, user_name: str) -> list[ViolationResponse]:
    violations = (
        db.query(UserViolation)
        .options(joinedload(UserViolation.violation_type))
        .filter(UserViolation.user_id == user_id)
        .order_by(UserViolation.violation_date.desc(), UserViolation.id.desc())
        .all()
    )

    return [
        ViolationResponse(
            id=item.id,
            user_id=item.user_id,
            user_name=user_name,
            violation_type_id=item.violation_type_id,
            violation_type_name=item.violation_type.name if item.violation_type else "Unknown",
            violation_date=item.violation_date,
            penalty_points=item.penalty_points,
            description=item.description,
            created_at=item.created_at,
        )
        for item in violations
    ]


def _build_activity_responses(db: Session, user_id: int) -> list[ActivityResponse]:
    activities = (
        db.query(UserActivity)
        .options(joinedload(UserActivity.activity_type))
        .filter(UserActivity.user_id == user_id)
        .order_by(UserActivity.activity_date.desc(), UserActivity.id.desc())
        .all()
    )

    return [
        ActivityResponse(
            id=item.id,
            activity_type_id=item.activity_type_id,
            activity_type_name=item.activity_type.activity_name if item.activity_type else "Unknown",
            activity_date=item.activity_date,
            earned_points=item.earned_points,
            description=item.description,
            notes=item.notes,
        )
        for item in activities
    ]


def build_user_response(
    db: Session,
    user: User,
    *,
    include_violations: bool = True,
    include_activities: bool = True,
    include_room_violation_frequency: bool = True,
) -> UserResponse:
    """
    Собирает UserResponse в одном месте.

    Это упрощает все endpoint'ы пользователей и гарантирует единый формат
    ответа для `/users`, `/users/me`, `/api/v1/me` и связанных разделов.
    """
    points = _safe_calculate_user_points(db, user)
    contact_number = user.contact_number if user.contact_number is not None else 0
    social_links = user.social_links if isinstance(user.social_links, dict) else {}
    user_points = points if isinstance(points, dict) else {"total": 0}
    violations = _safe_build_violation_responses(db, user.id, user.full_name, include_violations)
    activities = _safe_build_activity_responses(db, user.id, include_activities)
    room_violation_frequency = (
        _safe_room_violation_frequency(db, user.room_id)
        if include_room_violation_frequency
        else None
    )
    room_cleanliness_average = _safe_room_cleanliness_average(db, user.room_id)

    return UserResponse(
        id=user.id,
        student_card=user.student_card,
        full_name=user.full_name,
        contact_number=contact_number,
        dormitory_id=user.dormitory_id,
        dormitory_name=user.dormitory.name if user.dormitory else None,
        room_id=user.room_id,
        room_number=user.room.room_number if user.room else None,
        group_number=user.group_number,
        specialization=user.specialization,
        role_id=user.role_id,
        role_name=user.role.role_name if user.role else "Unknown",
        role_description=user.role.role_description if user.role else None,
        email=user.email,
        phone=user.phone,
        birth_date=user.birth_date,
        course=user.course,
        faculty=user.faculty,
        created_at=user.created_at,
        points=user_points,
        social_links=social_links,
        violations=violations,
        room_violation_frequency=room_violation_frequency,
        room_cleanliness_points=room_cleanliness_average,
        activities=activities,
    )


def _safe_calculate_user_points(db: Session, user: User) -> dict:
    if isinstance(user.points, dict):
        cached_total = user.points.get("total")
        if isinstance(cached_total, int):
            return user.points

    try:
        return calculate_user_points(db, user.id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to calculate points for user_id=%s", user.id)
        if isinstance(user.points, dict):
            return user.points
        return {"total": 0}


def _safe_build_violation_responses(
    db: Session,
    user_id: int,
    user_name: str,
    include_violations: bool,
) -> list[ViolationResponse]:
    if not include_violations:
        return []
    try:
        return _build_violation_responses(db, user_id, user_name)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to load violations for user_id=%s", user_id)
        return []


def _safe_build_activity_responses(
    db: Session,
    user_id: int,
    include_activities: bool,
) -> list[ActivityResponse]:
    if not include_activities:
        return []
    try:
        return _build_activity_responses(db, user_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to load activities for user_id=%s", user_id)
        return []


def _safe_room_violation_frequency(db: Session, room_id: int | None) -> int | None:
    try:
        return _get_room_violation_frequency(db, room_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to load room violation frequency for room_id=%s", room_id)
        return None


def _safe_room_cleanliness_average(db: Session, room_id: int | None) -> float | None:
    if room_id is None:
        return None

    try:
        average_score = (
            db.query(func.avg(CleanlinessHistory.score))
            .filter(CleanlinessHistory.room_id == room_id)
            .scalar()
        )
        if average_score is None:
            return None
        return round(float(average_score), 1)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to load room cleanliness average for room_id=%s", room_id)
        return None
