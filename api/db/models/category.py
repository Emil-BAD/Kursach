# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from api.db.models.base import Base

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    entity_type = Column(String(20), nullable=False)

    news = relationship("News", back_populates="category")
    events = relationship("Event", back_populates="category")
    products = relationship("Product", back_populates="category")
    rental_listings = relationship("RentalListing", back_populates="category")
