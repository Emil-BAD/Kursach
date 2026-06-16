from pydantic import BaseModel, Field
from datetime import date, datetime

class CleanlinessHistoryCreate(BaseModel):
    room_id: int
    score: int = Field(ge=2, le=5)

class CleanlinessHistoryResponse(BaseModel):
    id: int
    room_id: int
    score: int
    assigned_by: int
    assigned_at: datetime
    inspector_name: str | None = None
    assigned_by_name: str | None = None

    class Config:
        from_attributes = True


class RoomCleanlinessRoomInfo(BaseModel):
    id: int
    room_number: int
    dormitory_id: int
    dormitory_name: str | None = None
    cleanliness_points: int


class RoomCleanlinessHistoryItem(BaseModel):
    id: int
    room_id: int
    score: int
    assigned_by: int
    assigned_at: datetime
    inspector_name: str | None = None
    comment: str | None = None


class RoomCleanlinessChartPoint(BaseModel):
    date: date
    score: int


class RoomCleanlinessSummaryResponse(BaseModel):
    room: RoomCleanlinessRoomInfo
    current_score: int
    average_score: float
    inspection_count: int
    last_checked_at: datetime | None = None
    history: list[RoomCleanlinessHistoryItem] = Field(default_factory=list)
    chart: list[RoomCleanlinessChartPoint] = Field(default_factory=list)
