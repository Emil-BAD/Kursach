# api/services/category.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.db.models import Category
from api.schemas.category import CategoriesResponse
from api.core.dependencies import get_current_user
from api.db.models import User

router = APIRouter(prefix="/categories")

@router.get("", response_model=CategoriesResponse)
def get_categories(entity_type: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Category)
    if entity_type:
        query = query.filter(Category.entity_type == entity_type)
    categories = query.all()
    return CategoriesResponse(items=categories)