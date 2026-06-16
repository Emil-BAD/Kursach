# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

# Позволяет запускать приложение двумя способами:
# 1. из корня проекта: `uvicorn api.app:app --reload`
# 2. из папки api: `uvicorn app:app --reload`
#
# Во втором случае Python не видит пакет `api`, потому что текущая директория
# становится корнем импорта. Добавляем родительскую папку проекта в sys.path.
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.core.config import settings
from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db, init_db
from api.db.models import (
    ActivityType,
    CleanlinessHistory,
    Dormitory,
    Role,
    Room,
    User,
    UserActivity,
    UserViolation,
    ViolationType,
)
from api.schemas.user import UserResponse
from api.services.cleanliness import check_user_role
from api.services.user_helpers import build_user_response

# ========== V1/V2 роутеры (новая архитектура) ==========
from api.v1 import auth, users, news, calendar, admin, cleanliness as cleanliness_v1
from api.v2 import payments as payments_v2

# ========== Старые роутеры (для совместимости) ==========
# TODO: Постепенно мигрировать на v1 версию
from api.services.auth import router as auth_router_old
from api.services.user import router as user_router_old
from api.services.news import router as news_router
from api.services.product import router as product_router
from api.services.event import router as event_router
from api.services.event_registration import router as event_registration_router
from api.services.user_violations import router as user_violations_router
from api.services.cleanliness import router as cleanliness_router
from api.services.dormitory import router as dormitory_router
from api.services.favorite import router as favorite_router
from api.services.category import router as category_router
from api.services.activities import router as activities_router
from api.services.directories import router as directories_router
from api.services.payments import router as payments_router
from api.services.rentals import router as rentals_router, legacy_router as rentals_legacy_router
from api.services.reports import router as reports_router
from api.services.residence import router as residence_router
from api.services.service_requests import router as service_requests_router

# Инициализация FastAPI
app = FastAPI(
    title="Dormitory Management API",
    description="API для управления общежитиями. Этап 2: новая архитектура.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.on_event("startup")
def startup_event():
    init_db()

# ========== CORS Middleware ==========
allowed_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Регистрация V1 роутеров (новая архитектура) ==========
print("[INFO] Регистрирую V1 роутеры (новая архитектура)...")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(news.router)
app.include_router(calendar.router)
app.include_router(admin.router)
app.include_router(cleanliness_v1.router)
print("[INFO] Регистрирую V2 роутеры (новая архитектура)...")
app.include_router(payments_v2.router)

# ========== Регистрация старых роутеров (для совместимости) ==========
print("[INFO] Регистрирую старые роутеры (для совместимости)...")
app.include_router(user_router_old, tags=["users-legacy"])
app.include_router(activities_router, tags=["activities"])
app.include_router(category_router, tags=["categories"])
app.include_router(favorite_router, tags=["favorite"])
app.include_router(dormitory_router, tags=["dormitory"])
app.include_router(cleanliness_router, tags=["cleanliness"])
app.include_router(user_violations_router, tags=["user_violations"])
app.include_router(news_router, tags=["news"])
app.include_router(event_router, tags=["event"])
app.include_router(event_registration_router, tags=["event_registration"])
app.include_router(product_router, tags=["product"])
app.include_router(auth_router_old, tags=["auth"])
app.include_router(service_requests_router, tags=["service_requests"])
app.include_router(residence_router, tags=["residence"])
app.include_router(payments_router, tags=["payments"])
app.include_router(rentals_router, tags=["rentals"])
app.include_router(rentals_legacy_router, tags=["rentals-legacy"])
app.include_router(reports_router, tags=["reports"])
app.include_router(directories_router, tags=["directories"])

@app.get("/users/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Профиль текущего пользователя (кто вошёл по Bearer-токену).

    Принимает: заголовок Authorization: Bearer <access_token>, тело не нужно.

    Возвращает JSON (UserResponse): билет, ФИО, общежитие, комната, баллы, нарушения, активности и т.д.
    """
    return build_user_response(
        db,
        current_user,
        include_room_violation_frequency=False,
    )

@app.get("/admin-only")
def admin_only(current_user: User = Depends(get_current_admin)):
    """
    Тестовый эндпоинт: доступен только администратору (по роли в БД).

    Принимает: Authorization: Bearer <token>

    Возвращает: {"message": "Привет, администратор!"}
    """
    return {"message": "Привет, администратор!"}


@app.get("/cleanliness-history", response_model=List[dict])
def get_cleanliness_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Полная история оценок чистоты по комнатам (для санкомиссии / админки).

    Раньше был открыт без авторизации — это дыра в безопасности. Теперь:
      - нужен Bearer access-токен;
      - те же роли, что и для POST /cleanliness (см. check_user_role в cleanliness.py).

    Принимает: Authorization: Bearer <token>

    Возвращает JSON-массив, пример элемента:
      {"id": 1, "room_id": 5, "score": 4, "assigned_by": "Иванов И.И.", "assigned_at": "2025-01-01T12:00:00"}
    """
    check_user_role(current_user)
    records = (
        db.query(CleanlinessHistory)
        .options(joinedload(CleanlinessHistory.assigned_by_user))
        .order_by(CleanlinessHistory.assigned_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "room_id": r.room_id,
            "score": r.score,
            "assigned_by": r.assigned_by_user.full_name if r.assigned_by_user else "Unknown",
            "assigned_at": r.assigned_at.isoformat() if r.assigned_at else "",
        }
        for r in records
    ]

