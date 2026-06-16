# -*- coding: utf-8 -*-
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CheckInCreate(BaseModel):
    user_id: int
    dormitory_id: int
    room_id: int
    check_in_date: date
    comment: Optional[str] = None


class CheckOutUpdate(BaseModel):
    check_out_date: date
    eviction_reason: Optional[str] = None
    comment: Optional[str] = None


class ResidenceHistoryResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    dormitory_id: int
    dormitory_name: str
    room_id: int
    room_number: int
    check_in_date: date
    check_out_date: Optional[date] = None
    eviction_reason: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    is_active: bool


class ResidenceHistoryListResponse(BaseModel):
    items: list[ResidenceHistoryResponse]
    total: int


class RoomOccupancyResponse(BaseModel):
    room_id: int
    room_number: int
    dormitory_id: int
    dormitory_name: str
    capacity: int
    occupied_places: int
    free_places: int
    occupancy_percent: float


class DormitoryOccupancyResponse(BaseModel):
    dormitory_id: int
    dormitory_name: str
    total_rooms: int
    total_places: int
    occupied_places: int
    free_places: int
    occupancy_percent: float
