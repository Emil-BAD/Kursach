# -*- coding: utf-8 -*-
"""
News Service - бизнес-логика для работы с новостями.
Содержит логику получения, создания, обновления новостей.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from api.db.models import News, Dormitory, User, Category
from api.repositories.news import NewsRepository
from api.services.calendar_content_sync_service import CalendarContentSyncService
from api.services.user_helpers import can_manage_news
from api.core.exceptions import (
    NotFoundError,
    DatabaseError,
    DormitoryNotFoundError,
)


class NewsService:
    """Сервис для работы с новостями"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = NewsRepository(db)
    
    def get_news_by_id(self, news_id: int) -> News:
        """Получить новость по ID"""
        news = self.repo.get_with_author(news_id)
        if not news:
            raise NotFoundError("Новость", news_id)
        return news
    
    def get_all_news(self, page: int = 1, page_size: int = 20) -> tuple[List[News], int]:
        """
        Получить все новости с пагинацией.
        
        Returns:
            (news_list, total_count)
        """
        skip = (page - 1) * page_size
        news = self.repo.get_all_paginated(skip, page_size)
        total = self.repo.get_all_count()
        return news, total
    
    def get_news_by_dormitory(self, dormitory_id: int, page: int = 1, page_size: int = 20) -> tuple[List[News], int]:
        """
        Получить новости конкретного общежития.
        
        Returns:
            (news_list, total_count)
        """
        # Проверяем что общежитие существует
        dorm = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dorm:
            raise DormitoryNotFoundError(dormitory_id)
        
        skip = (page - 1) * page_size
        news = self.repo.get_by_dormitory(dormitory_id, skip, page_size)
        total = self.repo.count_by_dormitory(dormitory_id)
        return news, total

    def _validate_dormitory(self, dormitory_id: int | None) -> None:
        """Проверить, что общежитие существует, если ID передан."""
        if not dormitory_id:
            return

        dorm = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dorm:
            raise DormitoryNotFoundError(dormitory_id)

    def _validate_category(self, category_id: int | None) -> None:
        """Проверить, что категория новости существует."""
        if category_id is None:
            from api.core.exceptions import ValidationError
            raise ValidationError("category_id обязателен для новости")

        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            from api.core.exceptions import ValidationError
            raise ValidationError("Категория новости не найдена")
    
    def create_news(
        self,
        title: str,
        content: str,
        author_id: int,
        category_id: int,
        dormitory_id: int = None,
        is_private: bool = False,
        image_urls: list = None,
        calendar_start_at: datetime | None = None,
        calendar_end_at: datetime | None = None,
    ) -> News:
        """Создать новую новость"""
        # Проверяем что автор существует
        author = self.db.query(User).filter(User.id == author_id).first()
        if not author:
            from api.core.exceptions import UserNotFoundError
            raise UserNotFoundError(author_id)
        
        if not can_manage_news(author):
            from api.core.exceptions import InsufficientPermissionsError
            raise InsufficientPermissionsError()
        
        self._validate_category(category_id)
        self._validate_dormitory(dormitory_id)
        self._validate_calendar_dates(calendar_start_at, calendar_end_at)
        
        try:
            news = News(
                title=title,
                content=content,
                author_id=author_id,
                category_id=category_id,
                dormitory_id=dormitory_id,
                is_private=is_private,
                image_urls=image_urls or [],
                calendar_start_at=calendar_start_at,
                calendar_end_at=calendar_end_at,
            )
            self.db.add(news)
            self.db.flush()
            CalendarContentSyncService(self.db).sync_news(news, actor_id=author_id)
            self.db.commit()
            self.db.refresh(news)
            return news
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def update_news(self, news_id: int, user_id: int, user_role: str, **update_data) -> News:
        """Обновить новость. Может автор или администратор."""
        news = self.repo.get_by_id(news_id)
        if not news:
            raise NotFoundError("Новость", news_id)
        
        can_edit = news.author_id == user_id or user_role in {
            "admin",
            "commandant",
            "educator",
            "council_president",
            "council_member",
        }
        if not can_edit:
            from api.core.exceptions import InsufficientPermissionsError
            raise InsufficientPermissionsError()

        if "category_id" in update_data:
            self._validate_category(update_data.get("category_id"))
        if "dormitory_id" in update_data:
            self._validate_dormitory(update_data.get("dormitory_id"))

        clear_calendar_dates = bool(update_data.pop("clear_calendar_dates", False))
        clear_calendar_end_at = bool(update_data.pop("clear_calendar_end_at", False))
        if clear_calendar_dates:
            update_data["calendar_start_at"] = None
            update_data["calendar_end_at"] = None
        elif clear_calendar_end_at:
            update_data["calendar_end_at"] = None

        next_calendar_start_at = update_data.get("calendar_start_at", news.calendar_start_at)
        next_calendar_end_at = update_data.get("calendar_end_at", news.calendar_end_at)
        self._validate_calendar_dates(next_calendar_start_at, next_calendar_end_at)
        
        try:
            for key, value in update_data.items():
                if hasattr(news, key):
                    setattr(news, key, value)
            CalendarContentSyncService(self.db).sync_news(news, actor_id=user_id)
            self.db.commit()
            self.db.refresh(news)
            return news
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def delete_news(self, news_id: int, user_id: int, user_role: str) -> bool:
        """
        Удалить новость.
        Может удалить: автор новости или админ.
        """
        news = self.repo.get_by_id(news_id)
        if not news:
            raise NotFoundError("Новость", news_id)
        
        # Проверяем права: автор или админ
        can_delete = (
            news.author_id == user_id or
            user_role in {
                "admin",
                "commandant",
                "educator",
                "council_president",
                "council_member",
            }
        )
        if not can_delete:
            from api.core.exceptions import InsufficientPermissionsError
            raise InsufficientPermissionsError()
        
        try:
            CalendarContentSyncService(self.db).remove_news_event(news.id)
            self.db.delete(news)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
    
    def get_latest_news(self, limit: int = 5) -> List[News]:
        """Получить последние N новостей"""
        return self.repo.get_latest(limit)

    def _validate_calendar_dates(
        self,
        calendar_start_at: datetime | None,
        calendar_end_at: datetime | None,
    ) -> None:
        if calendar_start_at is None and calendar_end_at is not None:
            from api.core.exceptions import ValidationError
            raise ValidationError("Дата окончания новости не может быть задана без даты начала")
        if calendar_start_at is not None and calendar_end_at is not None and calendar_end_at < calendar_start_at:
            from api.core.exceptions import ValidationError
            raise ValidationError("Дата окончания новости не может быть раньше даты начала")
