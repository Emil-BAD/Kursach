# api/schemas/product.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from fastapi import UploadFile

class ProductBase(BaseModel):
    title: str
    description: str
    price: float
    category_id: int
    dormitory_id: Optional[int] = None

class ProductCreate(ProductBase):
    image_files: Optional[List[UploadFile]] = None  # Поддержка загрузки файлов

class ProductUpdate(ProductBase):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_files: Optional[List[UploadFile]] = None  # Для обновления можно загружать новые файлы
    category_id: Optional[int] = None
    dormitory_id: Optional[int] = None
    status: Optional[str] = None

class ProductModeration(BaseModel):
    status: str  # "pending", "approved", "rejected"
    rejection_reason: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    seller_id: int
    seller_name: str
    created_at: datetime
    image_urls: Optional[dict] = None  # Список URL-адресов изображений
    category_id: int
    category_name: str
    status: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    seller_telegram: Optional[str] = None
    seller_vk: Optional[str] = None

    class Config:
        orm_mode = True

class PaginatedProductResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        orm_mode = True