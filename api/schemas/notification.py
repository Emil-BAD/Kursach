from pydantic import BaseModel
from datetime import datetime

# Для создания уведомления (внутреннее использование в сервисах)
class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None

# Для обновления уведомления (PUT /api/v1/notifications/{id})
class NotificationUpdate(BaseModel):
    is_read: bool | None = None

# Для ответа (GET /api/v1/notifications, GET /api/v1/notifications/{id})
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime
    entity_type: str | None
    entity_id: int | None

    class Config:
        from_attributes = True

# Для пагинированного ответа (GET /api/v1/notifications)
class PaginatedNotificationResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[NotificationResponse]

# Для создания настроек уведомлений (при регистрации пользователя)
class NotificationSettingsCreate(BaseModel):
    user_id: int
    news_notifications: bool = True
    event_notifications: bool = True
    product_notifications: bool = True
    cleanliness_notifications: bool = True
    violation_notifications: bool = True

# Для обновления настроек (PUT /api/v1/notification-settings)
class NotificationSettingsUpdate(BaseModel):
    news_notifications: bool | None = None
    event_notifications: bool | None = None
    product_notifications: bool | None = None
    cleanliness_notifications: bool | None = None
    violation_notifications: bool | None = None

# Для ответа (GET /api/v1/notification-settings)
class NotificationSettingsResponse(BaseModel):
    id: int
    user_id: int
    news_notifications: bool
    event_notifications: bool
    product_notifications: bool
    cleanliness_notifications: bool
    violation_notifications: bool

    class Config:
        from_attributes = True