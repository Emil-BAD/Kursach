from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, server_default="pending")
    registered_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Связи
    event = relationship("Event", back_populates="registrations")
    user = relationship("User")