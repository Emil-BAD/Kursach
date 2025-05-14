from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type_id = Column(Integer, ForeignKey("activity_types.id"), nullable=False)
    activity_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)  # Заметки об активности, а не description

    user = relationship("User", back_populates="activities")
    activity_type = relationship("ActivityType", back_populates="user_activities")