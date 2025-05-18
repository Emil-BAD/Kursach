# api/db/models/product.py
# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
from api.db.models.base import Base

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    image_urls = Column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"))
    status = Column(String(20), nullable=False, server_default="pending")
    rejection_reason = Column(Text)
    seller_telegram = Column(String(255), nullable=True)  # Новое поле для Telegram
    seller_vk = Column(String(255), nullable=True)       # Новое поле для VK

    seller = relationship("User", back_populates="products_sold")
    category = relationship("Category", back_populates="products")
    dormitory = relationship("Dormitory", back_populates="products")
    moderation_logs = relationship("ProductModerationLog", back_populates="product")
    favorited_by = relationship("FavoriteProduct", back_populates="product")