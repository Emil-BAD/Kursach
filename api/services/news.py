# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from db.models import News, User, Category, Dormitory
from core.dependencies import get_current_admin

router = APIRouter()

@router.get("/news", response_model=List[dict])
def get_news(db: Session = Depends(get_db)):
    news = db.query(News).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "created_at": n.created_at.isoformat(),
            "author": n.author.full_name,
            "is_private": n.is_private,
            "image_url": n.image_url  # Используем правильное имя атрибута
        }
        for n in news
    ]

@router.post("/news", response_model=dict)
def create_news(
    title: str = Body(...),
    content: str = Body(...),
    category_id: int = Body(...),
    dormitory_id: int = Body(None),
    is_private: bool = Body(False),
    image_url: str = Body(None),  # Добавляем поддержку image_url
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Проверка существования категории
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития, если указано
    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    news = News(
        title=title,
        content=content,
        author_id=current_user.id,
        category_id=category_id,
        dormitory_id=dormitory_id,
        is_private=is_private,
        image_url=image_url  # Используем правильное имя атрибута
    )
    db.add(news)
    db.commit()
    db.refresh(news)
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "created_at": news.created_at.isoformat(),
        "author": news.author.full_name,
        "is_private": news.is_private,
        "image_url": news.image_url  # Возвращаем правильное имя атрибута
    }