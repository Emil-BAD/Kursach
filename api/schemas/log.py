from pydantic import BaseModel
from datetime import datetime
from enum import Enum

# Перечисление для действия модерации
class ModerationAction(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"

# Схема для логов действий (action_logs)
class ActionLogResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    action_type: str
    entity_type: str
    entity_id: int
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

# Схема для логов модерации товаров (product_moderation_logs)
class ProductModerationLogResponse(BaseModel):
    id: int
    product_id: int
    moderator_id: int
    moderator_name: str
    action: ModerationAction
    reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True

# Схема для истории баллов за чистоту (cleanliness_history)
class CleanlinessHistoryResponse(BaseModel):
    id: int
    room_id: int
    points_change: int
    reason: str
    assigned_by: int
    assigned_by_name: str
    created_at: datetime

    class Config:
        from_attributes = True

# Пагинированные ответы для каждого типа логов
class PaginatedActionLogResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[ActionLogResponse]

class PaginatedProductModerationLogResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[ProductModerationLogResponse]

class PaginatedCleanlinessHistoryResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[CleanlinessHistoryResponse]