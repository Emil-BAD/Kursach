from pydantic import BaseModel, Field
from datetime import date, datetime

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

class UserResponse(BaseModel):
    id: int
    student_card: str
    full_name: str
    contact_number: int
    dormitory_id: int
    dormitory_name: str
    room_id: int
    room_number: int
    group_number: int | None
    specialization: str | None
    role_id: int
    role_name: str
    email: str | None
    phone: str | None
    birth_date: date
    course: int
    faculty: str
    created_at: datetime
    points: dict
    
    class Config:
        from_attributes = True

class PointsHistory(BaseModel):
    change: int
    reason: str
    date: datetime

class PaginatedUserResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int = Field(ge=1, default=1)
    size: int = Field(ge=1, le=100, default=10)
    total_pages: int

    class Config:
        from_attributes = True