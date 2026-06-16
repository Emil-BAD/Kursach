# -*- coding: utf-8 -*-
"""
Базовый репозиторий - общие методы для работы с БД.
Вместо того чтобы писать db.query(...).filter(...) везде, 
используем чистый интерфейс.
"""
from typing import TypeVar, Generic, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Базовый репозиторий с общими CRUD операциями"""
    
    def __init__(self, db: Session, model: type):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """Получить одну запись по ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Получить список записей с пагинацией"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def get_all_count(self) -> int:
        """Получить общее количество записей"""
        return self.db.query(self.model).count()
    
    def get_by_filter(self, **filters) -> Optional[T]:
        """Получить одну запись по фильтру"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first()
    
    def get_all_by_filter(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """Получить список записей по фильтру"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.offset(skip).limit(limit).all()
    
    def count_by_filter(self, **filters) -> int:
        """Получить количество записей по фильтру"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.count()
    
    def create(self, **data) -> T:
        """Создать новую запись"""
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, obj: T, **data) -> T:
        """Обновить запись"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, obj: T) -> bool:
        """Удалить запись"""
        self.db.delete(obj)
        self.db.commit()
        return True
    
    def exists(self, **filters) -> bool:
        """Проверить существование записи по фильтру"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None
