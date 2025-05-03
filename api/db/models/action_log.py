from sqlalchemy import Column, Integer, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Связи
    user = relationship("User")