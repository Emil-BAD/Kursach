# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List
from api.core.dependencies import get_current_user, get_current_admin
from api.db.database import get_db
from api.db.models import User, Dormitory, CleanlinessHistory
from api.services.user import router as user_router
from api.services.news import router as news_router
from api.services.product import router as product_router
from api.services.auth import router as auth_router
from api.services.event import router as event_router
from api.services.event_registration import router as event_registration_router
from api.services.user_violations import router as user_violations_router

app = FastAPI()

app.include_router(user_router, tags=["users"])
app.include_router(user_violations_router, tags=["user_violations"])
app.include_router(news_router, tags=["news"])
app.include_router(event_router, tags=["event"])
app.include_router(event_registration_router, tags=["event_registration"])
app.include_router(product_router, tags=["product"])
app.include_router(auth_router, tags=["auth"])


@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "role": current_user.role.role_name
    }

@app.get("/admin-only")
def admin_only(current_user: User = Depends(get_current_admin)):
    return {"message": "Привет, администратор!"}

@app.get("/dormitories", response_model=List[dict])
def get_dormitories(db: Session = Depends(get_db)):
    dormitories = db.query(Dormitory).all()
    return [{"id": dorm.id, "name": dorm.name, "address": dorm.address} for dorm in dormitories]


@app.get("/cleanliness-history", response_model=List[dict])
def get_cleanliness_history(db: Session = Depends(get_db)):
    records = db.query(CleanlinessHistory).all()
    return [
        {
            "id": r.id,
            "room_id": r.room_id,
            "score": r.score,
            "assigned_by": r.assigned_by_user.full_name,
            "assigned_at": r.assigned_at.isoformat()
        }
        for r in records
    ]