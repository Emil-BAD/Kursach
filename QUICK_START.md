# 🚀 QUICK START - Новая архитектура API

## Добавляем новый endpoint за 5 минут

Предположим нужно добавить управление **Dormitories** (общежития).

### Шаг 1: Repository

Файл: `api/repositories/dormitory.py`

```python
from typing import List
from sqlalchemy.orm import Session
from api.db.models import Dormitory
from api.repositories.base import BaseRepository

class DormitoryRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Dormitory)
    
    def get_all_paginated(self, skip: int, limit: int) -> List[Dormitory]:
        return self.db.query(Dormitory).offset(skip).limit(limit).all()
```

### Шаг 2: Service

Файл: `api/services/dormitory_service.py`

```python
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from api.db.models import Dormitory
from api.repositories.dormitory import DormitoryRepository
from api.core.exceptions import NotFoundError, DatabaseError

class DormitoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DormitoryRepository(db)
    
    def get_dorm_by_id(self, dorm_id: int) -> Dormitory:
        dorm = self.repo.get_by_id(dorm_id)
        if not dorm:
            raise NotFoundError("Общежитие", dorm_id)
        return dorm
    
    def get_all_dormitories(self, page: int = 1, page_size: int = 20) -> tuple:
        skip = (page - 1) * page_size
        dorms = self.repo.get_all_paginated(skip, page_size)
        total = self.repo.get_all_count()
        return dorms, total
    
    def create_dormitory(self, name: str, address: str, image_urls: list = None) -> Dormitory:
        try:
            return self.repo.create(
                name=name,
                address=address,
                image_urls=image_urls or []
            )
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()
```

### Шаг 3: Router

Файл: `api/v1/dormitories.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.db.models import User
from api.core.dependencies import get_current_user
from api.core.rbac import require_role, Role
from api.services.dormitory_service import DormitoryService
from api.schemas.common import paginate_response
from api.core.exceptions import APIException

router = APIRouter(prefix="/api/v1", tags=["dormitories"])

@router.get("/dormitories")
def list_dormitories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Получить список всех общежитий.
    
    **Возвращает:**
    ```json
    {
      "items": [
        {"id": 1, "name": "Корпус А", "address": "ул. Пушкина, 5", ...}
      ],
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
    ```
    """
    try:
        service = DormitoryService(db)
        dorms, total = service.get_all_dormitories(page, page_size)
        return paginate_response(dorms, page, page_size, total)
    except APIException:
        raise
    except Exception:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()

@router.get("/dormitories/{dorm_id}")
def get_dormitory(
    dorm_id: int,
    db: Session = Depends(get_db),
):
    """Получить данные одного общежития"""
    try:
        service = DormitoryService(db)
        return service.get_dorm_by_id(dorm_id)
    except APIException:
        raise
    except Exception:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()

@router.post("/dormitories")
def create_dormitory(
    name: str,
    address: str,
    image_urls: list = None,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Создать новое общежитие (только админ)"""
    try:
        service = DormitoryService(db)
        return service.create_dormitory(name, address, image_urls)
    except APIException:
        raise
    except Exception:
        from api.core.exceptions import InternalServerError
        raise InternalServerError()
```

### Шаг 4: Добавить в app.py

```python
# В начале app.py добавь импорт
from api.v1 import dormitories

# В раздел "Регистрация V1 роутеров" добавь
app.include_router(dormitories.router)
```

**Готово! 🎉**

---

## Другие примеры

### Если нужна проверка прав

```python
@router.post("/dormitories/{id}")
def edit_dormitory(
    dorm_id: int,
    name: str,
    current_user: User = Depends(require_permission(Permission.MANAGE_DORMITORIES)),
    db = Depends(get_db)
):
    # Только у кого есть право MANAGE_DORMITORIES
    ...
```

### Если нужно проверить что пользователь может работать только со своими данными

```python
@router.put("/me")
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    # current_user - это текущий пользователь
    # Можешь проверить что он редактирует только себя
    service = UserService(db)
    return service.update_user(current_user.id, **data.dict())
```

### Если нужны условные правила

```python
from api.core.rbac import has_role, has_permission

@router.get("/reports")
def get_reports(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    service = ReportService(db)
    
    # Админ видит всё, командант только свое общежитие
    if has_role(current_user, Role.ADMIN):
        reports = service.get_all_reports()
    elif has_role(current_user, Role.COMMANDANT):
        reports = service.get_dorm_reports(current_user.dorm_id)
    else:
        raise InsufficientPermissionsError()
    
    return reports
```

---

## Частые ошибки

### ❌ Неправильно: логика в роутере

```python
@router.get("/users")
def get_users(db = Depends(get_db)):
    users = db.query(User).filter(...).all()  # БАД!
    return users
```

### ✅ Правильно: логика в service

```python
@router.get("/users")
def get_users(db = Depends(get_db)):
    service = UserService(db)
    return service.get_all_users()  # ХОРОШО!
```

---

### ❌ Неправильно: HTTPException везде

```python
@router.post("/users")
def create(data, db = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=404, detail="Not found")  # БАД!
```

### ✅ Правильно: использовать exceptions.py

```python
@router.post("/users")
def create(data, db = Depends(get_db)):
    if not user:
        raise UserNotFoundError()  # ХОРОШО!
```

---

### ❌ Неправильно: разные форматы пагинации

```python
@router.get("/users")
def users1(page, db = Depends(get_db)):
    return {"data": [...], "page": page}  # Формат 1

@router.get("/products")
def products(page, db = Depends(get_db)):
    return {"items": [...], "total": total}  # Формат 2 - БАД!
```

### ✅ Правильно: единая пагинация

```python
@router.get("/users")
def users(page, db = Depends(get_db)):
    # ...
    return paginate_response(items, page, page_size, total)

@router.get("/products")
def products(page, db = Depends(get_db)):
    # ...
    return paginate_response(items, page, page_size, total)  # ХОРОШО!
```

---

## Структура ответа

Все успешные ответы:
```json
{
  "items": [...],           // Для списков
  "page": 1,               // Для paginated
  "total": 100,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```

Все ошибки (автоматически):
```json
{
  "detail": "Пользователь не найден"
}
```

---

## Команды

```bash
# Запустить
python -m uvicorn api.app:app --reload

# Документация
http://localhost:8000/api/docs

# Тесты (потом)
pytest tests/
```

---

**✨ Вот и всё! Теперь можешь добавлять endpoint'ы за 5 минут.**

Вопросы? Смотри:
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - подробная документация
- [`MIGRATION_GUIDE.md`](./MIGRATION_GUIDE.md) - примеры миграции
- Существующие роутеры: `api/v1/auth.py`, `api/v1/users.py`, `api/v1/news.py`
