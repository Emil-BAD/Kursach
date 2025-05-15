from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base

class ActivityType(Base):
    __tablename__ = "activity_types"

    id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Связи
    user_activities = relationship("UserActivity", back_populates="activity_type")