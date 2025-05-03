from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type_id = Column(Integer, ForeignKey("activity_types.id"), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Связи
    user = relationship("User", back_populates="activities")
    activity_type = relationship("ActivityType", back_populates="user_activities")