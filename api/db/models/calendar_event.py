# -*- coding: utf-8 -*-
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from api.db.models.base import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        CheckConstraint(
            "event_kind IN ('repair', 'water_outage', 'kitchen_duty', 'community_work', 'inspection', 'other')",
            name="chk_calendar_events_kind",
        ),
        CheckConstraint(
            "scope_type IN ('global', 'dormitory', 'block', 'room')",
            name="chk_calendar_events_scope",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'completed', 'draft')",
            name="chk_calendar_events_status",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'duty_generated', 'news_generated', 'event_generated')",
            name="chk_calendar_events_source",
        ),
        CheckConstraint("end_at >= start_at", name="chk_calendar_events_dates"),
        CheckConstraint(
            "(scope_type <> 'dormitory' OR dormitory_id IS NOT NULL)",
            name="chk_calendar_events_scope_dormitory",
        ),
        CheckConstraint(
            "(scope_type <> 'block' OR block_id IS NOT NULL)",
            name="chk_calendar_events_scope_block",
        ),
        CheckConstraint(
            "(scope_type <> 'room' OR room_id IS NOT NULL)",
            name="chk_calendar_events_scope_room",
        ),
        Index("idx_calendar_events_start_at", "start_at"),
        Index("idx_calendar_events_event_kind", "event_kind"),
        Index("idx_calendar_events_status", "status"),
        Index("idx_calendar_events_dormitory_id", "dormitory_id"),
        Index("idx_calendar_events_block_id", "block_id"),
        Index("idx_calendar_events_room_id", "room_id"),
        Index("idx_calendar_events_related_news_id", "related_news_id"),
        Index("idx_calendar_events_related_event_id", "related_event_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_kind = Column(String(30), nullable=False)
    scope_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default="scheduled")
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, nullable=False, server_default=text("FALSE"))
    location = Column(String(255), nullable=True)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id", ondelete="SET NULL"), nullable=True)
    block_id = Column(Integer, ForeignKey("dormitory_blocks.id", ondelete="SET NULL"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    related_news_id = Column(Integer, ForeignKey("news.id", ondelete="SET NULL"), nullable=True)
    related_event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(String(30), nullable=False, server_default="manual")
    metadata_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    dormitory = relationship("Dormitory", back_populates="calendar_events")
    block = relationship("DormitoryBlock", back_populates="calendar_events")
    room = relationship("Room", back_populates="calendar_events")
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_calendar_events",
    )
    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        back_populates="updated_calendar_events",
    )
    related_news = relationship("News", back_populates="related_calendar_events")
    related_event = relationship("Event", back_populates="related_calendar_events")
    kitchen_duty_assignment = relationship(
        "KitchenDutyAssignment",
        back_populates="calendar_event",
        uselist=False,
    )
