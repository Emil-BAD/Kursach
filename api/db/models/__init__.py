# -*- coding: utf-8 -*-
# Импортируем все модели в правильном порядке, чтобы избежать циклических зависимостей

from api.db.models.base import Base
from api.db.models.role import Role
from api.db.models.dormitory import Dormitory
from api.db.models.room import Room
from api.db.models.category import Category
from api.db.models.event import Event
from api.db.models.event_registration import EventRegistration
from api.db.models.user import User
from api.db.models.violation_type import ViolationType
from api.db.models.user_violation import UserViolation
from api.db.models.activity_type import ActivityType
from api.db.models.user_activity import UserActivity
from api.db.models.news import News
from api.db.models.product import Product
from api.db.models.product_moderation_log import ProductModerationLog
from api.db.models.notification_settings import NotificationSettings
from api.db.models.notification import Notification
from api.db.models.cleanliness_history import CleanlinessHistory
from api.db.models.action_log import ActionLog
from api.db.models.refresh_token import RefreshToken
from api.db.models.favoriteproduct import FavoriteProduct

__all__ = [
    "Base",
    "Role",
    "Dormitory",
    "Room",
    "Category",
    "Event",
    "EventRegistration",
    "CleanlinessHistory",
    "FavoriteProduct"
    "User",
    "ViolationType",
    "UserViolation",
    "ActivityType",
    "UserActivity",
    "News",
    "Product",
    "ProductModerationLog",
    "NotificationSettings",
    "Notification",
    "ActionLog",
    "RefreshToken"
]