# -*- coding: utf-8 -*-
"""
Кастомные исключения - все ошибки приложения в одном месте.
Вместо разрозненных HTTPException(...) везде.
"""
from fastapi import HTTPException, status


class APIException(HTTPException):
    """Базовый класс для всех API ошибок"""
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


# ========== 400 Bad Request ==========
class BadRequestError(APIException):
    """Неверные параметры запроса"""
    def __init__(self, detail: str):
        super().__init__(detail, status_code=status.HTTP_400_BAD_REQUEST)


class ValidationError(BadRequestError):
    """Ошибка валидации данных"""
    def __init__(self, detail: str):
        super().__init__(detail)


class InvalidCredentialsError(BadRequestError):
    """Неверные учётные данные"""
    def __init__(self):
        super().__init__("Неверный логин или пароль")


class UserAlreadyExistsError(BadRequestError):
    """Пользователь уже существует"""
    def __init__(self, field: str):
        super().__init__(f"Пользователь с таким {field} уже существует")


# ========== 401 Unauthorized ==========
class UnauthorizedError(APIException):
    """Требуется аутентификация"""
    def __init__(self, detail: str = "Не авторизован"):
        super().__init__(detail, status_code=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredError(UnauthorizedError):
    """Токен истёк"""
    def __init__(self):
        super().__init__("Токен истёк, требуется повторный вход")


class InvalidTokenError(UnauthorizedError):
    """Неверный токен"""
    def __init__(self):
        super().__init__("Неверный токен")


# ========== 403 Forbidden ==========
class ForbiddenError(APIException):
    """Нет доступа"""
    def __init__(self, detail: str = "Доступ запрещен"):
        super().__init__(detail, status_code=status.HTTP_403_FORBIDDEN)


class InsufficientPermissionsError(ForbiddenError):
    """Недостаточно прав"""
    def __init__(self):
        super().__init__("Недостаточно прав для этой операции")


# ========== 404 Not Found ==========
class NotFoundError(APIException):
    """Ресурс не найден"""
    def __init__(self, resource: str, identifier: str = ""):
        detail = f"{resource} не найден"
        if identifier:
            detail = f"{resource} с ID {identifier} не найден"
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class UserNotFoundError(NotFoundError):
    """Пользователь не найден"""
    def __init__(self, user_id: int = None):
        super().__init__("Пользователь", user_id)


class DormitoryNotFoundError(NotFoundError):
    """Общежитие не найдено"""
    def __init__(self, dorm_id: int = None):
        super().__init__("Общежитие", dorm_id)


class RoomNotFoundError(NotFoundError):
    """Комната не найдена"""
    def __init__(self, room_id: int = None):
        super().__init__("Комната", room_id)


class ProductNotFoundError(NotFoundError):
    """Товар не найден"""
    def __init__(self, product_id: int = None):
        super().__init__("Товар", product_id)


class RoleNotFoundError(NotFoundError):
    """Роль не найдена"""
    def __init__(self, role_id: int = None):
        super().__init__("Роль", role_id)


# ========== 409 Conflict ==========
class ConflictError(APIException):
    """Конфликт (например, дублирующиеся данные)"""
    def __init__(self, detail: str):
        super().__init__(detail, status_code=status.HTTP_409_CONFLICT)


# ========== 503 Service Unavailable ==========
class ServiceUnavailableError(APIException):
    """Сервис временно недоступен"""
    def __init__(self, detail: str = "Сервис временно недоступен"):
        super().__init__(detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class DatabaseUnavailableError(ServiceUnavailableError):
    """База данных временно недоступна"""
    def __init__(self):
        super().__init__("Не удалось подключиться к базе данных. Проверьте строку подключения и доступ к серверу БД.")


# ========== 500 Internal Server Error ==========
class InternalServerError(APIException):
    """Внутренняя ошибка сервера"""
    def __init__(self, detail: str = "Внутренняя ошибка сервера"):
        super().__init__(detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatabaseError(InternalServerError):
    """Ошибка БД"""
    def __init__(self):
        super().__init__("Ошибка при работе с БД")


class ExternalServiceError(InternalServerError):
    """Ошибка внешнего сервиса (Cloudinary и т.д.)"""
    def __init__(self, service_name: str):
        super().__init__(f"Ошибка при работе с {service_name}")
