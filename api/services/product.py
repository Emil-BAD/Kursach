# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from db.models import Product
from core.dependencies import get_current_admin

router = APIRouter()

@router.get("/products", response_model=List[dict])
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "price": float(p.price),
            "seller": p.seller.full_name,
            "status": p.status
        }
        for p in products
    ]