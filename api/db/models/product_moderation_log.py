from sqlalchemy import Column, Integer, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base

class ProductModerationLog(Base):
    __tablename__ = "product_moderation_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Связи
    product = relationship("Product", back_populates="moderation_logs")
    moderator = relationship("User")