from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CalendarContextMeta(BaseModel):
    user_dormitory_id: int | None = None
    user_block_id: int | None = None
    user_room_id: int | None = None


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    event_kind: str
    scope_type: str
    status: str = "scheduled"
    start_at: datetime
    end_at: datetime
    is_all_day: bool = False
    location: str | None = None
    dormitory_id: int | None = None
    block_id: int | None = None
    room_id: int | None = None
    related_news_id: int | None = None
    related_event_id: int | None = None
    metadata_json: dict[str, Any] | None = None


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    event_kind: str | None = None
    scope_type: str | None = None
    status: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_all_day: bool | None = None
    location: str | None = None
    dormitory_id: int | None = None
    block_id: int | None = None
    room_id: int | None = None
    related_news_id: int | None = None
    related_event_id: int | None = None
    metadata_json: dict[str, Any] | None = None


class CancelCalendarEventRequest(BaseModel):
    reason: str | None = None


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_kind: str
    scope_type: str
    status: str
    start_at: datetime
    end_at: datetime
    is_all_day: bool
    location: str | None = None
    dormitory_id: int | None = None
    dormitory_name: str | None = None
    block_id: int | None = None
    block_name: str | None = None
    room_id: int | None = None
    room_number: int | None = None
    created_by_id: int
    created_by_name: str | None = None
    updated_by_id: int | None = None
    updated_by_name: str | None = None
    related_news_id: int | None = None
    related_event_id: int | None = None
    source_type: str
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DormitoryBlockCreate(BaseModel):
    dormitory_id: int
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    kitchen_label: str | None = None


class DormitoryBlockUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    kitchen_label: str | None = None
    is_active: bool | None = None


class DormitoryBlockRoomBindRequest(BaseModel):
    room_id: int
    rotation_order: int = Field(..., ge=1)


class DormitoryBlockRoomUpdateRequest(BaseModel):
    rotation_order: int = Field(..., ge=1)


class DormitoryBlockRoomResponse(BaseModel):
    room_id: int
    room_number: int
    rotation_order: int


class DormitoryBlockResponse(BaseModel):
    id: int
    dormitory_id: int
    dormitory_name: str | None = None
    name: str
    description: str | None = None
    kitchen_label: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DormitoryBlockDetailResponse(DormitoryBlockResponse):
    rooms: list[DormitoryBlockRoomResponse]


class KitchenDutyPlanCreate(BaseModel):
    dormitory_id: int
    block_id: int
    month_start: date
    month_end: date
    comment: str | None = None


class KitchenDutyAssignmentResponse(BaseModel):
    id: int
    room_id: int
    room_number: int | None = None
    duty_date: date
    duty_order: int
    calendar_event_id: int
    event_status: str | None = None


class KitchenDutyPlanResponse(BaseModel):
    id: int
    dormitory_id: int
    dormitory_name: str | None = None
    block_id: int
    block_name: str | None = None
    month_start: date
    month_end: date
    status: str
    created_by_id: int
    created_by_name: str | None = None
    comment: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KitchenDutyPlanDetailResponse(KitchenDutyPlanResponse):
    rooms: list[DormitoryBlockRoomResponse]
    assignments: list[KitchenDutyAssignmentResponse]
    events: list[CalendarEventResponse]
