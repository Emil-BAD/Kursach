# Курсовой проект: Backend-сервис на FastAPI

Современный REST API, реализованный на **FastAPI** для курсовой работы.

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=for-the-badge&logo=postgresql&logoColor=white)

## О проекте

Это backend-сервис, созданный в рамках курсовой работы.  
Цель — продемонстрировать умение проектировать чистый REST API, работать с валидацией данных, обрабатывать CRUD-операции и правильно структурировать проект на FastAPI.

## Технологии

- Python 3.9+
- FastAPI
- Pydantic (валидация и схемы)
- Uvicorn (ASGI-сервер)
- SQLite (базовая реализация) / возможность перехода на PostgreSQL
- (опционально) GitHub Actions — CI/CD

## Основной функционал

- Получение списка объектов → `GET /items`
- Получение одного объекта → `GET /items/{id}`
- Создание объекта → `POST /items`
- Обновление объекта → `PUT /items/{id}`
- Удаление объекта → `DELETE /items/{id}`
- Валидация входных данных
- Корректная обработка ошибок (404, 422 и др.)
- Автоматическая документация OpenAPI

## Быстрый старт

### 1. Клонируем репозиторий

```bash
git clone https://github.com/Emil-BAD/Kursach.git
cd Kursach
```

### 2. Создаём и активируем виртуальное окружение

```bash
# Создаём виртуальное окружение
python -m venv venv
```

**Активация** (выбери свою ОС):

- **Windows** (cmd / PowerShell)

```bash
venv\Scripts\activate
```

- **Windows** (PowerShell, если выдаёт ошибку — разреши скрипты):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
venv\Scripts\activate
```

- **Linux / macOS**

```bash
source venv/bin/activate
```

После активации в начале строки терминала должен появиться `(venv)`.

### 3. Устанавливаем зависимости

```bash
# Рекомендую обновить pip
python -m pip install --upgrade pip

# Устанавливаем все пакеты из requirements.txt
pip install -r requirements.txt
```

### 4. Запускаем сервер

```bash
uvicorn api.main:app --reload --port 8000
```

- `--reload` — автоматически перезапускает сервер при изменении кода (удобно для разработки)
- Сервер будет доступен по адресу: **http://127.0.0.1:8000** или **http://localhost:8000**

### 5. Документация API (открой в браузере)

- Интерактивная Swagger UI:  
  http://127.0.0.1:8000/docs

- Более читаемая ReDoc:  
  http://127.0.0.1:8000/redoc

Готово! Можно тестировать API.

## Структура проекта

```
Kursach/
├── api/
│   ├── __init__.py
│   ├── main.py             # точка входа, подключение роутеров
│   ├── database.py         # подключение к БД
│   ├── models.py           # структуры таблиц / SQL-запросы
│   ├── schemas.py          # Pydantic модели (вход/выход)
│   └── endpoints/
│       ├── __init__.py
│       └── items.py        # роутер с CRUD-операциями
├── requirements.txt
├── .gitignore
└── README.md
```

## Примеры запросов (cURL)

### Получить все записи

```bash
curl http://127.0.0.1:8000/items
```

### Создать запись

```bash
curl -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Ноутбук", "description": "Мощный игровой ноут", "price": 125000}'
```

### Обновить запись (id = 1)

```bash
curl -X PUT http://127.0.0.1:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Ноутбук PRO", "price": 149000}'
```

## Планы по доработке (Roadmap)

- [ ] Переход на PostgreSQL + SQLAlchemy / Tortoise-ORM
- [ ] Аутентификация (JWT + refresh-токены)
- [ ] Тесты (pytest + TestClient)
- [ ] Docker + docker-compose
- [ ] Миграции через Alembic
- [ ] Пагинация, фильтры, поиск
- [ ] Rate limiting
- [ ] Логирование (структурированное)

## Автор

**Emil-BAD**  
Открыт к предложениям по стажировкам, фрилансу и удалённой работе.

Если проект понравился — ставь ⭐ на GitHub!

Готов ответить на любые вопросы и помочь с доработками ✌️
