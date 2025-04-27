from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum

class ProductStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ProductCreate(BaseModel):
    title: str
    description: str
    price: float
    image_url: list[str] | None = None
    category_id: int
    dormitory_id: int

class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    image_url: list[str] | None = None
    category_id: int | None = None
    dormitory_id: int | None = None
    status: ProductStatus | None = None
    rejection_reason: str | None = None

class ProductResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    seller_id: int
    seller_name: str
    created_at: datetime
    image_url: list[str] | None
    category_id: int
    category_name: str
    dormitory_id: int
    dormitory_name: str
    status: ProductStatus
    rejection_reason: str | None
    
    class Config:
        from_attributes = True

class PaginatedProductResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[ProductResponse]