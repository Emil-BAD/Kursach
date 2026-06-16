# -*- coding: utf-8 -*-
"""
API v1 - News роутер (тонкий слой)
Управление новостями: получение списка, создание, обновление, удаление.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db.models import User
from api.core.dependencies import get_current_user
from api.services.news_service import NewsService
from api.schemas.common import paginate_response
from api.core.exceptions import APIException


router = APIRouter(prefix="/api/v1", tags=["news"])
logger = logging.getLogger(__name__)


class NewsCreate:
    """Схема для создания новости"""
    title: str
    content: str
    dormitory_id: int = None
    image_urls: list = None


class NewsUpdate:
    """Схема для обновления новости"""
    title: str = None
    content: str = None
    image_urls: list = None


def _serialize_news(news) -> dict:
    """
    Преобразует ORM-объект новости в обычный JSON-совместимый словарь.

    Это важно для v1-роутера: FastAPI не всегда корректно сериализует список
    SQLAlchemy ORM-объектов, если мы кладём их в обычный `dict` без явной
    схемы ответа.
    """
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "created_at": news.created_at.isoformat() if news.created_at else None,
        "author_id": news.author_id,
        "author_name": news.author.full_name if getattr(news, "author", None) else None,
        "image_urls": news.image_urls or [],
        "category_id": news.category_id,
        "category_name": news.category.name if getattr(news, "category", None) else None,
        "dormitory_id": news.dormitory_id,
        "dormitory_name": news.dormitory.name if getattr(news, "dormitory", None) else None,
        "is_private": news.is_private,
        "calendar_start_at": news.calendar_start_at.isoformat() if news.calendar_start_at else None,
        "calendar_end_at": news.calendar_end_at.isoformat() if news.calendar_end_at else None,
    }


@router.get("/news", response_model=dict)
def list_all_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Получить список всех новостей.
    
    **Параметры:**
    - page: номер страницы
    - page_size: размер страницы
    
    **Возвращает:**
    ```json
    {
      "items": [
        {
          "id": 1,
          "title": "Новое событие",
          "content": "...",
          "author_id": 1,
          "created_at": "2024-01-15T10:30:00",
          ...
        }
      ],
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3,
      "has_next": true,
      "has_prev": false
    }
    ```
    """
    try:
        service = NewsService(db)
        news, total = service.get_all_news(page, page_size)
        result = paginate_response([_serialize_news(item) for item in news], page, page_size, total)
        return result
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while listing news page=%s page_size=%s", page, page_size)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/news/{news_id}", response_model=dict)
def get_news_detail(
    news_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить одну новость по ID.
    
    **Параметры:**
    - news_id: ID новости
    
    **Возвращает:**
    Объект новости с полной информацией (автор, общежитие и т.д.)
    """
    try:
        service = NewsService(db)
        news = service.get_news_by_id(news_id)
        return _serialize_news(news)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting news detail news_id=%s", news_id)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.post("/news")
def create_news(
    title: str,
    content: str,
    category_id: int,
    dormitory_id: int = None,
    is_private: bool = False,
    image_urls: list = None,
    calendar_start_at: datetime | None = None,
    calendar_end_at: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создать новую новость (админ и комендант).
    
    **Принимает (form-data или query):**
    - title: заголовок
    - content: содержание
    - category_id: ID категории новости
    - dormitory_id: ID общежития (опционально)
    - is_private: приватная ли новость
    - image_urls: массив ссылок на изображения (опционально)
    
    **Возвращает:**
    Созданная новость.
    """
    try:
        service = NewsService(db)
        news = service.create_news(
            title=title,
            content=content,
            author_id=current_user.id,
            category_id=category_id,
            dormitory_id=dormitory_id,
            is_private=is_private,
            image_urls=image_urls,
            calendar_start_at=calendar_start_at,
            calendar_end_at=calendar_end_at,
        )
        return _serialize_news(news)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating news author_id=%s", current_user.id)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.put("/news/{news_id}")
def update_news(
    news_id: int,
    title: str = None,
    content: str = None,
    category_id: int = None,
    dormitory_id: int = None,
    is_private: bool = None,
    image_urls: list = None,
    calendar_start_at: datetime | None = None,
    calendar_end_at: datetime | None = None,
    clear_calendar_dates: bool = False,
    clear_calendar_end_at: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Обновить новость (может только автор или админ).
    
    **Принимает:**
    - title: новый заголовок (опционально)
    - content: новое содержание (опционально)
    - category_id: новая категория (опционально)
    - dormitory_id: новое общежитие (опционально)
    - is_private: новый флаг приватности (опционально)
    - image_urls: новые изображения (опционально)
    
    **Возвращает:**
    Обновленная новость.
    """
    try:
        update_data = {
            k: v for k, v in {
                "title": title,
                "content": content,
                "category_id": category_id,
                "dormitory_id": dormitory_id,
                "is_private": is_private,
                "image_urls": image_urls,
                "calendar_start_at": calendar_start_at,
                "calendar_end_at": calendar_end_at,
                "clear_calendar_dates": clear_calendar_dates,
                "clear_calendar_end_at": clear_calendar_end_at,
            }.items() if v is not None
        }
        
        service = NewsService(db)
        news = service.update_news(news_id, current_user.id, current_user.role.role_name, **update_data)
        return _serialize_news(news)
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while updating news news_id=%s", news_id)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.delete("/news/{news_id}")
def delete_news(
    news_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Удалить новость (может только автор или админ).
    
    **Параметры:**
    - news_id: ID новости для удаления
    
    **Возвращает:**
    ```json
    {
      "success": true,
      "message": "Новость успешно удалена"
    }
    ```
    """
    try:
        service = NewsService(db)
        service.delete_news(news_id, current_user.id, current_user.role.role_name)
        return {"success": True, "message": "Новость успешно удалена"}
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while deleting news news_id=%s", news_id)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/dormitories/{dorm_id}/news", response_model=dict)
def list_news_by_dormitory(
    dorm_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Получить новости конкретного общежития.
    
    **Параметры:**
    - dorm_id: ID общежития
    - page: номер страницы
    - page_size: размер страницы
    
    **Возвращает:**
    Paginated список новостей общежития.
    """
    try:
        service = NewsService(db)
        news, total = service.get_news_by_dormitory(dorm_id, page, page_size)
        result = paginate_response([_serialize_news(item) for item in news], page, page_size, total)
        return result
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while listing dormitory news dorm_id=%s", dorm_id)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


@router.get("/news/latest", response_model=dict)
def get_latest_news(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Получить последние N новостей.
    
    **Параметры:**
    - limit: количество новостей (по умолчанию 5, макс 20)
    
    **Возвращает:**
    ```json
    {
      "items": [...],
      "total": 5
    }
    ```
    """
    try:
        service = NewsService(db)
        news = service.get_latest_news(limit)
        return {"items": [_serialize_news(item) for item in news], "total": len(news)}
    except APIException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting latest news limit=%s", limit)
        from api.core.exceptions import InternalServerError
        raise InternalServerError()
