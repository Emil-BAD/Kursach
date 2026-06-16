# -*- coding: utf-8 -*-
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class DormitoryBlockRoom(Base):
    __tablename__ = "dormitory_block_rooms"
    __table_args__ = (
        UniqueConstraint("block_id", "room_id", name="uq_dormitory_block_rooms_block_room"),
        CheckConstraint("rotation_order > 0", name="chk_dormitory_block_rooms_rotation_order"),
        Index("idx_dormitory_block_rooms_room_id", "room_id"),
        Index("idx_dormitory_block_rooms_rotation_order", "rotation_order"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("dormitory_blocks.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    rotation_order = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    block = relationship("DormitoryBlock", back_populates="block_rooms")
    room = relationship("Room", back_populates="block_links")
