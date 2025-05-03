from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class ViolationTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_penalty_points: Optional[int] = None


class ViolationTypeCreate(ViolationTypeBase):
    pass

class ViolationTypeUpdate(ViolationTypeBase):
    name: Optional[str] = None
    description: Optional[str] = None
    default_penalty_points: Optional[int] = None

class ViolationTypeResponse(ViolationTypeBase):
    id: int

    class Config:
        orm_mode = True