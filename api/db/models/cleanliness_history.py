# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from api.db.models.base import Base

class CleanlinessHistory(Base):
    __tablename__ = "cleanliness_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    score = Column(Integer, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    room = relationship("Room", back_populates="cleanliness_history")
    assigned_by_user = relationship("User", back_populates="cleanliness_history")