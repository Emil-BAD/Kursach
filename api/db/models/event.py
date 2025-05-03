from sqlalchemy import Column, Integer, String, ForeignKey, Text, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    event_date = Column(TIMESTAMP, nullable=False)
    location = Column(String(200), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_urls = Column(JSONB, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    status = Column(String(20), nullable=False, server_default="open")
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    is_private = Column(Boolean, nullable=False, server_default="FALSE")

    # Связи
    organizer = relationship("User", back_populates="events")
    category = relationship("Category", back_populates="events")
    dormitory = relationship("Dormitory", back_populates="events")
    registrations = relationship("EventRegistration", back_populates="event")