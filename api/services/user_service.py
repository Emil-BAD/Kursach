# -*- coding: utf-8 -*-
"""
User Service - бизнес-логика для работы с пользователями.
Получение, обновление, удаление пользователей.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from api.db.models import User, Role, Dormitory, Room
from api.repositories.user import UserRepository
from api.core.exceptions import (
    UserNotFoundError,
    DatabaseError,
    UserAlreadyExistsError,
    RoleNotFoundError,
    DormitoryNotFoundError,
    RoomNotFoundError,
)
from api.core.auth import get_password_hash
from api.services.user_helpers import build_user_response


class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def get_user_by_id(self, user_id: int) -> User:
        """Получить пользователя по ID"""
        user = self.user_repo.get_with_role(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return user
    
    def get_all_users(self, page: int = 1, page_size: int = 20) -> tuple[List[User], int]:
        """
        Получить список всех пользователей с пагинацией.
        
        Returns:
            (users, total_count)
        """
        skip = (page - 1) * page_size
        users = self.user_repo.get_all(skip=skip, limit=page_size)
        total = self.user_repo.get_all_count()
        return users, total
    
    def create_user(
        self,
        student_card: str,
        password: str,
        full_name: str,
        contact_number: int,
        role_id: int,
        dormitory_id: int = None,
        room_id: int = None,
        group_number: int = None,
        email: str = None,
        birth_date = None,
        course: int = None,
        faculty: str = None,
        specialization: str = None,
    ) -> User:
        """Создать нового пользователя"""
        # Проверяем уникальность студенческого билета
        if self.user_repo.exists(student_card=student_card):
            raise UserAlreadyExistsError("студенческий билет")
        
        # Проверяем существование роли
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise RoleNotFoundError(role_id)
        
        # Проверяем существование общежития (если указано)
        if dormitory_id:
            dorm = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
            if not dorm:
                raise DormitoryNotFoundError(dormitory_id)
        
        # Проверяем существование комнаты (если указано)
        if room_id:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if not room:
                raise RoomNotFoundError(room_id)
        
        # Хешируем пароль
        password_hash = get_password_hash(password)
        
        # Создаём пользователя
        try:
            user = self.user_repo.create(
                student_card=student_card,
                password_hash=password_hash,
                full_name=full_name,
                contact_number=contact_number,
                role_id=role_id,
                dormitory_id=dormitory_id,
                room_id=room_id,
                group_number=group_number,
                email=email,
                birth_date=birth_date,
                course=course,
                faculty=faculty,
                specialization=specialization,
                points={"total": 100},
            )
            return user
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def update_user(self, user_id: int, **update_data) -> User:
        """Обновить данные пользователя"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        
        # Если меняется роль - проверяем существование
        if "role_id" in update_data:
            role = self.db.query(Role).filter(Role.id == update_data["role_id"]).first()
            if not role:
                raise RoleNotFoundError(update_data["role_id"])
        
        # Если меняется общежитие - проверяем существование
        if "dormitory_id" in update_data and update_data["dormitory_id"]:
            dorm = self.db.query(Dormitory).filter(Dormitory.id == update_data["dormitory_id"]).first()
            if not dorm:
                raise DormitoryNotFoundError(update_data["dormitory_id"])
        
        # Если меняется комната - проверяем существование
        if "room_id" in update_data and update_data["room_id"]:
            room = self.db.query(Room).filter(Room.id == update_data["room_id"]).first()
            if not room:
                raise RoomNotFoundError(update_data["room_id"])
        
        try:
            user = self.user_repo.update(user, **update_data)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        
        try:
            self.user_repo.delete(user)
            return True
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def get_users_by_dormitory(self, dormitory_id: int, page: int = 1, page_size: int = 20) -> tuple[List[User], int]:
        """Получить пользователей в общежитии"""
        # Проверяем что общежитие существует
        dorm = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dorm:
            raise DormitoryNotFoundError(dormitory_id)
        
        skip = (page - 1) * page_size
        users = self.user_repo.get_by_dormitory(dormitory_id, skip=skip, limit=page_size)
        total = self.user_repo.count_by_dormitory(dormitory_id)
        return users, total
    
    def get_users_by_room(self, room_id: int) -> List[User]:
        """Получить пользователей в комнате"""
        # Проверяем что комната существует
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise RoomNotFoundError(room_id)
        
        return self.user_repo.get_by_room(room_id)
    
    def change_user_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Изменить пароль пользователя"""
        from api.core.auth import verify_password
        from api.core.exceptions import InvalidCredentialsError
        
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        
        # Проверяем старый пароль
        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError()
        
        # Обновляем пароль
        try:
            new_password_hash = get_password_hash(new_password)
            self.user_repo.update(user, password_hash=new_password_hash)
            return True
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

    def get_user_response(self, user_id: int):
        """Получить готовый API-ответ по пользователю."""
        user = self.get_user_by_id(user_id)
        return build_user_response(self.db, user)
