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

class UserResponse(BaseModel):
    id: int
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
    created_at: datetime
    
    class Config:
        from_attributes = True