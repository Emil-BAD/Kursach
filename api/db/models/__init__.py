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
from api.db.models.service_request import ServiceRequest
from api.db.models.service_request_comment import ServiceRequestComment
from api.db.models.service_request_attachment import ServiceRequestAttachment
from api.db.models.residence_history import ResidenceHistory
from api.db.models.payment import Payment
from api.db.models.payment_account_settings import PaymentAccountSettings
from api.db.models.payment_top_up import PaymentTopUp
from api.db.models.dormitory_block import DormitoryBlock
from api.db.models.dormitory_block_room import DormitoryBlockRoom
from api.db.models.calendar_event import CalendarEvent
from api.db.models.kitchen_duty_plan import KitchenDutyPlan
from api.db.models.kitchen_duty_assignment import KitchenDutyAssignment
from api.db.models.rental_listing import RentalListing
from api.db.models.rental_booking import RentalBooking

__all__ = [
    "Base",
    "Role",
    "Dormitory",
    "Room",
    "Category",
    "Event",
    "EventRegistration",
    "CleanlinessHistory",
    "FavoriteProduct",
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
    "RefreshToken",
    "ServiceRequest",
    "ServiceRequestComment",
    "ServiceRequestAttachment",
    "ResidenceHistory",
    "Payment",
    "PaymentAccountSettings",
    "PaymentTopUp",
    "DormitoryBlock",
    "DormitoryBlockRoom",
    "CalendarEvent",
    "KitchenDutyPlan",
    "KitchenDutyAssignment",
    "RentalListing",
    "RentalBooking",
]
