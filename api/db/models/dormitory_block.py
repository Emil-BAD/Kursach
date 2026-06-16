# -*- coding: utf-8 -*-
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from api.db.models.base import Base


class DormitoryBlock(Base):
    __tablename__ = "dormitory_blocks"
    __table_args__ = (
        UniqueConstraint("dormitory_id", "name", name="uq_dormitory_blocks_dormitory_name"),
        Index("idx_dormitory_blocks_dormitory_id", "dormitory_id"),
        Index("idx_dormitory_blocks_is_active", "is_active"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    kitchen_label = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    dormitory = relationship("Dormitory", back_populates="blocks")
    block_rooms = relationship(
        "DormitoryBlockRoom",
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="DormitoryBlockRoom.rotation_order",
    )
    calendar_events = relationship("CalendarEvent", back_populates="block")
    kitchen_duty_plans = relationship("KitchenDutyPlan", back_populates="block")
