# api/services/product.py
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

        # Извлекаем Telegram-ссылку из social_links продавца
        seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None

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
            "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None,
            "seller_telegram": seller_telegram  # Добавляем Telegram-ссылку
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

    # Извлекаем Telegram-ссылку из social_links продавца
    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None

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
        "rejection_reason": product.rejection_reason if current_user.role_id in [1, 2, 3] or product.seller_id == current_user.id else None,
        "seller_telegram": seller_telegram  # Добавляем Telegram-ссылку
    }

@router.post("/products", response_model=ProductResponse)
def create_product(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    dormitory_id: Optional[int] = Form(None),
    image_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка прав
    if current_user.role_id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Проверка категории
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Категория не найдена")

    # Проверка общежития
    if dormitory_id:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=400, detail="Общежитие не найдено")

    # Загрузка изображений
    image_urls = {}
    if image_files:
        for i, file in enumerate(image_files):
            if file and file.filename:
                response = cloudinary.uploader.upload(
                    file.file,
                    folder="products",
                    resource_type="image"
                )
                image_urls[f"image_{i+1}"] = response["secure_url"]

    # Создание продукта
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

    # Формирование ответа
    dormitory_name = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first().name if db_product.dormitory_id else None
    return {
        "id": db_product.id,
        "title": db_product.title,
        "description": db_product.description,
        "price": float(db_product.price),
        "seller_id": db_product.seller_id,
        "seller_name": current_user.full_name,
        "created_at": db_product.created_at,
        "image_urls": db_product.image_urls,
        "category_id": db_product.category_id,
        "category_name": category.name,
        "status": db_product.status,
        "dormitory_id": db_product.dormitory_id,
        "dormitory_name": dormitory_name,
        "rejection_reason": None,
        "seller_telegram": current_user.social_links.get("telegram") if current_user.social_links else None
    }

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    dormitory_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    image_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Если image_files содержит некорректные данные, это уже обработано FastAPI валидацией
    # Вместо обработки здесь, нужно правильно отправлять запрос

    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка прав: только продавец или администратор (role_id=2) может редактировать
    if db_product.seller_id != current_user.id and current_user.role_id != 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования товара")

    # Проверка: нельзя редактировать товар после одобрения (кроме админов)
    if db_product.status == "approved" and current_user.role_id != 2:
        raise HTTPException(status_code=400, detail="Нельзя редактировать товар после одобрения")

    # Преобразование пустых строк в None и валидация числовых полей
    if price == "":
        price = None
    else:
        try:
            price = float(price) if price else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле price должно быть числом")

    if category_id == "":
        category_id = None
    else:
        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле category_id должно быть целым числом")

    if dormitory_id == "":
        dormitory_id = None
    else:
        try:
            dormitory_id = int(dormitory_id) if dormitory_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле dormitory_id должно быть целым числом")

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

    # Обновление изображений через Cloudinary
    if image_files and any(file.filename for file in image_files):  # Проверяем, есть ли файлы с именем
        image_urls = db_product.image_urls or {}
        for i, file in enumerate(image_files, len(image_urls) + 1):
            if file and file.filename:
                try:
                    response = cloudinary.uploader.upload(
                        file.file,
                        folder="products",
                        resource_type="image",
                        public_id=f"product_{product_id}_image_{i}"
                    )
                    image_urls[f"image_{i}"] = response["secure_url"]
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")
        db_product.image_urls = image_urls

    # Обновление полей только если переданы непустые значения
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

    # Обновление статуса
    if status is not None and status.strip() != "":
        allowed_statuses = ["pending", "approved", "rejected"]
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые значения: {allowed_statuses}")
        
        if status in ["approved", "rejected"] and current_user.role_id != 2:
            raise HTTPException(status_code=403, detail="Только администратор может устанавливать статус 'approved' или 'rejected'")
        
        db_product.status = status
        
        if status != "rejected":
            db_product.rejection_reason = None

    # Если статус не передан, устанавливаем "pending" при любом изменении (кроме админов)
    elif any([
        (title is not None and title.strip() != ""),
        (description is not None and description.strip() != ""),
        price is not None,
        category_id is not None,
        dormitory_id is not None,
        image_files and any(file.filename for file in image_files)
    ]):
        if current_user.role_id != 1:
            db_product.status = "pending"
            db_product.rejection_reason = None

    db.commit()
    db.refresh(db_product)

    # Получение связанных данных
    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None

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
        "rejection_reason": db_product.rejection_reason,
        "seller_telegram": seller_telegram
    }

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    dormitory_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    image_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Если image_files содержит некорректные данные, это уже обработано FastAPI валидацией
    # Вместо обработки здесь, нужно правильно отправлять запрос

    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка прав: только продавец или администратор (role_id=2) может редактировать
    if db_product.seller_id != current_user.id and current_user.role_id != 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования товара")

    # Проверка: нельзя редактировать товар после одобрения (кроме админов)
    if db_product.status == "approved" and current_user.role_id != 2:
        raise HTTPException(status_code=400, detail="Нельзя редактировать товар после одобрения")

    # Преобразование пустых строк в None и валидация числовых полей
    if price == "":
        price = None
    else:
        try:
            price = float(price) if price else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле price должно быть числом")

    if category_id == "":
        category_id = None
    else:
        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле category_id должно быть целым числом")

    if dormitory_id == "":
        dormitory_id = None
    else:
        try:
            dormitory_id = int(dormitory_id) if dormitory_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Поле dormitory_id должно быть целым числом")

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

    # Обновление изображений через Cloudinary
    if image_files and any(file.filename for file in image_files):  # Проверяем, есть ли файлы с именем
        image_urls = db_product.image_urls or {}
        for i, file in enumerate(image_files, len(image_urls) + 1):
            if file and file.filename:
                try:
                    response = cloudinary.uploader.upload(
                        file.file,
                        folder="products",
                        resource_type="image",
                        public_id=f"product_{product_id}_image_{i}"
                    )
                    image_urls[f"image_{i}"] = response["secure_url"]
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")
        db_product.image_urls = image_urls

    # Обновление полей только если переданы непустые значения
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

    # Обновление статуса
    if status is not None and status.strip() != "":
        allowed_statuses = ["pending", "approved", "rejected"]
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые значения: {allowed_statuses}")
        
        if status in ["approved", "rejected"] and current_user.role_id != 1:
            raise HTTPException(status_code=403, detail="Только администратор может устанавливать статус 'approved' или 'rejected'")
        
        db_product.status = status
        
        if status != "rejected":
            db_product.rejection_reason = None

    # Если статус не передан, устанавливаем "pending" при любом изменении (кроме админов)
    elif any([
        (title is not None and title.strip() != ""),
        (description is not None and description.strip() != ""),
        price is not None,
        category_id is not None,
        dormitory_id is not None,
        image_files and any(file.filename for file in image_files)
    ]):
        if current_user.role_id != 1:
            db_product.status = "pending"
            db_product.rejection_reason = None

    db.commit()
    db.refresh(db_product)

    # Получение связанных данных
    category = db.query(Category).filter(Category.id == db_product.category_id).first()
    dormitory = db.query(Dormitory).filter(Dormitory.id == db_product.dormitory_id).first() if db_product.dormitory_id else None
    seller = db.query(User).filter(User.id == db_product.seller_id).first()

    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None

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
        "rejection_reason": db_product.rejection_reason,
        "seller_telegram": seller_telegram
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

    # Извлекаем Telegram-ссылку из social_links продавца
    seller_telegram = seller.social_links.get("telegram") if seller and seller.social_links else None

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
        "rejection_reason": db_product.rejection_reason,
        "seller_telegram": seller_telegram  # Добавляем Telegram-ссылку
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