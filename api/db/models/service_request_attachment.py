# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class ServiceRequestAttachment(Base):
    __tablename__ = "service_request_attachments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    service_request = relationship("ServiceRequest", back_populates="attachments")
    uploaded_by = relationship("User", back_populates="service_request_attachments")
