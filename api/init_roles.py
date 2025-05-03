# -*- coding: utf-8 -*-
from api.db.database import SessionLocal
from api.db.models import Role

# Создаем сессию
db = SessionLocal()

# Список ролей для добавления
roles = [
    {"id": 1, "role_name": "student", "role_description": "Обычный студент"},
    {"id": 2, "role_name": "admin", "role_description": "Администратор системы"},
]

try:
    for role_data in roles:
        # Проверяем, существует ли роль
        existing_role = db.query(Role).filter(Role.id == role_data["id"]).first()
        if not existing_role:
            role = Role(
                id=role_data["id"],
                role_name=role_data["role_name"],
                role_description=role_data["role_description"]
            )
            db.add(role)
    db.commit()
    print("Роли успешно добавлены!")
except Exception as e:
    print("Ошибка:", e)
    db.rollback()
finally:
    db.close()