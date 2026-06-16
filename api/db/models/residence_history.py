# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class ResidenceHistory(Base):
    __tablename__ = "residence_history"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=True)
    eviction_reason = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    user = relationship("User", back_populates="residence_history")
    dormitory = relationship("Dormitory", back_populates="residence_history")
    room = relationship("Room", back_populates="residence_history")
