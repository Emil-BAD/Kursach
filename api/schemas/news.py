from pydantic import BaseModel, Field
from datetime import date, datetime

class NewsCreate(BaseModel):
    title: str
    content: str
    image_url: str | None = None
    category_id: int
    dormitory_id: int
    is_private: bool = False

class NewsUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    image_url: str | None = None
    category_id: int | None = None
    dormitory_id: int | None = None
    is_private: bool | None = None

class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    author_id: int
    author_name: str
    image_url: str | None
    category_id: int
    category_name: str
    dormitory_id: int | None
    dormitory_name: str | None
    is_private: bool

    class Config:
        from_attributes = True

class PaginatedNewsResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[NewsResponse]