from pydantic import BaseModel, Field
from typing import List

# Схема для общежития
class DormitoryResponse(BaseModel):
    id: int
    name: str
    address: str
    image_urls: List[str] | None = Field(default=None, max_items=10)  # Список ссылок, до 10 элементов

    class Config:
        from_attributes = True

# Схема для комнаты
class RoomResponse(BaseModel):
    id: int
    room_number: int
    capacity: int
    dormitory_id: int
    cleanliness_points: int

    class Config:
        from_attributes = True

# Схема для общежития с комнатами
class DormitoryWithRoomsResponse(BaseModel):
    id: int
    name: str
    address: str
    image_urls: List[str] | None = Field(default=None, max_items=10)  # Список ссылок, до 10 элементов
    rooms: List[RoomResponse]

    class Config:
        from_attributes = True