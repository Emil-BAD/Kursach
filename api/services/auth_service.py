# -*- coding: utf-8 -*-
"""
Auth Service - бизнес-логика для аутентификации и авторизации.
Простой использование: вызови метод service.login(...) и получишь токены.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from api.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from api.core.config import settings
from api.core.exceptions import (
    DatabaseUnavailableError,
    InvalidCredentialsError,
    DatabaseError,
    TokenExpiredError,
    InvalidTokenError,
)
from api.db.models import User, RefreshToken
from api.repositories.user import UserRepository


class AuthService:
    """Сервис аутентификации"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def login(self, student_card: str, password: str) -> dict:
        """
        Вход по студенческому билету и паролю.
        
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "bearer"
            }
        """
        try:
            user = self.user_repo.get_by_student_card(student_card)
        except OperationalError:
            raise DatabaseUnavailableError()

        if not user:
            raise InvalidCredentialsError()
        
        # Проверяем пароль
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        
        # Генерируем токены
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        if settings.AUTH_STATELESS_REFRESH_TOKENS:
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }
        
        # Сохраняем refresh token в БД для валидации
        try:
            refresh_obj = RefreshToken(
                user_id=user.id,
                token=refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
            self.db.add(refresh_obj)
            self.db.commit()
        except OperationalError:
            self.db.rollback()
            raise DatabaseUnavailableError()
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    def register(
        self,
        student_card: str,
        password: str,
        full_name: str,
        contact_number: int,
        role_id: int,
        dormitory_id: int = None,
        room_id: int = None,
        group_number: int = None,
        specialization: str = None,
        email: str = None,
        phone: str = None,
        birth_date = None,
        course: int = None,
        faculty: str = None,
        social_links: dict | None = None,
    ) -> User:
        """
        Регистрация нового пользователя (обычно студента).
        
        Returns:
            User объект
        """
        from api.db.models import Role
        
        # Проверяем уникальность студенческого билета
        try:
            if self.user_repo.exists(student_card=student_card):
                from api.core.exceptions import UserAlreadyExistsError
                raise UserAlreadyExistsError("студенческий билет")
        except OperationalError:
            raise DatabaseUnavailableError()
        
        # Проверяем что роль существует
        try:
            role = self.db.query(Role).filter(Role.id == role_id).first()
        except OperationalError:
            raise DatabaseUnavailableError()
        if not role:
            from api.core.exceptions import RoleNotFoundError
            raise RoleNotFoundError(role_id)
        
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
                specialization=specialization,
                email=email,
                phone=phone,
                birth_date=birth_date,
                course=course,
                faculty=faculty,
                social_links=social_links,
                points={"total": 100},  # Начальные баллы
            )
            return user
        except OperationalError as e:
            self.db.rollback()
            raise DatabaseUnavailableError()
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError()
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Обновить access token используя refresh token.
        
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "bearer"
            }
        """
        from jose import jwt, JWTError
        
        # Декодируем refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            user_id = payload.get("sub")
            if not user_id:
                raise InvalidTokenError()
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError:
            raise InvalidTokenError()

        if settings.AUTH_STATELESS_REFRESH_TOKENS:
            return {
                "access_token": create_access_token(data={"sub": str(user_id)}),
                "refresh_token": create_refresh_token(data={"sub": str(user_id)}),
                "token_type": "bearer",
            }
        
        # Проверяем что этот refresh token сохранён в БД и не истёк
        try:
            stored_token = (
                self.db.query(RefreshToken)
                .filter(RefreshToken.token == refresh_token)
                .first()
            )
        except OperationalError:
            raise DatabaseUnavailableError()
        
        if not stored_token or stored_token.expires_at < datetime.utcnow():
            raise InvalidTokenError()
        
        # Генерируем новые токены
        try:
            # Удаляем старый refresh token
            self.db.delete(stored_token)
            
            new_access_token = create_access_token(data={"sub": str(user_id)})
            new_refresh_token = create_refresh_token(data={"sub": str(user_id)})
            
            # Сохраняем новый refresh token
            new_token_obj = RefreshToken(
                user_id=int(user_id),
                token=new_refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
            self.db.add(new_token_obj)
            self.db.commit()
        except OperationalError as e:
            self.db.rollback()
            raise DatabaseUnavailableError()
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError()
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }
    
    def logout(self, refresh_token: str) -> bool:
        """Logout - удалить refresh token из БД"""
        if settings.AUTH_STATELESS_REFRESH_TOKENS:
            return True

        try:
            token_obj = (
                self.db.query(RefreshToken)
                .filter(RefreshToken.token == refresh_token)
                .first()
            )
            if token_obj:
                self.db.delete(token_obj)
                self.db.commit()
                return True
            return False
        except OperationalError:
            self.db.rollback()
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
