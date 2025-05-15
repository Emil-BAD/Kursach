from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from api.db.database import get_db
from api.db.models import News, User, Category, Dormitory
from api.schemas.news import NewsCreate, NewsUpdate, NewsResponse, PaginatedNewsResponse
from api.core.dependencies import get_current_user, get_current_admin
import cloudinary
import cloudinary.uploader
from fastapi.responses import JSONResponse
import json

router = APIRouter()

cloudinary.config(
    cloud_name="dnoyteqkn",
    api_key="359235721338924",
    api_secret="p-OSCOIhBEzKAkRsrH4Ksyqw1PY"
)

# GET /news (без изменений)
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
            "image_urls": news.image_urls,
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

# GET /news/{news_id} (без изменений)
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
        "image_urls": news.image_urls,
        "category_id": news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": news.is_private
    }

# POST /news (обновлён для загрузки изображений через multipart/form-data)
@router.post("/news", response_model=NewsResponse)
async def create_news(
    title: str = Form(...),
    content: str = Form(...),
    category_id: int = Form(...),
    dormitory_id: Optional[int] = Form(None),
    is_private: bool = Form(False),
    images: List[UploadFile] = File(None),  # Поле для загрузки файлов
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Ограничение доступа: только определённые администраторы
    admin_ids = [2, 7, 9, 11, 12]
    if current_user.role_id not in admin_ids:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания новости")

    # Проверка существования категории
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития, если указано
    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Загрузка изображений в Cloudinary
    image_urls = []
    if images:
        for image in images:
            try:
                # Загружаем файл в Cloudinary
                upload_result = cloudinary.uploader.upload(
                    image.file,
                    folder="news_images",  # Опционально: папка в Cloudinary
                    resource_type="image"
                )
                # Получаем URL загруженного изображения
                image_urls.append(upload_result["secure_url"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")

    # Создаём новость
    db_news = News(
        title=title,
        content=content,
        author_id=current_user.id,
        category_id=category_id,
        dormitory_id=dormitory_id,
        is_private=is_private,
        image_urls=image_urls if image_urls else None
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
        "image_urls": db_news.image_urls,
        "category_id": db_news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": db_news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_news.is_private
    }

# PUT /news/{news_id} (обновлён для загрузки изображений через multipart/form-data)
@router.put("/news/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: int,
    title: Optional[str] = Form(None),  # Опциональное поле
    content: Optional[str] = Form(None),  # Опциональное поле
    category_id: Optional[int] = Form(None),  # Опциональное поле
    dormitory_id: Optional[int] = Form(None),  # Опциональное поле
    is_private: Optional[bool] = Form(None),  # Опциональное поле
    images: List[UploadFile] = File(None),  # Опциональное поле для изображений
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Ограничение доступа: только определённые администраторы
    admin_ids = [2, 7, 9, 11, 12]
    if current_user.role_id not in admin_ids:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования новости")

    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверка существования категории
    if category_id is not None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития
    if dormitory_id is not None:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Обновление полей, если они переданы
    if title is not None:
        db_news.title = title
    if content is not None:
        db_news.content = content
    if category_id is not None:
        db_news.category_id = category_id
    if dormitory_id is not None:
        db_news.dormitory_id = dormitory_id
    if is_private is not None:
        db_news.is_private = is_private

    # Загрузка новых изображений в Cloudinary, если переданы
    if images:
        image_urls = []
        for image in images:
            try:
                # Загружаем файл в Cloudinary
                upload_result = cloudinary.uploader.upload(
                    image.file,
                    folder="news_images",
                    resource_type="image"
                )
                image_urls.append(upload_result["secure_url"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")
        # Обновляем список URL-адресов (заменяем старые на новые)
        db_news.image_urls = image_urls

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
        "image_urls": db_news.image_urls,
        "category_id": db_news.category_id,
        "category_name": category.name if category else "Unknown",
        "dormitory_id": db_news.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "is_private": db_news.is_private
    }

# DELETE /news/{news_id} (без изменений)
@router.delete("/news/{news_id}", response_model=dict)
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверка прав: только администраторы с определёнными ID или автор могут удалять
    admin_ids = [2, 7, 9, 11, 12]
    if db_news.author_id != current_user.id and current_user.id not in admin_ids:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления новости")

    db.delete(db_news)
    db.commit()

    return {"message": "Новость успешно удалена", "news_id": news_id}