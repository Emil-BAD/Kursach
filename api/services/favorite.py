# api/services/favorite.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from api.db.database import get_db
from api.db.models import User, Product, FavoriteProduct, Category, Dormitory  # Добавляем Category и Dormitory
from api.schemas.favorite import FavoriteCreate, FavoriteResponse, PaginatedFavoriteResponse
from api.core.dependencies import get_current_user

router = APIRouter(prefix="/favorites")

@router.post("", response_model=FavoriteResponse)
def add_to_favorites(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка роли: только студенты (role_id=10)
    if current_user.role_id != 10:
        raise HTTPException(status_code=403, detail="Только студенты могут добавлять товары в избранное")

    # Проверка существования товара
    product = db.query(Product).filter(Product.id == favorite.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка, не добавлен ли товар уже
    existing_favorite = db.query(FavoriteProduct).filter(
        FavoriteProduct.user_id == current_user.id,
        FavoriteProduct.product_id == favorite.product_id
    ).first()
    if existing_favorite:
        raise HTTPException(status_code=400, detail="Товар уже в избранном")

    # Создание записи
    db_favorite = FavoriteProduct(user_id=current_user.id, product_id=favorite.product_id)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)

    # Получение данных о товаре
    category = db.query(Category).filter(Category.id == product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first() if product.dormitory_id else None
    seller = db.query(User).filter(User.id == product.seller_id).first()

    return FavoriteResponse(
        id=db_favorite.id,
        user_id=db_favorite.user_id,
        product_id=db_favorite.product_id,
        created_at=db_favorite.created_at,
        product={
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "seller_id": product.seller_id,
            "seller_name": seller.full_name if seller else "Unknown",
            "image_urls": product.image_urls,
            "category_id": product.category_id,
            "category_name": category.name if category else "Unknown",
            "status": product.status,
            "dormitory_id": product.dormitory_id,
            "dormitory_name": dormitory.name if dormitory else None,
            "rejection_reason": product.rejection_reason
        }
    )

@router.get("", response_model=PaginatedFavoriteResponse)
def get_favorites(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка роли: только студенты (role_id=10)
    if current_user.role_id != 10:
        raise HTTPException(status_code=403, detail="Только студенты могут просматривать избранное")

    skip = (page - 1) * size
    query = db.query(FavoriteProduct).filter(FavoriteProduct.user_id == current_user.id)
    total = query.count()
    favorites = query.offset(skip).limit(size).all()

    favorite_responses = []
    for favorite in favorites:
        product = db.query(Product).filter(Product.id == favorite.product_id).first()
        if product:
            category = db.query(Category).filter(Category.id == product.category_id).first()
            dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first() if product.dormitory_id else None
            seller = db.query(User).filter(User.id == product.seller_id).first()

            favorite_responses.append(FavoriteResponse(
                id=favorite.id,
                user_id=favorite.user_id,
                product_id=favorite.product_id,
                created_at=favorite.created_at,
                product={
                    "id": product.id,
                    "title": product.title,
                    "description": product.description,
                    "price": float(product.price),
                    "seller_id": product.seller_id,
                    "seller_name": seller.full_name if seller else "Unknown",
                    "image_urls": product.image_urls,
                    "category_id": product.category_id,
                    "category_name": category.name if category else "Unknown",
                    "status": product.status,
                    "dormitory_id": product.dormitory_id,
                    "dormitory_name": dormitory.name if dormitory else None,
                    "rejection_reason": product.rejection_reason
                }
            ))

    total_pages = (total + size - 1) // size

    return PaginatedFavoriteResponse(
        items=favorite_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )