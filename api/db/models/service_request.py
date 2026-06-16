# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    request_type = Column(String(30), nullable=False, server_default="request")
    status = Column(String(30), nullable=False, server_default="new")
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    resolution_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    closed_at = Column(DateTime, nullable=True)

    student = relationship("User", foreign_keys=[student_id], back_populates="created_service_requests")
    executor = relationship("User", foreign_keys=[executor_id], back_populates="assigned_service_requests")
    dormitory = relationship("Dormitory", back_populates="service_requests")
    room = relationship("Room", back_populates="service_requests")
    comments = relationship("ServiceRequestComment", back_populates="service_request", cascade="all, delete-orphan")
    attachments = relationship("ServiceRequestAttachment", back_populates="service_request", cascade="all, delete-orphan")
