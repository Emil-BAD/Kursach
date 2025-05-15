# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Date, DateTime, func
from sqlalchemy.orm import relationship
from api.db.models.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    student_card = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(100), nullable=False)
    contact_number = Column(Integer, nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    group_number = Column(Integer)
    specialization = Column(String(100))
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    social_links = Column(JSON)
    birth_date = Column(Date)
    course = Column(Integer)
    faculty = Column(String(100))
    device_token = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    points = Column(JSON, nullable=False, server_default='{"total": 100}')

    # Связь с таблицами, где пользователь НЕ является "родителем" (без каскада)
    role = relationship("Role", back_populates="users")
    dormitory = relationship("Dormitory", back_populates="users")
    room = relationship("Room", back_populates="users")

    # Связь с таблицами, где пользователь является "родителем" (с каскадом)
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    news = relationship("News", back_populates="author", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    event_registrations = relationship("EventRegistration", back_populates="user", cascade="all, delete-orphan")
    products_sold = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
    moderation_logs = relationship("ProductModerationLog", back_populates="moderator", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    action_logs = relationship("ActionLog", back_populates="user", cascade="all, delete-orphan")
    cleanliness_history = relationship("CleanlinessHistory", back_populates="assigned_by_user", cascade="all, delete-orphan")
    user_violations = relationship("UserViolation", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("FavoriteProduct", back_populates="user", cascade="all, delete-orphan")