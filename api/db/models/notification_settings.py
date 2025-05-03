from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    news_notifications = Column(Boolean, nullable=False, server_default="TRUE")
    event_notifications = Column(Boolean, nullable=False, server_default="TRUE")
    product_notifications = Column(Boolean, nullable=False, server_default="TRUE")
    cleanliness_notifications = Column(Boolean, nullable=False, server_default="TRUE")
    violation_notifications = Column(Boolean, nullable=False, server_default="TRUE")

    # Связи
    user = relationship("User", uselist=False)