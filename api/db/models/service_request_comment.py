# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class ServiceRequestComment(Base):
    __tablename__ = "service_request_comments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    service_request = relationship("ServiceRequest", back_populates="comments")
    author = relationship("User", back_populates="service_request_comments")
