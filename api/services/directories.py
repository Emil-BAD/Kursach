# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import ActivityType, User, ViolationType
from api.schemas.directory import (
    ActivityTypeCreate,
    ActivityTypeDirectoryResponse,
    ActivityTypeUpdate,
    ViolationTypeCreate,
    ViolationTypeDirectoryResponse,
    ViolationTypeUpdate,
)

router = APIRouter(prefix="/directories")


def _set_cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "private, max-age=300"


@router.get("/violation-types", response_model=list[ViolationTypeDirectoryResponse])
def get_violation_types_directory(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает справочник типов нарушений. Для клиента добавлен простой кэш-заголовок.

    Что принимает:
    Пустой запрос без тела.

    Что возвращает:
    [
      {
        "id": 1,
        "name": "Курение",
        "description": "Курение в комнате",
        "default_penalty_points": 10
      }
    ]
    """
    _set_cache_headers(response)
    items = db.query(ViolationType).order_by(ViolationType.name).all()
    return items


@router.post("/violation-types", response_model=ViolationTypeDirectoryResponse)
def create_violation_type_directory(
    data: ViolationTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Создаёт новый тип нарушения для админки.

    Что принимает:
    {
      "name": "Порча имущества",
      "description": "Повреждение мебели или техники",
      "default_penalty_points": 15
    }

    Что возвращает:
    {
      "id": 3,
      "name": "Порча имущества",
      "default_penalty_points": 15
    }
    """
    if db.query(ViolationType).filter(ViolationType.name == data.name).first():
        raise HTTPException(status_code=400, detail="Тип нарушения с таким названием уже существует")

    violation_type = ViolationType(
        name=data.name,
        description=data.description,
        default_penalty_points=data.default_penalty_points,
    )
    db.add(violation_type)
    db.commit()
    db.refresh(violation_type)
    return violation_type


@router.put("/violation-types/{violation_type_id}", response_model=ViolationTypeDirectoryResponse)
def update_violation_type_directory(
    violation_type_id: int,
    data: ViolationTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Обновляет тип нарушения для админки.

    Что принимает:
    {
      "description": "Обновлённое описание",
      "default_penalty_points": 12
    }

    Что возвращает:
    {
      "id": 3,
      "name": "Порча имущества",
      "default_penalty_points": 12
    }
    """
    violation_type = db.query(ViolationType).filter(ViolationType.id == violation_type_id).first()
    if not violation_type:
        raise HTTPException(status_code=404, detail="Тип нарушения не найден")

    if data.name is not None:
        duplicate = (
            db.query(ViolationType)
            .filter(ViolationType.name == data.name, ViolationType.id != violation_type_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Тип нарушения с таким названием уже существует")
        violation_type.name = data.name
    if data.description is not None:
        violation_type.description = data.description
    if data.default_penalty_points is not None:
        violation_type.default_penalty_points = data.default_penalty_points

    db.commit()
    db.refresh(violation_type)
    return violation_type


@router.delete("/violation-types/{violation_type_id}", response_model=dict)
def delete_violation_type_directory(
    violation_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Удаляет тип нарушения из справочника.

    Что принимает:
    Path-параметр `violation_type_id`, пример:
    {
      "violation_type_id": 3
    }

    Что возвращает:
    {
      "message": "Тип нарушения удалён",
      "violation_type_id": 3
    }
    """
    violation_type = db.query(ViolationType).filter(ViolationType.id == violation_type_id).first()
    if not violation_type:
        raise HTTPException(status_code=404, detail="Тип нарушения не найден")

    db.delete(violation_type)
    db.commit()
    return {"message": "Тип нарушения удалён", "violation_type_id": violation_type_id}


@router.get("/activity-types", response_model=list[ActivityTypeDirectoryResponse])
def get_activity_types_directory(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает справочник типов активностей. Для клиента добавлен простой кэш-заголовок.

    Что принимает:
    Пустой запрос без тела.

    Что возвращает:
    [
      {
        "id": 1,
        "activity_name": "Субботник",
        "description": "Участие в уборке"
      }
    ]
    """
    _set_cache_headers(response)
    items = db.query(ActivityType).order_by(ActivityType.activity_name).all()
    return items


@router.post("/activity-types", response_model=ActivityTypeDirectoryResponse)
def create_activity_type_directory(
    data: ActivityTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Создаёт новый тип активности для админки.

    Что принимает:
    {
      "activity_name": "Волонтёрство",
      "description": "Участие в волонтёрской активности"
    }

    Что возвращает:
    {
      "id": 4,
      "activity_name": "Волонтёрство",
      "description": "Участие в волонтёрской активности"
    }
    """
    if db.query(ActivityType).filter(ActivityType.activity_name == data.activity_name).first():
        raise HTTPException(status_code=400, detail="Тип активности с таким названием уже существует")

    activity_type = ActivityType(
        activity_name=data.activity_name,
        description=data.description,
    )
    db.add(activity_type)
    db.commit()
    db.refresh(activity_type)
    return activity_type


@router.put("/activity-types/{activity_type_id}", response_model=ActivityTypeDirectoryResponse)
def update_activity_type_directory(
    activity_type_id: int,
    data: ActivityTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Обновляет тип активности для админки.

    Что принимает:
    {
      "activity_name": "Соревнование",
      "description": "Участие в спортивном мероприятии"
    }

    Что возвращает:
    {
      "id": 4,
      "activity_name": "Соревнование",
      "description": "Участие в спортивном мероприятии"
    }
    """
    activity_type = db.query(ActivityType).filter(ActivityType.id == activity_type_id).first()
    if not activity_type:
        raise HTTPException(status_code=404, detail="Тип активности не найден")

    if data.activity_name is not None:
        duplicate = (
            db.query(ActivityType)
            .filter(ActivityType.activity_name == data.activity_name, ActivityType.id != activity_type_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Тип активности с таким названием уже существует")
        activity_type.activity_name = data.activity_name
    if data.description is not None:
        activity_type.description = data.description

    db.commit()
    db.refresh(activity_type)
    return activity_type


@router.delete("/activity-types/{activity_type_id}", response_model=dict)
def delete_activity_type_directory(
    activity_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Удаляет тип активности из справочника.

    Что принимает:
    Path-параметр `activity_type_id`, пример:
    {
      "activity_type_id": 4
    }

    Что возвращает:
    {
      "message": "Тип активности удалён",
      "activity_type_id": 4
    }
    """
    activity_type = db.query(ActivityType).filter(ActivityType.id == activity_type_id).first()
    if not activity_type:
        raise HTTPException(status_code=404, detail="Тип активности не найден")

    db.delete(activity_type)
    db.commit()
    return {"message": "Тип активности удалён", "activity_type_id": activity_type_id}
