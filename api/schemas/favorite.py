# api/schemas/favorite.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class FavoriteBase(BaseModel):
    product_id: int

class FavoriteCreate(FavoriteBase):
    pass

class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime
    product: dict  # Вложенная информация о товаре

    class Config:
        from_attributes = True

class PaginatedFavoriteResponse(BaseModel):
    items: List[FavoriteResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True