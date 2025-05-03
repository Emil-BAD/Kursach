from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum

class EventStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    
class EventCreate(BaseModel):
    title: str
    description: str
    location: str
    event_date: datetime
    image_urls: list[str] | None = None
    category_id: int
    dormitory_id: int
    is_private: bool = False

class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None 
    location: str | None = None
    image_urls: list[str] | None = None
    category_id: int | None = None
    dormitory_id: int | None = None
    status: EventStatus | None = None
    is_private: bool | None = None

class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_date: datetime
    created_at: datetime
    organizer_id: int
    organizer_name: str
    location: str
    image_urls: list[str] | None = None
    category_id: int
    dormitory_id: int
    dormitory_name: str
    status: EventStatus
    is_private: bool
    
    class Config:
        from_attributes = True

class PaginatedEventResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[EventResponse]
    