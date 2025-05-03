from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base

class ViolationType(Base):
    __tablename__ = "violation_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Предполагаем, что violation_name - это опечатка, и должно быть name
    description = Column(Text, nullable=True)  # Добавляем описание
    default_penalty_points = Column(Integer, nullable=True)  # Добавляем штрафные баллы по умолчанию

    # Связи
    user_violations = relationship("UserViolation", back_populates="violation_type")