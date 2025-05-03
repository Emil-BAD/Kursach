from sqlalchemy import Column, Integer, ForeignKey, String, Text, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, server_default="FALSE")
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)

    # Связи
    user = relationship("User", back_populates="notifications")