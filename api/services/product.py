from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from db.models import Product, User, Category, Dormitory
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, PaginatedProductResponse, ProductModeration
from core.dependencies import get_current_user, get_current_admin

router = APIRouter()

@router.get("/products", response_model=PaginatedProductResponse)
def get_products(
    page: int = 1,
    size: int = 10,
    category_id: int = None,
    dormitory_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * size
    query = db.query(Product)

    # Фильтрация
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if dormitory_id:
        query = query.filter(Product.dormitory_id == dormitory_id)
    if status:
        query = query.filter(Product.status == status)

    # Ограничение доступа: пользователи видят только свои товары со статусом "pending", остальные — только "approved"
    if current_user.role_id not in [1, 2, 3]:  # Не администратор и не член совета
        query = query.filter(
            (Product.status == "approved") | 
            ((Product.status == "pending") & (Product.seller_id == current_user.id))
        )

    total = query.count()
    products = query.offset(skip).limit(size).all()

    product_responses = []
    for product in products:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first() if product.dormitory_id else None
        seller = db.query(User).filter(User.id == product.seller_id).first()

        product_responses.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "seller_id": product.seller_id,
            "seller_name": seller.full_name if seller else "Unknown",
            "created_at": product.created_at,
            "image_urls": product.image_urls,
            "category_id": product.category_id,
            "category_name": category.name if category else "Unknown",
            "status": product.status,
            "dormitory_id": product.dormitory_id,
            "dormitory_name": dormitory.name if dormitory else None,
            "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None
        })

    total_pages = (total + size - 1) // size

    return PaginatedProductResponse(
        items=product_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Ограничение доступа
    if product.status == "pending" and current_user.role_id not in [1, 2, 3] and product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра этого товара")

    category = db.query(Category).filter(Category.id == product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first() if product.dormitory_id else None
    seller = db.query(User).filter(User.id == product.seller_id).first()

    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": float(product.price),
        "seller_id": product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": product.created_at,
        "image_urls": product.image_urls,
        "category_id": product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": product.status,
        "dormitory_id": product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None
    }

@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Только студенты, администраторы или члены совета могут создавать товары
    if current_user.role_id not in [1, 2, 3, 4]:  # Administrator, CouncilPresident, CouncilMember, Student
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания товара")

    # Проверка существования категории
    category = db.query(Category).filter(Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития (если указано)
    if product.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Создание нового товара
    db_product = Product(
        title=product.title,
        description=product.description,
        price=product.price,
        seller_id=current_user.id,
        image_urls=product.image_urls,
        category_id=product.category_id,
        dormitory_id=product.dormitory_id,
        status="pending"
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls,
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": None
    }

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка прав: только продавец может редактировать, если товар на модерации или отклонён
    if db_product.seller_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования товара")

    if db_product.status == "approved":
        raise HTTPException(status_code=400, detail="Нельзя редактировать товар после одобрения")

    # Проверка существования категории
    if product_update.category_id:
        category = db.query(Category).filter(Category.id == product_update.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    # Проверка существования общежития
    if product_update.dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == product_update.dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    # Обновление полей
    for key, value in product_update.dict(exclude_unset=True).items():
        setattr(db_product, key, value)

    # Сброс статуса на "pending" при редактировании
    db_product.status = "pending"
    db_product.rejection_reason = None

    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls,
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": db_product.rejection_reason
    }

@router.put("/products/{product_id}/moderate", response_model=ProductResponse)
def moderate_product(
    product_id: int,
    moderation: ProductModeration,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Только администраторы или члены совета могут модерировать
    if current_user.role_id not in [1, 2, 3]:  # Administrator, CouncilPresident, CouncilMember
        raise HTTPException(status_code=403, detail="Недостаточно прав для модерации товара")

    # Обновление статуса и причины отклонения
    db_product.status = moderation.status
    db_product.rejection_reason = moderation.rejection_reason if moderation.status == "rejected" else None

    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls,
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": db_product.rejection_reason
    }

@router.delete("/products/{product_id}", response_model=dict)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка прав: только продавец или администратор может удалить
    if db_product.seller_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления товара")

    db.delete(db_product)
    db.commit()

    return {"message": "Товар успешно удалён", "product_id": product_id}