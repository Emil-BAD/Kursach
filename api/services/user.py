# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from db.models import User, Dormitory, Room, Role
from schemas.user import PaginatedUserResponse, UserResponse
from core.dependencies import get_current_admin

router = APIRouter()

@router.get("/users", response_model=PaginatedUserResponse)
def get_users(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    skip = (page - 1) * size
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(size).all()

    user_responses = []
    for user in users:
        dormitory = db.query(Dormitory).filter(Dormitory.id == user.dormitory_id).first()
        room = db.query(Room).filter(Room.id == user.room_id).first()
        role = db.query(Role).filter(Role.id == user.role_id).first()

        user_responses.append(
            UserResponse(
                id=user.id,
                student_card=user.student_card,
                full_name=user.full_name,
                contact_number=user.contract_number,
                dormitory_id=user.dormitory_id or 0,
                dormitory_name=dormitory.name if dormitory else None,
                room_id=user.room_id or 0,
                room_number=room.room_number if room else 0,
                group_number=user.group_number,
                specialization=user.specialization,
                role_id=user.role_id,
                role_name=role.role_name if role else None,
                email=user.email,
                phone=user.phone,
                birth_date=user.birth_date,
                course=user.course,
                faculty=user.faculty,
                created_at=user.created_at,  # Предполагается, что добавим created_at в User
                points={}  # Пока пустой dict, можно расширить позже
            )
        )

    total_pages = (total + size - 1) // size

    return PaginatedUserResponse(
        items=user_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )