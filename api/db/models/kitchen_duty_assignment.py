# -*- coding: utf-8 -*-
from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class KitchenDutyAssignment(Base):
    __tablename__ = "kitchen_duty_assignments"
    __table_args__ = (
        UniqueConstraint("plan_id", "duty_date", name="uq_kitchen_duty_assignments_plan_date"),
        UniqueConstraint("calendar_event_id", name="uq_kitchen_duty_assignments_event"),
        CheckConstraint("duty_order > 0", name="chk_kitchen_duty_assignments_order"),
        Index("idx_kitchen_duty_assignments_room_id", "room_id"),
        Index("idx_kitchen_duty_assignments_duty_date", "duty_date"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("kitchen_duty_plans.id", ondelete="CASCADE"), nullable=False)
    calendar_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    duty_date = Column(Date, nullable=False)
    duty_order = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    plan = relationship("KitchenDutyPlan", back_populates="assignments")
    calendar_event = relationship("CalendarEvent", back_populates="kitchen_duty_assignment")
    room = relationship("Room", back_populates="kitchen_duty_assignments")
