# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, Text, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class RentalBooking(Base):
    __tablename__ = "rental_bookings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("rental_listings.id"), nullable=False)
    renter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, server_default="pending")
    deposit_amount = Column(Numeric(10, 2), nullable=False, default=0)
    fine_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_price = Column(Numeric(10, 2), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    listing = relationship("RentalListing", back_populates="bookings")
    renter = relationship("User", foreign_keys=[renter_id], back_populates="rental_bookings")
    approved_by = relationship("User", foreign_keys=[approved_by_id], back_populates="approved_rental_bookings")
