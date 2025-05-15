# main.py
# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List
from api.core.dependencies import get_current_user, get_current_admin
from api.db.database import get_db
from api.db.models import User, Dormitory, CleanlinessHistory, Room, Role, UserViolation, ViolationType, UserActivity, ActivityType
from api.services.user import router as user_router
from api.services.news import router as news_router
from api.services.product import router as product_router
from api.services.auth import router as auth_router
from api.services.event import router as event_router
from api.services.event_registration import router as event_registration_router
from api.services.user_violations import router as user_violations_router
from api.services.cleanliness import router as cleanliness_router
from fastapi.middleware.cors import CORSMiddleware
from api.services.dormitory import router as dormitory_router
from api.services.favorite import router as favorite_router
from api.services.category import router as category_router
from api.schemas.user import UserResponse

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://your-frontend-domain.com",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, tags=["users"])
app.include_router(category_router, tags=["categories"])
app.include_router(favorite_router, tags=["favorite"])
app.include_router(dormitory_router, tags=["dormitory"])
app.include_router(cleanliness_router, tags=["cleanliness"])
app.include_router(user_violations_router, tags=["user_violations"])
app.include_router(news_router, tags=["news"])
app.include_router(event_router, tags=["event"])
app.include_router(event_registration_router, tags=["event_registration"])
app.include_router(product_router, tags=["product"])
app.include_router(auth_router, tags=["auth"])

@app.get("/users/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Получаем связанные данные
    dormitory = db.query(Dormitory).filter(Dormitory.id == current_user.dormitory_id).first() if current_user.dormitory_id else None
    room = db.query(Room).filter(Room.id == current_user.room_id).first() if current_user.room_id else None
    role = db.query(Role).filter(Role.id == current_user.role_id).first()

    # Получаем историю нарушений пользователя
    violations = db.query(UserViolation).filter(UserViolation.user_id == current_user.id).all()
    violation_responses = [
        {
            "id": violation.id,
            "user_id": violation.user_id,
            "user_name": current_user.full_name,
            "violation_type_id": violation.violation_type_id,
            "violation_type_name": db.query(ViolationType).filter(ViolationType.id == violation.violation_type_id).first().name if db.query(ViolationType).filter(ViolationType.id == violation.violation_type_id).first() else "Unknown",
            "violation_date": violation.violation_date,
            "penalty_points": violation.penalty_points,
            "description": violation.description,
            "created_at": violation.created_at
        }
        for violation in violations
    ]

    # Рассчитываем частоту нарушений комнаты
    room_violation_frequency = None
    if current_user.room_id:
        room_users = db.query(User).filter(User.room_id == current_user.room_id).all()
        room_user_ids = [user.id for user in room_users]
        room_violation_frequency = db.query(UserViolation).filter(UserViolation.user_id.in_(room_user_ids)).count()

    # Получаем активности пользователя с оптимизацией через join
    activities = (
        db.query(UserActivity)
        .join(ActivityType, UserActivity.activity_type_id == ActivityType.id)
        .filter(UserActivity.user_id == current_user.id)
        .all()
    )
    activity_responses = [
        {
            "id": activity.id,
            "activity_type_id": activity.activity_type_id,
            "activity_type_name": activity.activity_type.activity_name if activity.activity_type else "Unknown",
            "activity_date": activity.activity_date,
            "earned_points": activity.earned_points,  # Добавляем earned_points
            "description": activity.description,
            "notes": activity.notes  # Оставляем оба поля
        }
        for activity in activities
    ]

    # Формируем ответ
    return UserResponse(
        id=current_user.id,
        student_card=current_user.student_card,
        full_name=current_user.full_name,
        contact_number=current_user.contact_number,
        dormitory_id=current_user.dormitory_id,
        dormitory_name=dormitory.name if dormitory else None,
        room_id=current_user.room_id,
        room_number=room.room_number if room else None,
        group_number=current_user.group_number,
        specialization=current_user.specialization,
        role_id=current_user.role_id,
        role_name=role.role_name if role else "Unknown",
        role_description=role.role_description if role else None,
        email=current_user.email,
        phone=current_user.phone,
        birth_date=current_user.birth_date,
        course=current_user.course,
        faculty=current_user.faculty,
        created_at=current_user.created_at,
        points=current_user.points,
        social_links=current_user.social_links,
        violations=violation_responses,
        room_violation_frequency=room_violation_frequency,
        activities=activity_responses
    )

@app.get("/admin-only")
def admin_only(current_user: User = Depends(get_current_admin)):
    return {"message": "Привет, администратор!"}

@app.get("/cleanliness-history", response_model=List[dict])
def get_cleanliness_history(db: Session = Depends(get_db)):
    records = db.query(CleanlinessHistory).all()
    return [
        {
            "id": r.id,
            "room_id": r.room_id,
            "score": r.score,
            "assigned_by": r.assigned_by_user.full_name,
            "assigned_at": r.assigned_at.isoformat()
        }
        for r in records
    ]