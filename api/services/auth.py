from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.db.models import User, Role, Dormitory, Room, RefreshToken
from api.schemas.user import UserRegister
from api.core.auth import create_access_token, create_refresh_token, verify_password, get_password_hash
from api.core.dependencies import get_current_user
from api.core.config import settings
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.student_card == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный student_card или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(user.id)}, expires_delta=refresh_token_expires)

    refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + refresh_token_expires
    )
    db.add(refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/auth/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Неверный refresh токен")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh токен истёк")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Неверный refresh токен")

    # Проверяем, есть ли refresh token в базе и не истёк ли он
    stored_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh токен недействителен")

    # Создаём новый access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user_id)}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/auth/invalidate")
def invalidate_tokens(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    # Удаляем все refresh токены пользователя
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()
    return {"message": "Все токены аннулированы"}

@router.post("/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Проверяем, существует ли пользователь с таким student_card
    existing_user = db.query(User).filter(User.student_card == user_data.student_card).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким студенческим билетом уже существует")

    # Убираем проверку по email, так как авторизация по student_card
    # (email остаётся опциональным полем для информации)

    # Хэшируем пароль
    hashed_password = get_password_hash(user_data.password)

    # Преобразуем birth_date из строки в date, если он указан
    birth_date = None
    if user_data.birth_date:
        try:
            birth_date = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты рождения, ожидается YYYY-MM-DD")

    # Создаём нового пользователя
    new_user = User(
        student_card=user_data.student_card,
        password=hashed_password,
        full_name=user_data.full_name,
        contact_number=user_data.contract_number,
        dormitory_id=user_data.dormitory_id,
        room_id=user_data.room_id,
        group_number=user_data.group_number,
        specialization=user_data.specialization,
        role_id=user_data.role_id,
        email=user_data.email,
        phone=user_data.phone,
        birth_date=birth_date,
        course=user_data.course,
        faculty=user_data.faculty,
        created_at=datetime.utcnow(),
        points={}  # Инициализируем пустой словарь для points
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Генерируем токены для нового пользователя
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(data={"sub": str(new_user.id)}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)}, expires_delta=refresh_token_expires)

    # Сохраняем refresh token в базе
    refresh = RefreshToken(
        user_id=new_user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + refresh_token_expires
    )
    db.add(refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }