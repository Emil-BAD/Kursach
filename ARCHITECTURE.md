# ЭТАП 2: Новая архитектура API

## 📁 Структура проекта

```
api/
├── core/                         # Ядро приложения
│   ├── config.py                # Настройки из .env
│   ├── auth.py                  # JWT логика
│   ├── dependencies.py          # FastAPI зависимости
│   ├── exceptions.py            # ✨ Централизованные ошибки
│   └── rbac.py                  # ✨ Роли и права (Role-Based Access Control)
│
├── db/
│   ├── database.py              # SQLAlchemy engine и session
│   └── models/                  # ORM модели
│
├── repositories/                # ✨ Data layer (новое)
│   ├── base.py                  # Базовый репозиторий с CRUD
│   ├── user.py                  # User специфичные методы БД
│   └── news.py                  # News специфичные методы БД
│
├── services/                    # ✨ Business logic layer (переделано)
│   ├── auth_service.py          # ✨ Use case: логин, регистрация, токены
│   ├── user_service.py          # ✨ Use case: управление пользователями
│   ├── news_service.py          # ✨ Use case: управление новостями
│   └── ...                      # Остальные старые сервисы (постепенно переписать)
│
├── schemas/                     # Pydantic модели
│   ├── common.py                # ✨ Базовые (PaginatedResponse, ErrorResponse)
│   └── ...
│
├── v1/                          # ✨ API v1 роутеры (новое)
│   ├── auth.py                  # GET/POST /api/v1/auth/*
│   ├── users.py                 # GET/POST /api/v1/users/*
│   ├── news.py                  # GET/POST /api/v1/news/*
│   └── ...                      # Остальные v1 роутеры
│
└── app.py                       # FastAPI приложение (главный файл)
```

## 🏗️ Архитектурные слои

### 1️⃣ Repository слой (`repositories/`)
**Что:** Работа с БД через ORM  
**Где:** `api/repositories/`  
**Примеры:**
```python
class UserRepository(BaseRepository):
    def get_by_student_card(self, student_card: str):
        return self.db.query(User).filter(...).first()
```

### 2️⃣ Service слой (`services/`)
**Что:** Бизнес-логика (валидация, вычисления, правила)  
**Где:** `api/services/{entity}_service.py`  
**Примеры:**
```python
class UserService:
    def create_user(self, ...):
        # Проверяем существование
        # Валидируем данные
        # Создаём через repository
        return user
```

### 3️⃣ Router слой (`v1/`)
**Что:** HTTP слой (валидация входа, преобразование выхода)  
**Где:** `api/v1/{entity}.py`  
**Примеры:**
```python
@router.post("/api/v1/users")
def create_user(data: UserCreate, db = Depends(get_db)):
    service = UserService(db)
    return service.create_user(...)
```

## 🔐 RBAC (Role-Based Access Control)

Все роли и права в одном месте: `api/core/rbac.py`

```python
from api.core.rbac import Role, require_role, require_permission

@router.get("/admin-only")
async def admin_endpoint(user = Depends(require_role(Role.ADMIN))):
    """Доступно только админам"""
    ...

@router.post("/products/moderate")
async def moderate(user = Depends(require_permission(Permission.MODERATE_PRODUCTS))):
    """Для тех кто может модерировать товары"""
    ...
```

Роли:
- `STUDENT` - студент (просмотр своих данных)
- `ADMIN` - администратор (все права)
- `COMMANDANT` - комендант общежития (управление его общежитием)
- `MODERATOR` - модератор (модерирование товаров)

## 📄 Пагинация

**Единый формат для всех GET списков:**

```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 150,
  "total_pages": 8,
  "has_next": true,
  "has_prev": false
}
```

**Использование:**
```python
from api.schemas.common import paginate_response

items, total = service.get_list(page, page_size)
result = paginate_response(items, page, page_size, total)
return result
```

## ❌ Обработка ошибок

**Централизованные исключения:**

```python
from api.core.exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    InsufficientPermissionsError,
    DatabaseError,
)

# Вместо:
# raise HTTPException(status_code=404, detail="User not found")

# Пишем:
raise UserNotFoundError(user_id)
```

Все исключения автоматически преобразуются в правильные HTTP ответы.

## 📍 Примеры миграции

См. [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)

### Быстрый пример: News

**Repository слой:**
```python
# api/repositories/news.py
class NewsRepository(BaseRepository):
    def get_all_paginated(self, skip, limit):
        return self.db.query(News).options(joinedload(News.author)).offset(skip).limit(limit).all()
```

**Service слой:**
```python
# api/services/news_service.py
class NewsService:
    def get_all_news(self, page, page_size):
        skip = (page - 1) * page_size
        news = self.repo.get_all_paginated(skip, page_size)
        total = self.repo.get_all_count()
        return news, total
```

**Router слой:**
```python
# api/v1/news.py
@router.get("/api/v1/news")
def list_news(page: int = 1, page_size: int = 20, db = Depends(get_db)):
    service = NewsService(db)
    news, total = service.get_all_news(page, page_size)
    return paginate_response(news, page, page_size, total)
```

## 🔄 Миграция старого кода

1. **Создай Repository:**
   - Наследуй `BaseRepository`
   - Добавь методы для специфичных запросов БД

2. **Создай Service:**
   - Инициализируй Repository
   - Напиши бизнес-логику
   - Бросай исключения из `api/core/exceptions.py`

3. **Создай Router в v1/:**
   - Используй `@require_role()` или `@require_permission()`
   - Вызывай service методы
   - Возвращай правильный формат (пагинация, ошибки и т.д.)

4. **Добавь в app.py:**
   - `from api.v1 import {entity}`
   - `app.include_router({entity}.router)`

## ✅ Преимущества новой архитектуры

| Аспект | До | После |
|--------|-----|--------|
| **Читаемость** | Логика разбросана | Каждый файл имеет одну роль |
| **Тестируемость** | Сложно мокировать | Легко тестировать слои отдельно |
| **Переиспользование** | Дублирование кода | DRY принцип |
| **N+1 queries** | Частые проблемы | Контролируется в repository |
| **Ошибки** | Разрозненные HTTPException | Централизованные исключения |
| **Роли/Права** | Магические числа везде | Вся логика в одном месте |
| **Пагинация** | Разные форматы | Единый стандарт |

## 🚀 Следующие шаги

1. ✅ RBAC система создана
2. ✅ Базовые repository и service
3. ✅ Auth, Users, News миграции
4. ⏳ Мигрировать Products
5. ⏳ Мигрировать Events
6. ⏳ Мигрировать Violations
7. ⏳ Добавить асинхронность (async/await)
8. ⏳ Кеширование (Redis)
9. ⏳ Логирование (structlog)

## 📞 Помощь

Если не ясно как мигрировать какой-то endpoint:

1. Посмотри [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
2. Найди похожий пример (напр. News)
3. Скопируй структуру, адаптируй под свой entity

---

**Версия:** 1.0  
**Дата:** 2024-04-22  
**Статус:** 🟢 В разработке (Этап 2)
