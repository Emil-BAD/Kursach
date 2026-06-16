# -*- coding: utf-8 -*-
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class PaymentTopUp(Base):
    __tablename__ = "payment_top_ups"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(30), nullable=False, server_default="confirmed")
    transfer_reference = Column(String(64), nullable=False, unique=True)
    account_number_snapshot = Column(String(100), nullable=False)
    recipient_name_snapshot = Column(String(200), nullable=False)
    bank_name_snapshot = Column(String(200), nullable=True)
    receipt_file_name = Column(String(255), nullable=True)
    receipt_file_url = Column(String(500), nullable=True)
    comment = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    credited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    user = relationship("User", foreign_keys=[user_id], back_populates="payment_top_ups")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], back_populates="reviewed_payment_top_ups")
