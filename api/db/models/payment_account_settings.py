# -*- coding: utf-8 -*-
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class PaymentAccountSettings(Base):
    __tablename__ = "payment_account_settings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(100), nullable=False)
    recipient_name = Column(String(200), nullable=False)
    bank_name = Column(String(200), nullable=True)
    payment_instructions = Column(Text, nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    updated_by = relationship("User", foreign_keys=[updated_by_id], back_populates="updated_payment_account_settings")
