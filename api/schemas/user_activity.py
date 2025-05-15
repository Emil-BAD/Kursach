from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Схема для создания активности
class UserActivityCreate(BaseModel):
    user_id: int
    activity_type_id: int
    activity_date: datetime
    earned_points: int
    description: Optional[str] = None
    notes: Optional[str] = None

# Схема для обновления активности
class UserActivityUpdate(BaseModel):
    user_id: Optional[int] = None
    activity_type_id: Optional[int] = None
    activity_date: Optional[datetime] = None
    earned_points: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None

# Схема ответа для активности
class UserActivityResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    activity_type_id: int
    activity_type_name: str
    activity_date: datetime
    earned_points: int
    description: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True

# Схема пагинации
class PaginatedUserActivityResponse(BaseModel):
    items: list[UserActivityResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        orm_mode = True