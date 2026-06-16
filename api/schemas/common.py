# -*- coding: utf-8 -*-
"""
Базовые Pydantic схемы для всех роутеров.
Пагинация, ошибки, стандартные ответы.
"""
from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic, Optional

T = TypeVar('T')


class PaginatedRequest(BaseModel):
    """Базовые параметры пагинации для всех GET списков"""
    page: int = Field(1, ge=1, description="Номер страницы (начиная с 1)")
    page_size: int = Field(20, ge=1, le=100, description="Размер страницы (макс 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Единый формат для всех paginated ответов"""
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Стандартный формат ошибок"""
    error: str = Field(..., description="Тип ошибки")
    detail: str = Field(..., description="Детали ошибки")
    status_code: int = Field(..., description="HTTP статус код")


class SuccessResponse(BaseModel, Generic[T]):
    """Стандартный формат успешного ответа"""
    success: bool = True
    data: T
    message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ListResponse(BaseModel, Generic[T]):
    """Простой список без пагинации"""
    items: List[T]
    total: int
    
    class Config:
        from_attributes = True


def paginate_response(items: List[T], page: int, page_size: int, total: int) -> dict:
    """Вспомогательная функция для создания paginated ответа"""
    total_pages = (total + page_size - 1) // page_size
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
