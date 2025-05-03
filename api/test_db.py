# -*- coding: utf-8 -*-
from db.database import SessionLocal
from db.models import User
from core.auth import get_password_hash

# Создаем сессию
db = SessionLocal()

# Пробуем создать тестового администратора
try:
    # Хешируем пароль
    hashed_password = get_password_hash("admin123")  # Пароль: admin123
    admin = User(
        student_card="ADMIN001",
        password_hash=hashed_password,
        full_name="Администратор",
        contract_number=99999,
        role_id=2  # Роль администратора
    )
    db.add(admin)
    db.commit()
    print("Администратор успешно создан:", admin.id)
except Exception as e:
    print("Ошибка:", e)
finally:
    db.close()