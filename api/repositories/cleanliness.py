from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from api.db.models import CleanlinessHistory, Room


class CleanlinessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_room_by_id(self, room_id: int) -> Room | None:
        return (
            self.db.query(Room)
            .options(joinedload(Room.dormitory))
            .filter(Room.id == room_id)
            .first()
        )

    def list_room_history(
        self,
        *,
        room_id: int,
        since: datetime | None = None,
    ) -> list[CleanlinessHistory]:
        query = (
            self.db.query(CleanlinessHistory)
            .options(joinedload(CleanlinessHistory.assigned_by_user))
            .filter(CleanlinessHistory.room_id == room_id)
        )

        if since is not None:
            query = query.filter(CleanlinessHistory.assigned_at >= since)

        return (
            query.order_by(
                CleanlinessHistory.assigned_at.desc(),
                CleanlinessHistory.id.desc(),
            )
            .all()
        )
