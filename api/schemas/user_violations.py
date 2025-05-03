from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# ... (существующие схемы, например UserResponse, EventResponse, NewsResponse)

class UserViolationBase(BaseModel):
    user_id: int
    violation_type_id: int
    violation_date: datetime
    penalty_points: int
    description: str

class UserViolationCreate(UserViolationBase):
    pass

class UserViolationUpdate(BaseModel):
    violation_date: Optional[datetime] = None
    penalty_points: Optional[int] = None
    description: Optional[str] = None

class UserViolationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    violation_type_id: int
    violation_type_name: str
    violation_date: datetime
    penalty_points: int
    description: str
    created_at: datetime

    class Config:
        orm_mode = True

class PaginatedUserViolationResponse(BaseModel):
    items: List[UserViolationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        orm_mode = True

# ... (остальные схемы остаются без изменений)