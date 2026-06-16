from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Базовая схема без image_urls
class NewsBase(BaseModel):
    title: str
    content: str
    category_id: int
    dormitory_id: Optional[int] = None
    is_private: Optional[bool] = False
    calendar_start_at: Optional[datetime] = None
    calendar_end_at: Optional[datetime] = None

# Схема для создания (без image_urls, так как изображения будут загружаться отдельно)
class NewsCreate(NewsBase):
    pass

# Схема для обновления (без image_urls, так как изображения будут загружаться отдельно)
class NewsUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    dormitory_id: Optional[int] = None
    is_private: Optional[bool] = None
    calendar_start_at: Optional[datetime] = None
    calendar_end_at: Optional[datetime] = None
    clear_calendar_dates: Optional[bool] = False
    clear_calendar_end_at: Optional[bool] = False

# Схема ответа (с image_urls, так как они возвращаются из базы)
class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    author_id: int
    author_name: str
    image_urls: Optional[List[str]] = None
    category_id: int
    category_name: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    is_private: bool
    calendar_start_at: Optional[datetime] = None
    calendar_end_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedNewsResponse(BaseModel):
    items: List[NewsResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True
