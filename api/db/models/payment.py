# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, Text, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(30), nullable=False, server_default="pending")
    payment_channel = Column(String(30), nullable=True)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    admin_comment = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    user = relationship("User", foreign_keys=[user_id], back_populates="payments")
    dormitory = relationship("Dormitory", back_populates="payments")
    room = relationship("Room", back_populates="payments")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_payments")
