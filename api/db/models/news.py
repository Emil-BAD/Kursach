from sqlalchemy import Column, Integer, String, ForeignKey, Text, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
from .base import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_urls = Column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    is_private = Column(Boolean, nullable=False, server_default="FALSE")
    calendar_start_at = Column(TIMESTAMP, nullable=True)
    calendar_end_at = Column(TIMESTAMP, nullable=True)

    # Связи
    author = relationship("User", back_populates="news")
    category = relationship("Category", back_populates="news")
    dormitory = relationship("Dormitory", back_populates="news")
    related_calendar_events = relationship("CalendarEvent", back_populates="related_news")
