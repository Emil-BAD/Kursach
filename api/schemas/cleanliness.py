from pydantic import BaseModel, Field
from datetime import datetime

class CleanlinessHistoryCreate(BaseModel):
    room_id: int
    score: int = Field(ge=2, le=5)

class CleanlinessHistoryResponse(BaseModel):
    id: int
    room_id: int
    score: int
    assigned_by: int
    assigned_at: datetime

    class Config:
        from_attributes = True