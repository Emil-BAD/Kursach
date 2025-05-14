from sqlalchemy import Column, Integer, String, ARRAY
from sqlalchemy.orm import relationship
from .base import Base

class Dormitory(Base):
    __tablename__ = "dormitories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)
    image_urls = Column(ARRAY(String, dimensions=1), nullable=True)  # Массив строк для ссылок

    # Связи
    rooms = relationship("Room", back_populates="dormitory")
    users = relationship("User", back_populates="dormitory")
    news = relationship("News", back_populates="dormitory")
    events = relationship("Event", back_populates="dormitory")
    products = relationship("Product", back_populates="dormitory")