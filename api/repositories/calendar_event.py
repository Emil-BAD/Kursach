from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from api.db.models import CalendarEvent
from api.repositories.base import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    def __init__(self, db: Session):
        super().__init__(db, CalendarEvent)

    def _base_query(self):
        return self.db.query(CalendarEvent).options(
            joinedload(CalendarEvent.dormitory),
            joinedload(CalendarEvent.block),
            joinedload(CalendarEvent.room),
            joinedload(CalendarEvent.created_by),
            joinedload(CalendarEvent.updated_by),
            joinedload(CalendarEvent.related_news),
            joinedload(CalendarEvent.related_event),
        )

    def get_with_relations(self, event_id: int) -> CalendarEvent | None:
        return self._base_query().filter(CalendarEvent.id == event_id).first()

    def list_filtered(
        self,
        *,
        skip: int,
        limit: int,
        can_view_all: bool,
        user_dormitory_id: int | None,
        user_block_id: int | None,
        user_room_id: int | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_kind: str | None = None,
        status: str | None = None,
        scope_type: str | None = None,
        dormitory_id: int | None = None,
        block_id: int | None = None,
        room_id: int | None = None,
    ) -> list[CalendarEvent]:
        query = self._apply_filters(
            self._base_query(),
            can_view_all=can_view_all,
            user_dormitory_id=user_dormitory_id,
            user_block_id=user_block_id,
            user_room_id=user_room_id,
            date_from=date_from,
            date_to=date_to,
            event_kind=event_kind,
            status=status,
            scope_type=scope_type,
            dormitory_id=dormitory_id,
            block_id=block_id,
            room_id=room_id,
        )
        return (
            query.order_by(CalendarEvent.start_at.asc(), CalendarEvent.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_filtered(
        self,
        *,
        can_view_all: bool,
        user_dormitory_id: int | None,
        user_block_id: int | None,
        user_room_id: int | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_kind: str | None = None,
        status: str | None = None,
        scope_type: str | None = None,
        dormitory_id: int | None = None,
        block_id: int | None = None,
        room_id: int | None = None,
    ) -> int:
        query = self._apply_filters(
            self.db.query(CalendarEvent),
            can_view_all=can_view_all,
            user_dormitory_id=user_dormitory_id,
            user_block_id=user_block_id,
            user_room_id=user_room_id,
            date_from=date_from,
            date_to=date_to,
            event_kind=event_kind,
            status=status,
            scope_type=scope_type,
            dormitory_id=dormitory_id,
            block_id=block_id,
            room_id=room_id,
        )
        return query.count()

    def list_my_duty(
        self,
        *,
        room_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> list[CalendarEvent]:
        query = self._base_query().filter(
            CalendarEvent.event_kind == "kitchen_duty",
            CalendarEvent.room_id == room_id,
        )
        if date_from is not None:
            query = query.filter(CalendarEvent.end_at >= date_from)
        if date_to is not None:
            query = query.filter(CalendarEvent.start_at <= date_to)
        return query.order_by(CalendarEvent.start_at.asc(), CalendarEvent.id.asc()).limit(limit).all()

    def list_by_ids(self, ids: list[int]) -> list[CalendarEvent]:
        if not ids:
            return []
        return self._base_query().filter(CalendarEvent.id.in_(ids)).all()

    def _apply_filters(
        self,
        query,
        *,
        can_view_all: bool,
        user_dormitory_id: int | None,
        user_block_id: int | None,
        user_room_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        event_kind: str | None,
        status: str | None,
        scope_type: str | None,
        dormitory_id: int | None,
        block_id: int | None,
        room_id: int | None,
    ):
        if date_from is not None:
            query = query.filter(CalendarEvent.end_at >= date_from)
        if date_to is not None:
            query = query.filter(CalendarEvent.start_at <= date_to)
        if event_kind:
            query = query.filter(CalendarEvent.event_kind == event_kind)
        if status:
            query = query.filter(CalendarEvent.status == status)
        if scope_type:
            query = query.filter(CalendarEvent.scope_type == scope_type)
        if dormitory_id is not None:
            query = query.filter(CalendarEvent.dormitory_id == dormitory_id)
        if block_id is not None:
            query = query.filter(CalendarEvent.block_id == block_id)
        if room_id is not None:
            query = query.filter(CalendarEvent.room_id == room_id)

        if can_view_all:
            return query

        visibility_filters = [CalendarEvent.scope_type == "global"]
        if user_dormitory_id is not None:
            visibility_filters.append(
                and_(
                    CalendarEvent.scope_type == "dormitory",
                    CalendarEvent.dormitory_id == user_dormitory_id,
                )
            )
        if user_block_id is not None:
            visibility_filters.append(
                and_(
                    CalendarEvent.scope_type == "block",
                    CalendarEvent.block_id == user_block_id,
                )
            )
        if user_room_id is not None:
            visibility_filters.append(
                and_(
                    CalendarEvent.scope_type == "room",
                    CalendarEvent.room_id == user_room_id,
                )
            )

        return query.filter(
            CalendarEvent.status != "draft",
            or_(*visibility_filters),
        )
