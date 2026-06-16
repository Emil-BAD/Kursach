# -*- coding: utf-8 -*-
from typing import Optional

from pydantic import BaseModel


class DormitorySummaryResponse(BaseModel):
    dormitory_id: int
    dormitory_name: str
    total_rooms: int
    total_places: int
    occupied_places: int
    free_places: int
    occupancy_percent: float


class DisciplineUserReportResponse(BaseModel):
    user_id: int
    full_name: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    room_id: Optional[int] = None
    room_number: Optional[int] = None
    total_points: int
    violation_count: int
    penalty_points: int
    activity_count: int
    earned_points: int


class DisciplineSummaryResponse(BaseModel):
    items: list[DisciplineUserReportResponse]
    total_users: int
    total_violations: int
    total_penalty_points: int
    total_earned_points: int
