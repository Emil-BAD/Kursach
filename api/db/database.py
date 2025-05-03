from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.core.config import settings
from api.db.models import Base

# Создаем движок для подключения к базе
engine = create_engine(settings.DATABASE_URL, echo=True)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем все таблицы в базе (если они еще не созданы)
Base.metadata.create_all(bind=engine)

# Зависимость для FastAPI: предоставляет сессию для каждого запроса
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()