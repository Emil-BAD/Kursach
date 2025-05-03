from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NewsBase(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    category_id: int
    dormitory_id: Optional[int] = None
    is_private: Optional[bool] = False

class NewsCreate(NewsBase):
    pass

class NewsUpdate(NewsBase):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    dormitory_id: Optional[int] = None
    is_private: Optional[bool] = None

class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    author_id: int
    author_name: str
    image_url: Optional[str] = None
    category_id: int
    category_name: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    is_private: bool

    class Config:
        orm_mode = True

class PaginatedNewsResponse(BaseModel):
    items: List[NewsResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        orm_mode = True