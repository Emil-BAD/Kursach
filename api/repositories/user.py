# -*- coding: utf-8 -*-
"""Репозиторий для User"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from api.db.models import User
from api.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Специализированные методы для работы с пользователями"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_student_card(self, student_card: str) -> Optional[User]:
        """Получить пользователя по номеру студенческого билета"""
        return self.db.query(User).filter(User.student_card == student_card).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_with_role(self, user_id: int) -> Optional[User]:
        """Получить пользователя с загруженными связями профиля"""
        return (
            self.db.query(User)
            .options(
                joinedload(User.role),
                joinedload(User.dormitory),
                joinedload(User.room),
            )
            .filter(User.id == user_id)
            .first()
        )
    
    def get_by_dormitory(self, dormitory_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """Получить всех пользователей в общежитии"""
        return (
            self.db.query(User)
            .filter(User.dormitory_id == dormitory_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_room(self, room_id: int) -> List[User]:
        """Получить всех пользователей в комнате"""
        return self.db.query(User).filter(User.room_id == room_id).all()
    
    def count_by_dormitory(self, dormitory_id: int) -> int:
        """Подсчитать количество пользователей в общежитии"""
        return self.db.query(User).filter(User.dormitory_id == dormitory_id).count()
    
    def count_by_role(self, role_name: str) -> int:
        """Подсчитать количество пользователей с определённой ролью"""
        from api.db.models import Role
        return (
            self.db.query(User)
            .join(Role)
            .filter(Role.role_name == role_name)
            .count()
        )
