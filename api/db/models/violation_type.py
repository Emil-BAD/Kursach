from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base

class ViolationType(Base):
    __tablename__ = "violation_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    points_deducted = Column(Integer, nullable=False)

    # Связи
    user_violations = relationship("UserViolation", back_populates="violation_type")