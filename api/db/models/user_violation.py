from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class UserViolation(Base):
    __tablename__ = "user_violations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    violation_type_id = Column(Integer, ForeignKey("violation_types.id"), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Связи
    user = relationship("User", back_populates="violations")
    violation_type = relationship("ViolationType", back_populates="user_violations")