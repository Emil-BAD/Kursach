from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductBase(BaseModel):
    title: str
    description: str
    price: float
    image_urls: Optional[dict] = None
    category_id: int
    dormitory_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_urls: Optional[dict] = None
    category_id: Optional[int] = None
    dormitory_id: Optional[int] = None

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
    image_urls: Optional[dict] = None
    category_id: int
    category_name: str
    status: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    rejection_reason: Optional[str] = None

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