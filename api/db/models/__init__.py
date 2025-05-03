# -*- coding: utf-8 -*-
# Импортируем все модели в правильном порядке, чтобы избежать циклических зависимостей

from db.models.base import Base
from db.models.role import Role
from db.models.dormitory import Dormitory
from db.models.room import Room
from db.models.category import Category
from db.models.event import Event
from db.models.event_registration import EventRegistration
from db.models.user import User
from db.models.violation_type import ViolationType
from db.models.user_violation import UserViolation
from db.models.activity_type import ActivityType
from db.models.user_activity import UserActivity
from db.models.news import News
from db.models.product import Product
from db.models.product_moderation_log import ProductModerationLog
from db.models.notification_settings import NotificationSettings
from db.models.notification import Notification
from db.models.cleanliness_history import CleanlinessHistory
from db.models.action_log import ActionLog
from db.models.refresh_token import RefreshToken

__all__ = [
    "Base",
    "Role",
    "Dormitory",
    "Room",
    "Category",
    "Event",
    "EventRegistration",
    "CleanlinessHistory",
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