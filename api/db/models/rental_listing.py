# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class RentalListing(Base):
    __tablename__ = "rental_listings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    daily_price = Column(Numeric(10, 2), nullable=False)
    deposit_amount = Column(Numeric(10, 2), nullable=False, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    image_urls = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, server_default="approved")
    listing_status = Column(String(30), nullable=False, server_default="active")
    availability_status = Column(String(30), nullable=False, server_default="free")
    pickup_location = Column(String(255), nullable=True)
    minimum_rental_period_text = Column(String(120), nullable=True)
    contact_name = Column(String(120), nullable=True)
    contact_value = Column(String(255), nullable=True)
    contact_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    owner = relationship("User", back_populates="rental_listings")
    category = relationship("Category", back_populates="rental_listings")
    dormitory = relationship("Dormitory", back_populates="rental_listings")
    bookings = relationship("RentalBooking", back_populates="listing", cascade="all, delete-orphan")
