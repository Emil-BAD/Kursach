# -*- coding: utf-8 -*-
"""
Repository для News (новости) - пример миграции со старой архитектуры.

Вместо чтобы писать db.query(News).filter(...).join(...) в каждом месте,
инкапсулируем это в методы репозитория.
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from api.db.models import News, Dormitory
from api.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    """Специализированные методы для работы с новостями"""
    
    def __init__(self, db: Session):
        super().__init__(db, News)
    
    def get_with_author(self, news_id: int) -> Optional[News]:
        """Получить новость с загруженным автором (избегаем N+1)"""
        return (
            self.db.query(News)
            .options(joinedload(News.author), joinedload(News.category), joinedload(News.dormitory))
            .filter(News.id == news_id)
            .first()
        )
    
    def get_all_paginated(self, skip: int, limit: int) -> List[News]:
        """Получить список новостей отсортированных по дате с загруженными авторами"""
        return (
            self.db.query(News)
            .options(joinedload(News.author), joinedload(News.category), joinedload(News.dormitory))
            .order_by(desc(News.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_dormitory(self, dormitory_id: int, skip: int = 0, limit: int = 100) -> List[News]:
        """Получить новости конкретного общежития"""
        return (
            self.db.query(News)
            .options(joinedload(News.author), joinedload(News.category), joinedload(News.dormitory))
            .filter(News.dormitory_id == dormitory_id)
            .order_by(desc(News.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_dormitory(self, dormitory_id: int) -> int:
        """Подсчитать количество новостей в общежитии"""
        return self.db.query(News).filter(News.dormitory_id == dormitory_id).count()
    
    def get_latest(self, limit: int = 5) -> List[News]:
        """Получить последние N новостей"""
        return (
            self.db.query(News)
            .options(joinedload(News.author), joinedload(News.category), joinedload(News.dormitory))
            .order_by(desc(News.created_at))
            .limit(limit)
            .all()
        )
