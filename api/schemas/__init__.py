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
    ProductStatus,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    PaginatedProductResponse
)

# Импортируем схемы из event.py
from .event import (
    EventStatus,
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
    "NewsCreate",
    "NewsUpdate",
    "NewsResponse",
    "PaginatedNewsResponse",
    # Product
    "ProductStatus",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "PaginatedProductResponse",
    # Event
    "EventStatus",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "PaginatedEventResponse",
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