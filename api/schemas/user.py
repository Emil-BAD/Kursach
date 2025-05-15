# api/schemas/user.py
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Dict, List
from api.schemas.user_violations import UserViolationResponse

class UserCreate(BaseModel):
    student_card: str
    password_hash: str
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
    social_links: Optional[Dict[str, str]] = None

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
    social_links: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    student_card: str
    password: str
    full_name: str
    contract_number: int
    role_id: int
    dormitory_id: int | None = None
    room_id: int | None = None
    group_number: int | None = None
    specialization: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None
    course: int | None = None
    faculty: str | None = None
    social_links: Optional[Dict[str, str]] = None

class UserActivityResponse(BaseModel):
    id: int
    activity_type_id: int
    activity_type_name: str
    activity_date: datetime
    notes: Optional[str] = None
    points_added: int

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    student_card: str
    full_name: str
    contact_number: int
    dormitory_id: int
    dormitory_name: str | None
    room_id: Optional[int] = None
    room_number: Optional[int] = None
    group_number: int | None
    specialization: str | None
    role_id: int
    role_name: str
    role_description: Optional[str] = None
    email: str | None
    phone: str | None
    birth_date: date | None
    course: int | None
    faculty: str | None
    created_at: datetime
    points: dict
    social_links: Optional[Dict[str, str]] = None
    violations: Optional[List[UserViolationResponse]] = []
    room_violation_frequency: Optional[int] = None
    activities: Optional[List[UserActivityResponse]] = []  # Добавляем поле активностей

    class Config:
        from_attributes = True

class PointsHistory(BaseModel):
    change: int
    reason: str
    date: datetime

class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int = Field(ge=1, default=1)
    size: int = Field(ge=1, le=100, default=10)
    total_pages: int

    class Config:
        from_attributes = True