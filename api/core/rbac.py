# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control) - централизованная система ролей и прав.
Все константы ролей в одном месте, без магических чисел в коде.
"""
from enum import Enum
from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db.models import User
from api.core.dependencies import get_current_user


class Role(str, Enum):
    """Роли в системе"""
    STUDENT = "student"
    ADMIN = "admin"
    COMMANDANT = "commandant"  # Комендант общежития
    MODERATOR = "moderator"


# Маппинг: роль → role.role_name из БД
ROLE_MAPPING = {
    Role.STUDENT: "student",
    Role.ADMIN: "admin",
    Role.COMMANDANT: "commandant",
    Role.MODERATOR: "moderator",
}


class Permission(str, Enum):
    """Права в системе"""
    # Управление пользователями
    MANAGE_USERS = "manage_users"  # Админ
    VIEW_ALL_USERS = "view_all_users"  # Админ, командант
    
    # Управление продуктами
    MODERATE_PRODUCTS = "moderate_products"  # Админ, модератор
    
    # Управление нарушениями
    CREATE_VIOLATION = "create_violation"  # Админ, командант
    VIEW_VIOLATIONS = "view_violations"  # Админ, командант, студент (свои)
    
    # Просмотр отчётов
    VIEW_REPORTS = "view_reports"  # Админ, командант
    
    # Управление заявками
    MANAGE_TICKETS = "manage_tickets"  # Админ, командант


# Матрица прав: роль → список прав
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.ADMIN: [
        Permission.MANAGE_USERS,
        Permission.VIEW_ALL_USERS,
        Permission.MODERATE_PRODUCTS,
        Permission.CREATE_VIOLATION,
        Permission.VIEW_VIOLATIONS,
        Permission.VIEW_REPORTS,
        Permission.MANAGE_TICKETS,
    ],
    Role.COMMANDANT: [
        Permission.VIEW_ALL_USERS,
        Permission.CREATE_VIOLATION,
        Permission.VIEW_VIOLATIONS,
        Permission.VIEW_REPORTS,
        Permission.MANAGE_TICKETS,
    ],
    Role.MODERATOR: [
        Permission.MODERATE_PRODUCTS,
    ],
    Role.STUDENT: [
        Permission.VIEW_VIOLATIONS,  # Только свои нарушения
    ],
}


def require_role(*allowed_roles: Role):
    """
    Проверить что текущий пользователь имеет одну из указанных ролей.
    
    Использование:
        @router.get("/admin-only")
        async def admin_only(user = Depends(require_role(Role.ADMIN))):
            ...
    """
    async def verify_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = current_user.role.role_name
        
        # Проверяем совпадение с одной из разрешённых ролей
        allowed_role_names = [ROLE_MAPPING[role] for role in allowed_roles]
        
        if user_role not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется одна из ролей: {', '.join(allowed_role_names)}"
            )
        return current_user
    
    return verify_role


def require_permission(permission: Permission):
    """
    Проверить что текущий пользователь имеет указанное право.
    
    Использование:
        @router.get("/moderate")
        async def moderate_products(user = Depends(require_permission(Permission.MODERATE_PRODUCTS))):
            ...
    """
    async def verify_permission(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = Role(current_user.role.role_name)
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав для этой операции"
            )
        return current_user
    
    return verify_permission


def has_permission(user: User, permission: Permission) -> bool:
    """Проверить наличие права без исключения (для условной логики)"""
    user_role = Role(user.role.role_name)
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    return permission in user_permissions


def has_role(user: User, *roles: Role) -> bool:
    """Проверить роль без исключения (для условной логики)"""
    user_role_name = user.role.role_name
    allowed_role_names = [ROLE_MAPPING[role] for role in roles]
    return user_role_name in allowed_role_names
