from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from api.core.exceptions import ValidationError
from api.db.models import CalendarEvent, Event, News


class CalendarContentSyncService:
    """Keeps content modules visible in the canonical calendar source."""

    def __init__(self, db: Session):
        self.db = db

    def sync_news(self, news: News, *, actor_id: int | None = None) -> CalendarEvent | None:
        existing_events = self._news_calendar_events(news.id)
        existing = existing_events[0] if existing_events else None
        self._delete_duplicates(existing_events[1:])

        start_at = news.calendar_start_at
        end_at = news.calendar_end_at or start_at

        if start_at is None or news.is_private:
            self._delete_existing(existing)
            return None

        self._validate_dates(start_at, end_at)

        payload = {
            "title": news.title.strip(),
            "description": news.content.strip() or None,
            "event_kind": "other",
            "scope_type": "dormitory" if news.dormitory_id is not None else "global",
            "status": "scheduled",
            "start_at": start_at,
            "end_at": end_at,
            "is_all_day": True,
            "location": None,
            "dormitory_id": news.dormitory_id,
            "block_id": None,
            "room_id": None,
            "updated_by_id": actor_id,
            "related_news_id": news.id,
            "related_event_id": None,
            "source_type": "news_generated",
            "metadata_json": {
                "generated_from": "news",
                "news_id": news.id,
                "category_id": news.category_id,
                "is_private": bool(news.is_private),
            },
        }

        if existing is None:
            existing = CalendarEvent(created_by_id=actor_id, **payload)
            self.db.add(existing)
            return existing

        for key, value in payload.items():
            setattr(existing, key, value)
        if existing.created_by_id is None:
            existing.created_by_id = actor_id
        return existing

    def remove_news_event(self, news_id: int) -> None:
        for event in self._news_calendar_events(news_id):
            self.db.delete(event)

    def sync_event(self, event: Event, *, actor_id: int | None = None) -> CalendarEvent | None:
        existing_events = self._domain_event_calendar_events(event.id)
        existing = existing_events[0] if existing_events else None
        self._delete_duplicates(existing_events[1:])

        calendar_status = self._map_event_status(event.status)
        if event.is_private or calendar_status == "cancelled":
            self._delete_existing(existing)
            return None

        payload = {
            "title": event.title.strip(),
            "description": event.description.strip() or None,
            "event_kind": "other",
            "scope_type": "dormitory" if event.dormitory_id is not None else "global",
            "status": calendar_status,
            "start_at": event.event_date,
            "end_at": event.event_date,
            "is_all_day": False,
            "location": event.location.strip() if event.location else None,
            "dormitory_id": event.dormitory_id,
            "block_id": None,
            "room_id": None,
            "updated_by_id": actor_id,
            "related_news_id": None,
            "related_event_id": event.id,
            "source_type": "event_generated",
            "metadata_json": {
                "generated_from": "event",
                "event_id": event.id,
                "category_id": event.category_id,
                "is_private": bool(event.is_private),
                "requirements": event.requirements,
            },
        }

        if existing is None:
            existing = CalendarEvent(created_by_id=actor_id, **payload)
            self.db.add(existing)
            return existing

        for key, value in payload.items():
            setattr(existing, key, value)
        if existing.created_by_id is None:
            existing.created_by_id = actor_id
        return existing

    def remove_event_calendar_projection(self, event_id: int) -> None:
        for event in self._domain_event_calendar_events(event_id):
            self.db.delete(event)

    def _news_calendar_events(self, news_id: int) -> list[CalendarEvent]:
        return (
            self.db.query(CalendarEvent)
            .filter(
                CalendarEvent.related_news_id == news_id,
                CalendarEvent.source_type == "news_generated",
            )
            .order_by(CalendarEvent.id.asc())
            .all()
        )

    def _domain_event_calendar_events(self, event_id: int) -> list[CalendarEvent]:
        return (
            self.db.query(CalendarEvent)
            .filter(
                CalendarEvent.related_event_id == event_id,
                CalendarEvent.source_type == "event_generated",
            )
            .order_by(CalendarEvent.id.asc())
            .all()
        )

    def _delete_duplicates(self, events: Iterable[CalendarEvent]) -> None:
        for event in events:
            self.db.delete(event)

    def _delete_existing(self, event: CalendarEvent | None) -> None:
        if event is not None:
            self.db.delete(event)

    def _validate_dates(self, start_at: datetime, end_at: datetime | None) -> None:
        if end_at is not None and end_at < start_at:
            raise ValidationError("Дата окончания не может быть раньше даты начала")

    def _map_event_status(self, status: str | None) -> str:
        normalized = (status or "open").strip().lower()
        if normalized in {"open", "scheduled"}:
            return "scheduled"
        if normalized == "cancelled":
            return "cancelled"
        if normalized in {"closed", "completed"}:
            return "completed"
        return "scheduled"
