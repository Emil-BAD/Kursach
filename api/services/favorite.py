# api/services/favorite.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import FavoriteProduct, Product, User
from api.schemas.favorite import FavoriteCreate, FavoriteResponse, PaginatedFavoriteResponse
from api.services.user_helpers import is_student

router = APIRouter(prefix="/favorites")


def _build_product_payload(product: Product) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": float(product.price),
        "seller_id": product.seller_id,
        "seller_name": product.seller.full_name if product.seller else "Unknown",
        "image_urls": product.image_urls or [],
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else "Unknown",
        "status": product.status,
        "dormitory_id": product.dormitory_id,
        "dormitory_name": product.dormitory.name if product.dormitory else None,
        "rejection_reason": product.rejection_reason,
    }


def _build_favorite_response(item: FavoriteProduct) -> FavoriteResponse:
    return FavoriteResponse(
        id=item.id,
        user_id=item.user_id,
        product_id=item.product_id,
        created_at=item.created_at,
        product=_build_product_payload(item.product),
    )


@router.post("", response_model=FavoriteResponse)
def add_to_favorites(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Добавить товар в избранное.

    Что делает:
    Создаёт связь между студентом и товаром маркетплейса.

    Что принимает:
    ```json
    {
      "product_id": 12
    }
    ```

    Что возвращает:
    Объект избранного с вложенной информацией о товаре.
    """
    if not is_student(current_user):
        raise HTTPException(status_code=403, detail="Только студенты могут добавлять товары в избранное")

    product = (
        db.query(Product)
        .options(joinedload(Product.seller), joinedload(Product.category), joinedload(Product.dormitory))
        .filter(Product.id == favorite.product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    existing = (
        db.query(FavoriteProduct)
        .filter(
            FavoriteProduct.user_id == current_user.id,
            FavoriteProduct.product_id == favorite.product_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Товар уже в избранном")

    db_favorite = FavoriteProduct(user_id=current_user.id, product_id=favorite.product_id)
    db.add(db_favorite)
    db.commit()

    created = (
        db.query(FavoriteProduct)
        .options(
            joinedload(FavoriteProduct.product).joinedload(Product.seller),
            joinedload(FavoriteProduct.product).joinedload(Product.category),
            joinedload(FavoriteProduct.product).joinedload(Product.dormitory),
        )
        .filter(FavoriteProduct.id == db_favorite.id)
        .first()
    )
    return _build_favorite_response(created)


@router.get("", response_model=PaginatedFavoriteResponse)
def get_favorites(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список избранных товаров текущего студента.

    Что делает:
    Возвращает избранные товары с пагинацией.

    Что принимает:
    Query-параметры:
    - `page`
    - `size`

    Что возвращает:
    ```json
    {
      "items": [...],
      "total": 2,
      "page": 1,
      "size": 10,
      "total_pages": 1
    }
    ```
    """
    if not is_student(current_user):
        raise HTTPException(status_code=403, detail="Только студенты могут просматривать избранное")

    skip = (page - 1) * size
    query = (
        db.query(FavoriteProduct)
        .options(
            joinedload(FavoriteProduct.product).joinedload(Product.seller),
            joinedload(FavoriteProduct.product).joinedload(Product.category),
            joinedload(FavoriteProduct.product).joinedload(Product.dormitory),
        )
        .filter(FavoriteProduct.user_id == current_user.id)
    )
    total = query.count()
    favorites = (
        query.order_by(FavoriteProduct.created_at.desc(), FavoriteProduct.id.desc())
        .offset(skip)
        .limit(size)
        .all()
    )

    return PaginatedFavoriteResponse(
        items=[_build_favorite_response(item) for item in favorites],
        total=total,
        page=page,
        size=size,
        total_pages=(total + size - 1) // size,
    )
