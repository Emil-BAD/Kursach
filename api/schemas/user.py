from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class UserCreate(BaseModel):
    student_card: str
    full_name: str
    contact_number: int
    dormitory_id: int
    room_id: int
    group_number: int | None
    specialization: str | None
    role_id: int
    email: str | None
    phone: str | None
    birth_date: date
    course: int
    faculty: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    contact_number: Optional[int] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    group_number: Optional[int] = None
    specialization: Optional[str] = None
    role_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    course: Optional[int] = None
    faculty: Optional[str] = None

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    student_card: str
    password: str
    full_name: str
    contract_number: int
    role_id: int
    dormitory_id: int = None
    room_id: int = None
    group_number: int = None
    specialization: str = None
    email: str = None
    phone: str = None
    birth_date: str = None
    course: int = None
    faculty: str = None

from typing import List

class UserResponse(BaseModel):
    id: int
    student_card: str
    full_name: str
    contact_number: int
    dormitory_id: int
    dormitory_name: str | None  # Сделали опциональным
    room_id: int
    room_number: int
    group_number: int | None
    specialization: str | None
    role_id: int
    role_name: str
    email: str | None
    phone: str | None
    birth_date: date | None  # Сделали опциональным
    course: int | None  # Сделали опциональным
    faculty: str | None  # Сделали опциональным
    created_at: datetime
    points: dict
    
    class Config:
        from_attributes = True

class PointsHistory(BaseModel):
    change: int
    reason: str
    date: datetime

class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]  # Используем List для явной типизации
    total: int
    page: int = Field(ge=1, default=1)
    size: int = Field(ge=1, le=100, default=10)
    total_pages: int

    class Config:
        from_attributes = True