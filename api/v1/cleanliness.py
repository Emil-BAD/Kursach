from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import User
from api.schemas.cleanliness import RoomCleanlinessSummaryResponse
from api.services.cleanliness_v1_service import CleanlinessV1Service


router = APIRouter(prefix="/api/v1/cleanliness", tags=["cleanliness-v1"])


@router.get("/my-room", response_model=RoomCleanlinessSummaryResponse)
def get_my_room_cleanliness(
    period: str = Query(
        "week",
        description="Период истории проверок: week, month или all",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить текущий балл чистоты и историю проверок комнаты студента.

    Endpoint всегда возвращает summary по комнате, даже если проверок ещё нет.
    Источник текущего балла: `rooms.cleanliness_points`.
    """
    return CleanlinessV1Service(db).get_my_room_summary(
        current_user=current_user,
        period=period,
    )
