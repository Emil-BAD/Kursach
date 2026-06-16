# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from api.db.models.base import Base

class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=False)
    cleanliness_points = Column(Integer, nullable=False, server_default="0")

    dormitory = relationship("Dormitory", back_populates="rooms")
    users = relationship("User", back_populates="room")
    cleanliness_history = relationship("CleanlinessHistory", back_populates="room")
    service_requests = relationship("ServiceRequest", back_populates="room")
    residence_history = relationship("ResidenceHistory", back_populates="room")
    payments = relationship("Payment", back_populates="room")
    block_links = relationship("DormitoryBlockRoom", back_populates="room", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="room")
    kitchen_duty_assignments = relationship("KitchenDutyAssignment", back_populates="room")
