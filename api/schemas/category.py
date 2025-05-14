# api/schemas/category.py
from pydantic import BaseModel
from typing import List

class CategoryResponse(BaseModel):
    id: int
    name: str
    entity_type: str

    class Config:
        from_attributes = True

class CategoriesResponse(BaseModel):
    items: List[CategoryResponse]