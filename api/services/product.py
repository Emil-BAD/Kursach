from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from api.db.database import get_db
from api.db.models import Product, User, Category, Dormitory
from api.schemas.product import ProductCreate, ProductUpdate, ProductResponse, PaginatedProductResponse, ProductModeration
from api.core.dependencies import get_current_user, get_current_admin
import cloudinary
import cloudinary.uploader

router = APIRouter()

# Настройка Cloudinary
cloudinary.config(
    cloud_name="dnoyteqkn",
    api_key="359235721338924",
    api_secret="p-OSCOIhBEzKAkRsrH4Ksyqw1PY"
)

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

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if dormitory_id:
        query = query.filter(Product.dormitory_id == dormitory_id)
    if status:
        query = query.filter(Product.status == status)

    if current_user.role_id not in [1, 2, 3]:
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

        seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None
        seller_vk = seller.social_links.get("vk") if seller and seller.social_links else None

        # Преобразуем словарь в список, если он есть
        image_urls = list(product.image_urls.values()) if product.image_urls and isinstance(product.image_urls, dict) else product.image_urls or []

        product_responses.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "seller_id": product.seller_id,
            "seller_name": seller.full_name if seller else "Unknown",
            "created_at": product.created_at,
            "image_urls": image_urls,
            "category_id": product.category_id,
            "category_name": category.name if category else "Unknown",
            "status": product.status,
            "dormitory_id": product.dormitory_id,
            "dormitory_name": dormitory.name if dormitory else None,
            "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None,
            "seller_telegram": seller_telegram,
            "seller_vk": seller_vk
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

    if product.status == "pending" and current_user.role_id not in [1, 2, 3] and product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра этого товара")

    category = db.query(Category).filter(Category.id == product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == product.dormitory_id).first() if product.dormitory_id else None
    seller = db.query(User).filter(User.id == product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None
    seller_vk = seller.social_links.get("vk") if seller and seller.social_links else None

    # Преобразуем словарь в список, если он есть
    image_urls = list(product.image_urls.values()) if product.image_urls and isinstance(product.image_urls, dict) else product.image_urls or []

    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": float(product.price),
        "seller_id": product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": product.created_at,
        "image_urls": image_urls,
        "category_id": product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": product.status,
        "dormitory_id": product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None,
        "seller_telegram": seller_telegram,
        "seller_vk": seller_vk
    }

@router.post("/products", response_model=ProductResponse)
async def create_product(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    dormitory_id: Optional[int] = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория не найдена")

    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие не найдено")

    image_urls = []
    if images:
        for i, image in enumerate(images, 1):
            try:
                upload_result = cloudinary.uploader.upload(
                    image.file,
                    folder="products",
                    resource_type="image"
                )
                image_urls.append(upload_result["secure_url"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения {i}: {str(e)}")

    db_product = Product(
        title=title,
        description=description,
        price=price,
        seller_id=current_user.id,
        image_urls=image_urls if image_urls else None,
        category_id=category_id,
        dormitory_id=dormitory_id,
        status="pending"
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None
    seller_vk = seller.social_links.get("vk") if seller and seller.social_links else None

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls or [],
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": None,
        "seller_telegram": seller_telegram,
        "seller_vk": seller_vk
    }

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    category_id: Optional[int] = Form(None),
    dormitory_id: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    if db_product.seller_id != current_user.id and current_user.role_id != 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования товара")

    if db_product.status == "approved" and current_user.role_id != 2:
        raise HTTPException(status_code=400, detail="Нельзя редактировать товар после одобрения")

    if category_id is not None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Категория с указанным ID не найдена")

    if dormitory_id is not None:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие с указанным ID не найдено")

    if images:
        image_urls = []
        for i, image in enumerate(images, 1):
            try:
                upload_result = cloudinary.uploader.upload(
                    image.file,
                    folder="products",
                    resource_type="image"
                )
                image_urls.append(upload_result["secure_url"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения {i}: {str(e)}")
        db_product.image_urls = image_urls

    if title is not None and title.strip() != "":
        db_product.title = title
    if description is not None and description.strip() != "":
        db_product.description = description
    if price is not None:
        db_product.price = price
    if category_id is not None:
        db_product.category_id = category_id
    if dormitory_id is not None:
        db_product.dormitory_id = dormitory_id

    if status is not None and status.strip() != "":
        allowed_statuses = ["pending", "approved", "rejected"]
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые значения: {allowed_statuses}")
        
        if status in ["approved", "rejected"] and current_user.role_id != 2:
            raise HTTPException(status_code=403, detail="Только администратор может устанавливать статус 'approved' или 'rejected'")
        
        db_product.status = status
        if status != "rejected":
            db_product.rejection_reason = None

    elif any([
        title is not None and title.strip() != "",
        description is not None and description.strip() != "",
        price is not None,
        category_id is not None,
        dormitory_id is not None,
        images and any(image.filename for image in images)
    ]):
        if current_user.role_id != 2:
            db_product.status = "pending"
            db_product.rejection_reason = None

    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None
    seller_vk = seller.social_links.get("vk") if seller and seller.social_links else None

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls or [],
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": db_product.rejection_reason,
        "seller_telegram": seller_telegram,
        "seller_vk": seller_vk
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

    if current_user.role_id not in [1, 2, 3]:
        raise HTTPException(status_code=403, detail="Недостаточно прав для модерации товара")

    db_product.status = moderation.status
    db_product.rejection_reason = moderation.rejection_reason if moderation.status == "rejected" else None

    db.commit()
    db.refresh(db_product)

    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None
    seller_vk = seller.social_links.get("vk") if seller and seller.social_links else None

    # Преобразуем словарь в список, если он есть
    image_urls = list(db_product.image_urls.values()) if db_product.image_urls and isinstance(db_product.image_urls, dict) else db_product.image_urls or []

    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": seller.full_name if seller else "Unknown",
        "created_at": db_product.created_at,
        "image_urls": image_urls,
        "category_id": db_product.category_id,
        "category_name": category.name if category else "Unknown",
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory.name if dormitory else None,
        "rejection_reason": db_product.rejection_reason,
        "seller_telegram": seller_telegram,
        "seller_vk": seller_vk
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

    if db_product.seller_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления товара")

    db.delete(db_product)
    db.commit()

    return {"message": "Товар успешно удалён", "product_id": product_id}