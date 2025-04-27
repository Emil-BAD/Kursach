from sqlalchemy import Column, Integer, String, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_card = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(100), nullable=False)
    contract_number = Column(Integer, nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    group_number = Column(Integer, nullable=True)
    specialization = Column(String(100), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    social_links = Column(JSON, nullable=True)
    birth_date = Column(Date, nullable=True)
    course = Column(Integer, nullable=True)
    faculty = Column(String(100), nullable=True)
    device_token = Column(String(500), nullable=True)

    # Связи
    dormitory = relationship("Dormitory", back_populates="users")
    room = relationship("Room", back_populates="users")
    role = relationship("Role", back_populates="users")
    violations = relationship("UserViolation", back_populates="user")
    activities = relationship("UserActivity", back_populates="user")
    news = relationship("News", back_populates="author")
    events = relationship("Event", back_populates="organizer")
    products = relationship("Product", back_populates="seller")
    notifications = relationship("Notification", back_populates="user")