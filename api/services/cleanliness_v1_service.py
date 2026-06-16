from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.core.exceptions import BadRequestError, ForbiddenError, RoomNotFoundError, ValidationError
from api.db.models import CleanlinessHistory, Room, User
from api.repositories.cleanliness import CleanlinessRepository
from api.schemas.cleanliness import (
    RoomCleanlinessChartPoint,
    RoomCleanlinessHistoryItem,
    RoomCleanlinessRoomInfo,
    RoomCleanlinessSummaryResponse,
)


class CleanlinessV1Service:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CleanlinessRepository(db)

    def get_my_room_summary(
        self,
        *,
        current_user: User,
        period: str,
    ) -> RoomCleanlinessSummaryResponse:
        if current_user.dormitory_id is None:
            raise BadRequestError("У вас не указано общежитие")
        if current_user.room_id is None:
            raise BadRequestError("У вас не указана комната")

        room = self.repository.get_room_by_id(current_user.room_id)
        if room is None:
            raise RoomNotFoundError(current_user.room_id)
        if room.dormitory_id != current_user.dormitory_id:
            raise ForbiddenError("Комната не относится к вашему общежитию")

        since = self._period_to_since(period)
        history = self.repository.list_room_history(room_id=room.id, since=since)
        current_score = int(room.cleanliness_points or 0)

        return RoomCleanlinessSummaryResponse(
            room=self._serialize_room(room),
            current_score=current_score,
            average_score=self._calculate_average_score(history, current_score),
            inspection_count=len(history),
            last_checked_at=history[0].assigned_at if history else None,
            history=[self._serialize_history_item(item) for item in history],
            chart=self._build_chart(history),
        )

    def _period_to_since(self, period: str) -> datetime | None:
        now = datetime.utcnow()
        if period == "week":
            return now - timedelta(days=7)
        if period == "month":
            return now - timedelta(days=30)
        if period == "all":
            return None
        raise ValidationError("Недопустимый период. Используйте week, month или all")

    def _serialize_room(self, room: Room) -> RoomCleanlinessRoomInfo:
        return RoomCleanlinessRoomInfo(
            id=room.id,
            room_number=room.room_number,
            dormitory_id=room.dormitory_id,
            dormitory_name=room.dormitory.name if room.dormitory else None,
            cleanliness_points=int(room.cleanliness_points or 0),
        )

    def _serialize_history_item(
        self,
        item: CleanlinessHistory,
    ) -> RoomCleanlinessHistoryItem:
        return RoomCleanlinessHistoryItem(
            id=item.id,
            room_id=item.room_id,
            score=int(item.score),
            assigned_by=item.assigned_by,
            assigned_at=item.assigned_at,
            inspector_name=item.assigned_by_user.full_name if item.assigned_by_user else None,
            comment=None,
        )

    def _calculate_average_score(
        self,
        history: list[CleanlinessHistory],
        current_score: int,
    ) -> float:
        if not history:
            return float(current_score)
        total = sum(int(item.score or 0) for item in history)
        return round(total / len(history), 2)

    def _build_chart(self, history: list[CleanlinessHistory]) -> list[RoomCleanlinessChartPoint]:
        chart_history = list(reversed(history[:7]))
        return [
            RoomCleanlinessChartPoint(
                date=item.assigned_at.date(),
                score=int(item.score),
            )
            for item in chart_history
            if item.assigned_at is not None
        ]
