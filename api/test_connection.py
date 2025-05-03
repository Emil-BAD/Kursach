import psycopg2
from core.config import settings

# Пробуем подключиться к базе
try:
    conn = psycopg2.connect(settings.DATABASE_URL)
    print("Подключение успешно!")
    conn.close()
except Exception as e:
    print("Ошибка:", e)