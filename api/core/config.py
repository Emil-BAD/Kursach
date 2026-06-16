from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv
import os
from pathlib import Path

# Загружаем переменные из локального .env проекта.
# Сначала ищем .env в корне проекта, затем fallback на api/.env.
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATHS = [
    BASE_DIR / ".env",
    BASE_DIR / "api" / ".env",
]

for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=False, encoding="utf-8")
        break

class Settings(BaseSettings):
    """Все настройки приложения из .env"""
    
    # Аутентификация
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dormitory_db")
    DATABASE_URL_DIRECT: str | None = os.getenv("DATABASE_URL_DIRECT")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "psycopg2")
    PREFER_DIRECT_DATABASE_URL: bool = False
    AUTO_CREATE_TABLES: bool = False
    ENABLE_RUNTIME_SCHEMA_PATCHES: bool = True
    AUTH_STATELESS_REFRESH_TOKENS: bool = False
    
    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    )
    
    # Cloudinary (опционально)
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str | None = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str | None = os.getenv("CLOUDINARY_API_SECRET")
    
    # Environment
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False

        return False

    @field_validator("DB_DRIVER", mode="before")
    @classmethod
    def parse_db_driver(cls, value):
        if value is None:
            return "psycopg2"

        normalized = str(value).strip().lower()
        allowed = {"psycopg2", "psycopg", "pg8000"}
        if normalized in allowed:
            return normalized

        return "psycopg2"
    
settings = Settings()
