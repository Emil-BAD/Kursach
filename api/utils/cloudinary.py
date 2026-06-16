# -*- coding: utf-8 -*-
"""Настройка Cloudinary из .env — ключи не храним в коде."""
try:
    import cloudinary
    import cloudinary.uploader as cloudinary_uploader
except ImportError:  # pragma: no cover - зависит от окружения запуска
    cloudinary = None
    cloudinary_uploader = None

from api.core.config import settings

_configured = False


def ensure_cloudinary_configured() -> bool:
    """
    Подключает Cloudinary один раз, если заданы все три переменные окружения.
    Возвращает True, если можно загружать файлы; False — если интеграция не настроена.
    """
    global _configured
    if _configured:
        return True
    if cloudinary is None:
        return False
    name = settings.CLOUDINARY_CLOUD_NAME
    key = settings.CLOUDINARY_API_KEY
    secret = settings.CLOUDINARY_API_SECRET
    if not name or not key or not secret:
        return False
    cloudinary.config(cloud_name=name, api_key=key, api_secret=secret)
    _configured = True
    return True


def get_cloudinary_uploader():
    """Возвращает модуль uploader, если библиотека Cloudinary установлена."""
    return cloudinary_uploader
