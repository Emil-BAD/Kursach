from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EventBase(BaseModel):
    title: str
    description: str
    event_date: datetime
    location: str
    category_id: int
    dormitory_id: Optional[int] = None
    status: Optional[str] = "open"
    is_private: Optional[bool] = False
    requirements: Optional[str] = None

class EventCreate(EventBase):
    pass  # Для создания события

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    category_id: Optional[int] = None
    dormitory_id: Optional[int] = None
    status: Optional[str] = None
    is_private: Optional[bool] = None
    requirements: Optional[str] = None

class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_date: datetime
    location: str
    created_at: datetime
    organizer_id: int
    organizer_name: str
    category_id: int
    category_name: str
    status: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    is_private: bool
    requirements: Optional[str] = None

    class Config:
        orm_mode = True

class PaginatedEventResponse(BaseModel):
    items: List[EventResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        orm_mode = True

class EventRegistrationCreate(BaseModel):
    event_id: int

class EventRegistrationUpdate(BaseModel):
    status: str  # "pending", "confirmed", "cancelled"

class EventRegistrationResponse(BaseModel):
    id: int
    event_id: int
    event_title: str
    user_id: int
    user_name: str
    status: str
    registered_at: datetime
    message: Optional[str] = None

    class Config:
        orm_mode = True

class PaginatedEventRegistrationResponse(BaseModel):
    items: List[EventRegistrationResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        orm_mode = True