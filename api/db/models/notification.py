from sqlalchemy import Column, Integer, ForeignKey, JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import relationship
from api.db.models.base import Base

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(JSON, nullable=False)  # Хранит title, message и другие данные
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    entity_type = Column(String, nullable=True)  # Если есть в таблице
    entity_id = Column(Integer, nullable=True)  # Если есть в таблице

    user = relationship("User", back_populates="notifications")