# -*- coding: utf-8 -*-
"""
ЭТАП 2: МИГРАЦИЯ НА НОВУЮ АРХИТЕКТУРУ
=====================================

Этот файл показывает как переносить старые endpoint'ы на новую архитектуру v1.

ДО (старый код):
================

@router.get("/products")
def get_products(page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    # Логика прямо в роутере - ПЛОХО!
    skip = (page - 1) * size
    query = db.query(Product)
    total = query.count()
    products = query.offset(skip).limit(size).all()
    
    product_responses = []
    for product in products:
        category = db.query(Category).filter(...).first()  # N+1 query!
        ...
    
    return {"items": product_responses, "total": total, "page": page}


НОВАЯ АРХИТЕКТУРА:
==================

1. REPOSITORY СЛОЙ (новый)
--------------------------
# api/repositories/product.py

class ProductRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Product)
    
    def get_with_category(self, product_id: int):
        from sqlalchemy.orm import joinedload
        return (
            self.db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.id == product_id)
            .first()
        )
    
    def get_all_paginated(self, skip: int, limit: int):
        return self.db.query(Product).offset(skip).limit(limit).all()
    
    def count_all(self):
        return self.db.query(Product).count()


2. SERVICE СЛОЙ (бизнес-логика)
--------------------------------
# api/services/product_service.py

class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)
    
    def get_products_list(self, page: int, page_size: int):
        \"\"\"Получить список товаров с пагинацией\"\"\"
        skip = (page - 1) * page_size
        products = self.repo.get_all_paginated(skip, page_size)
        total = self.repo.count_all()
        return products, total


3. ROUTER СЛОЙ (тонкий, только валидация)
------------------------------------------
# api/v1/products.py

@router.get("/products")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    \"\"\"
    Получить список товаров.
    
    Параметры:
    - page: номер страницы (по умолчанию 1)
    - page_size: размер страницы (по умолчанию 20, макс 100)
    
    Возвращает:
    {
        "items": [...],
        "page": 1,
        "page_size": 20,
        "total": 100,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false
    }
    \"\"\"
    try:
        service = ProductService(db)
        products, total = service.get_products_list(page, page_size)
        result = paginate_response(products, page, page_size, total)
        return result
    except APIException:
        raise
    except Exception as e:
        raise InternalServerError()


ПРИНЦИПЫ НОВОЙ АРХИТЕКТУРЫ:
===========================

1. РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ:
   - Repository: ТОЛЬКО работа с БД (query'з, create, update, delete)
   - Service: ТОЛЬКО бизнес-логика (валидация, вычисления, правила)
   - Router: ТОЛЬКО HTTP слой (валидация входных данных, преобразование response)

2. ОБРАБОТКА ОШИБОК:
   - Используй централизованные исключения из api/core/exceptions.py
   - Не бросай raw HTTPException с номерами!
   
   ДО:  raise HTTPException(status_code=404, detail="User not found")
   ПОСЛЕ: raise UserNotFoundError(user_id)

3. RBAC (РОЛИ И ПРАВА):
   - Используй @require_role() или @require_permission() вместо разрозненных проверок
   
   ДО:  if current_user.role.id not in [1, 2, 3]:
            raise HTTPException(...)
   
   ПОСЛЕ: current_user: User = Depends(require_role(Role.ADMIN, Role.COMMANDANT))

4. ПАГИНАЦИЯ:
   - Используй единый формат paginate_response()
   - Все GET списки должны возвращать: items, page, page_size, total, total_pages, has_next, has_prev

5. ФАЙЛЫ В POST/PUT:
   - Разделяй загрузку файлов и создание объекта на два шага
   
   ДОМ (плохо - multipart):
   @router.post("/products")
   def create(title: str = Form(), file: UploadFile = File(), ...):
       ...
   
   ПОСЛЕ (хорошо):
   # Шаг 1: Upload файла
   @router.post("/upload")
   def upload_image(file: UploadFile, ...):
       url = cloudinary.upload(file)
       return {"image_url": url}
   
   # Шаг 2: Create с image_url
   @router.post("/products")
   def create(data: ProductCreate):  # image_url уже в data
       ...


ПРИМЕР ПОЛНОЙ МИГРАЦИИ: News Service
=====================================

ДО (старый код из api/services/news.py):
-----------------------------------------
@router.get("/news")
def get_news(page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    skip = (page - 1) * size
    query = db.query(News).order_by(desc(News.created_at))
    total = query.count()
    news = query.offset(skip).limit(size).all()
    
    news_responses = []
    for new in news:
        author = db.query(User).filter(User.id == new.author_id).first()
        responses.append({
            "id": new.id,
            "title": new.title,
            "author_name": author.full_name if author else "Unknown",
        })
    
    return {"items": news_responses, "total": total}


ПОСЛЕ (новая архитектура):
--------------------------

# 1. Repository слой
# api/repositories/news.py

class NewsRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, News)
    
    def get_all_paginated(self, skip: int, limit: int):
        from sqlalchemy import desc
        from sqlalchemy.orm import joinedload
        
        return (
            self.db.query(News)
            .options(joinedload(News.author))  # Загружаем автора одним query!
            .order_by(desc(News.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_all(self):
        return self.db.query(News).count()


# 2. Service слой
# api/services/news_service.py

class NewsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NewsRepository(db)
    
    def get_news_list(self, page: int, page_size: int):
        skip = (page - 1) * page_size
        news = self.repo.get_all_paginated(skip, page_size)
        total = self.repo.count_all()
        return news, total


# 3. Router слой
# api/v1/news.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.services.news_service import NewsService
from api.schemas.news import NewsResponse
from api.schemas.common import paginate_response
from api.core.exceptions import APIException

router = APIRouter(prefix="/api/v1", tags=["news"])

@router.get("/news", response_model=dict)
def list_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    \"\"\"Получить список новостей\"\"\"
    try:
        service = NewsService(db)
        news, total = service.get_news_list(page, page_size)
        result = paginate_response(news, page, page_size, total)
        return result
    except APIException:
        raise
    except Exception:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()


КОНТРОЛЬНЫЙ СПИСОК МИГРАЦИИ:
============================

Для каждого старого endpoint'а:

[ ] 1. Создал Repository класс в api/repositories/{entity}.py
    - Наследует BaseRepository
    - Содержит методы для работы с БД
    
[ ] 2. Создал Service класс в api/services/{entity}_service.py
    - Инициализирует Repository
    - Содержит бизнес-логику
    - Бросает исключения из api/core/exceptions.py
    
[ ] 3. Создал Router в api/v1/{entity}.py
    - Тонкий слой: валидация + вызов service
    - Использует @require_role() для проверки прав
    - Возвращает правильный формат (для пагинации - paginate_response)
    
[ ] 4. Добавил router в app.py через app.include_router(...)
    
[ ] 5. Задокументировал docstring'ом:
    - Что делает endpoint
    - Пример входных данных (JSON)
    - Пример выходных данных (JSON)


РЕЗУЛЬТАТЫ:
===========

✓ Чистый код: логика разделена по слоям
✓ Легче тестировать: каждый слой независим
✓ Нет N+1 query проблем: joinedload в repository
✓ Единообразные ошибки: централизованные исключения
✓ Единая пагинация: один формат для всех
✓ RBAC: понятные роли вместо магических чисел
✓ Читаемо: каждый файл имеет одну ответственность
"""
