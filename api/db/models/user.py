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
    contract_number = Column(Integer, nullable=False)
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

    role = relationship("Role", back_populates="users")
    dormitory = relationship("Dormitory", back_populates="users")
    room = relationship("Room", back_populates="users")
    activities = relationship("UserActivity", back_populates="user")
    news = relationship("News", back_populates="author")
    events = relationship("Event", back_populates="organizer")
    event_registrations = relationship("EventRegistration", back_populates="user")
    products_sold = relationship("Product", back_populates="seller")
    moderation_logs = relationship("ProductModerationLog", back_populates="moderator")
    notification_settings = relationship("NotificationSettings", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    action_logs = relationship("ActionLog", back_populates="user")
    cleanliness_history = relationship("CleanlinessHistory", back_populates="assigned_by_user")
    user_violations = relationship("UserViolation", back_populates="user")