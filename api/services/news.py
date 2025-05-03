from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from db.models import News, User, Category, Dormitory
from schemas.news import NewsCreate, NewsUpdate, NewsResponse, PaginatedNewsResponse
from core.dependencies import get_current_user, get_current_admin

router = APIRouter()

@router.get("/news", response_model=PaginatedNewsResponse)
def get_news(
    page: int = 1,
    per_page: int = 10,
    category_id: int = None,
    dormitory_id: int = None,
    is_private: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * per_page
    query = db.query(News)

    # Фильтрация
    if category_id:
        query = query.filter(News.category_id == category_id)
    if dormitory_id:
        query = query.filter(News.dormitory_id == dormitory_id)
    if is_private is not None:
        query = query.filter(News.is_private == is_private)

    # Ограничение доступа: приватные новости видны только администраторам
    if current_user.role_id != 1 and is_private is not True:  # Если не администратор, скрываем приватные новости
        query = query.filter(News.is_private == False)

    total = query.count()
    news_items = query.offset(skip).limit(per_page).all()

    news_responses = []
    for news in news_items:
        category = db.query(Category).filter(Category.id == news.category_id).first()
        dormitory = db.query(Dormitory).filter(Dormitory.id == news.dormitory_id).first() if news.dormitory_id else None
        author = db.query(User).filter(User.id == news.author_id).first()

        news_responses.append({
            "id": news.id,
            "title": news.title,
            "content": news.content,
            "created_at": news.created_at.isoformat(),
            "author_id": news.author_id,
            "author_name": author.full_name if author else "Unknown",
            "image_url": news.image_url,
            "category_id": news.category_id,
            "category_name": category.name if category else "Unknown",
            "dormitory_id": news.dormitory_id,
            "dormitory_name": dormitory.name if dormitory else None,
            "is_private": news.is_private
        })

    total_pages = (total + per_page - 1) // per_page

    return PaginatedNewsResponse(
        items=news_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/news/{news_id}", response_model=NewsResponse)
def get_news_by_id(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Ограничение доступа: приватные новости видны только администраторам
    if news.is_private and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра приватной новости")

    category = db.query(Category).filter(Category.id == news.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == news.dormitory_id).first() if news.dormitory_id else None
    author = db.query(User).filter(User.id == news.author_id).first()

    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "created_at": news.created_at.isoformat(),
        "author_id": news.author_id,
        "author_name": author.full_name if author else "Unknown",
        "image_url": news.image_url,
        "category_id": news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": news.is_private
    }

@router.post("/news", response_model=NewsResponse)
def create_news(
    news: NewsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Проверка существования категории
    category = db.query(Category).filter(Category.id == news.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития, если указано
    if news.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == news.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    db_news = News(
        title=news.title,
        content=news.content,
        author_id=current_user.id,
        category_id=news.category_id,
        dormitory_id=news.dormitory_id,
        is_private=news.is_private,
        image_url=news.image_url
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)

    category = db.query(Category).filter(Category.id == db_news.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_news.dormitory_id).first() if db_news.dormitory_id else None
    author = db.query(User).filter(User.id == db_news.author_id).first()

    return {
        "id": db_news.id,
        "title": db_news.title,
        "content": db_news.content,
        "created_at": db_news.created_at.isoformat(),
        "author_id": db_news.author_id,
        "author_name": author.full_name if author else "Unknown",
        "image_url": db_news.image_url,
        "category_id": db_news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": db_news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_news.is_private
    }

@router.put("/news/{news_id}", response_model=NewsResponse)
def update_news(
    news_id: int,
    news_update: NewsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверка прав: только администратор или автор может редактировать
    if db_news.author_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования новости")

    # Проверка существования категории
    if news_update.category_id:
        category = db.query(Category).filter(Category.id == news_update.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития
    if news_update.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == news_update.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Обновление полей
    for key, value in news_update.dict(exclude_unset=True).items():
        setattr(db_news, key, value)

    db.commit()
    db.refresh(db_news)

    category = db.query(Category).filter(Category.id == db_news.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_news.dormitory_id).first() if db_news.dormitory_id else None
    author = db.query(User).filter(User.id == db_news.author_id).first()

    return {
        "id": db_news.id,
        "title": db_news.title,
        "content": db_news.content,
        "created_at": db_news.created_at.isoformat(),
        "author_id": db_news.author_id,
        "author_name": author.full_name if author else "Unknown",
        "image_url": db_news.image_url,
        "category_id": db_news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": db_news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_news.is_private
    }

@router.delete("/news/{news_id}", response_model=dict)
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверка прав: только администратор или автор может удалять
    if db_news.author_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления новости")

    db.delete(db_news)
    db.commit()

    return {"message": "Новость успешно удалена", "news_id": news_id}