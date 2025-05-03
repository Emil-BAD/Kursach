# Импортируем схемы из user.py
from .user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PointsHistory,
    PaginatedUserResponse
)

# Импортируем схемы из news.py
from .news import (
    NewsCreate,
    NewsUpdate,
    NewsResponse,
    PaginatedNewsResponse
)

# Импортируем схемы из product.py
from .product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductModeration,
    ProductResponse,
    PaginatedProductResponse
)

# Импортируем схемы из event.py
from .event import (
    EventBase,
    EventCreate,
    EventUpdate,
    EventResponse,
    PaginatedEventResponse
)

# Импортируем схемы из log.py
from .log import (
    ModerationAction,
    ActionLogResponse,
    ProductModerationLogResponse,
    CleanlinessHistoryResponse,
    PaginatedActionLogResponse,
    PaginatedProductModerationLogResponse,
    PaginatedCleanlinessHistoryResponse
)

# Импортируем схемы из notification.py
from .notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    PaginatedNotificationResponse,
    NotificationSettingsCreate,
    NotificationSettingsUpdate,
    NotificationSettingsResponse
)

# Экспортируем все схемы через __all__
__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "PointsHistory",
    "PaginatedUserResponse",
    # News
    "NewsBase",
    "NewsUpdate",
    "NewsResponse",
    "PaginatedNewsResponse",
    # Product
    "ProductBase",
    "ProductCreate",
    "ProductModeration",
    "ProductUpdate",
    "ProductResponse",
    "PaginatedProductResponse",
    # Event
    "EventBase",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "PaginatedEventResponse",
    # User_violations
    "UserViolationBase",
    "UserViolationCreate",
    "UserViolationUpdate",
    "UserViolationResponse",
    "PaginatedUserViolationResponse"
    # Log
    "ModerationAction",
    "ActionLogResponse",
    "ProductModerationLogResponse",
    "CleanlinessHistoryResponse",
    "PaginatedActionLogResponse",
    "PaginatedProductModerationLogResponse",
    "PaginatedCleanlinessHistoryResponse",
    # Notification
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationResponse",
    "PaginatedNotificationResponse",
    "NotificationSettingsCreate",
    "NotificationSettingsUpdate",
    "NotificationSettingsResponse"
]