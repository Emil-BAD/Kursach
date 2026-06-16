# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import Dormitory, Room, ServiceRequest, ServiceRequestAttachment, ServiceRequestComment, User
from api.schemas.service_request import (
    ServiceRequestCommentCreate,
    ServiceRequestCommentResponse,
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
)

router = APIRouter(prefix="/service-requests")

ALLOWED_REQUEST_TYPES = {"repair", "complaint", "request"}
ALLOWED_REQUEST_STATUSES = {"new", "in_progress", "resolved", "rejected", "closed"}


def _is_admin(user: User) -> bool:
    return bool(user.role and user.role.role_name == "admin")


def _validate_request_type(request_type: str) -> None:
    if request_type not in ALLOWED_REQUEST_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип заявки. Допустимые значения: {sorted(ALLOWED_REQUEST_TYPES)}",
        )


def _validate_request_status(status: str) -> None:
    if status not in ALLOWED_REQUEST_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус заявки. Допустимые значения: {sorted(ALLOWED_REQUEST_STATUSES)}",
        )


def _get_user_or_404(db: Session, user_id: int, field_name: str = "Пользователь") -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"{field_name} не найден")
    return user


def _get_dormitory_or_404(db: Session, dormitory_id: int) -> Dormitory:
    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if not dormitory:
        raise HTTPException(status_code=404, detail="Общежитие не найдено")
    return dormitory


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return room


def _validate_dormitory_and_room(
    db: Session,
    dormitory_id: int | None,
    room_id: int | None,
) -> tuple[Dormitory | None, Room | None]:
    dormitory = None
    room = None

    if dormitory_id is not None:
        dormitory = _get_dormitory_or_404(db, dormitory_id)

    if room_id is not None:
        room = _get_room_or_404(db, room_id)
        if dormitory_id is not None and room.dormitory_id != dormitory_id:
            raise HTTPException(status_code=400, detail="Комната не относится к указанному общежитию")
        if dormitory is None:
            dormitory = room.dormitory

    return dormitory, room


def _get_request_or_404(db: Session, request_id: int) -> ServiceRequest:
    service_request = (
        db.query(ServiceRequest)
        .options(
            joinedload(ServiceRequest.student),
            joinedload(ServiceRequest.executor),
            joinedload(ServiceRequest.dormitory),
            joinedload(ServiceRequest.room),
            joinedload(ServiceRequest.comments).joinedload(ServiceRequestComment.author),
            joinedload(ServiceRequest.attachments).joinedload(ServiceRequestAttachment.uploaded_by),
        )
        .filter(ServiceRequest.id == request_id)
        .first()
    )
    if not service_request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return service_request


def _can_view_request(current_user: User, service_request: ServiceRequest) -> bool:
    if _is_admin(current_user):
        return True
    if service_request.student_id == current_user.id:
        return True
    if service_request.executor_id == current_user.id:
        return True
    return False


def _build_comment_response(comment: ServiceRequestComment) -> ServiceRequestCommentResponse:
    return ServiceRequestCommentResponse(
        id=comment.id,
        author_id=comment.author_id,
        author_name=comment.author.full_name if comment.author else "Unknown",
        comment=comment.comment,
        created_at=comment.created_at,
    )


def _build_request_response(service_request: ServiceRequest) -> ServiceRequestResponse:
    comments = sorted(service_request.comments, key=lambda item: item.created_at or datetime.min)
    attachments = sorted(service_request.attachments, key=lambda item: item.created_at or datetime.min)

    return ServiceRequestResponse(
        id=service_request.id,
        title=service_request.title,
        description=service_request.description,
        request_type=service_request.request_type,
        status=service_request.status,
        student_id=service_request.student_id,
        student_name=service_request.student.full_name if service_request.student else "Unknown",
        executor_id=service_request.executor_id,
        executor_name=service_request.executor.full_name if service_request.executor else None,
        dormitory_id=service_request.dormitory_id,
        dormitory_name=service_request.dormitory.name if service_request.dormitory else None,
        room_id=service_request.room_id,
        room_number=service_request.room.room_number if service_request.room else None,
        resolution_comment=service_request.resolution_comment,
        created_at=service_request.created_at,
        updated_at=service_request.updated_at,
        closed_at=service_request.closed_at,
        comments=[_build_comment_response(comment) for comment in comments],
        attachments=[
            {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "uploaded_by_id": attachment.uploaded_by_id,
                "uploaded_by_name": attachment.uploaded_by.full_name if attachment.uploaded_by else None,
                "created_at": attachment.created_at,
            }
            for attachment in attachments
        ],
    )


@router.get("", response_model=ServiceRequestListResponse)
def get_service_requests(
    request_type: str | None = None,
    status: str | None = None,
    dormitory_id: int | None = None,
    room_id: int | None = None,
    student_id: int | None = None,
    executor_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает список заявок по общежитию с фильтрами по типу, статусу, комнате, студенту и исполнителю.

    Что принимает:
    Query-параметры, например:
    {
      "request_type": "repair",
      "status": "new",
      "dormitory_id": 1
    }

    Что возвращает:
    {
      "items": [
        {
          "id": 1,
          "title": "Протекает кран",
          "request_type": "repair",
          "status": "new",
          "student_id": 5
        }
      ],
      "total": 1
    }
    """
    query = db.query(ServiceRequest).options(
        joinedload(ServiceRequest.student),
        joinedload(ServiceRequest.executor),
        joinedload(ServiceRequest.dormitory),
        joinedload(ServiceRequest.room),
        joinedload(ServiceRequest.comments).joinedload(ServiceRequestComment.author),
        joinedload(ServiceRequest.attachments).joinedload(ServiceRequestAttachment.uploaded_by),
    )

    if request_type:
        _validate_request_type(request_type)
        query = query.filter(ServiceRequest.request_type == request_type)
    if status:
        _validate_request_status(status)
        query = query.filter(ServiceRequest.status == status)
    if dormitory_id is not None:
        query = query.filter(ServiceRequest.dormitory_id == dormitory_id)
    if room_id is not None:
        query = query.filter(ServiceRequest.room_id == room_id)
    if student_id is not None:
        query = query.filter(ServiceRequest.student_id == student_id)
    if executor_id is not None:
        query = query.filter(ServiceRequest.executor_id == executor_id)

    if not _is_admin(current_user):
        query = query.filter(
            or_(
                ServiceRequest.student_id == current_user.id,
                ServiceRequest.executor_id == current_user.id,
            )
        )

    requests = query.order_by(ServiceRequest.created_at.desc()).all()
    return ServiceRequestListResponse(
        items=[_build_request_response(item) for item in requests],
        total=len(requests),
    )


@router.get("/{request_id}", response_model=ServiceRequestResponse)
def get_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает одну заявку вместе с комментариями, вложениями, исполнителем и привязкой к комнате.

    Что принимает:
    Path-параметр `request_id`, пример:
    {
      "request_id": 10
    }

    Что возвращает:
    {
      "id": 10,
      "title": "Жалоба на шум",
      "status": "in_progress",
      "comments": [],
      "attachments": []
    }
    """
    service_request = _get_request_or_404(db, request_id)
    if not _can_view_request(current_user, service_request):
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра заявки")
    return _build_request_response(service_request)


@router.post("", response_model=ServiceRequestResponse)
def create_service_request(
    request_data: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Создаёт новую заявку на ремонт, жалобу или обычный запрос с привязкой к студенту, комнате и общежитию.

    Что принимает:
    {
      "title": "Сломан свет",
      "description": "В комнате 215 не работает свет",
      "request_type": "repair",
      "dormitory_id": 1,
      "room_id": 7,
      "attachments": [
        {"file_name": "photo.jpg", "file_url": "https://example.com/photo.jpg"}
      ]
    }

    Что возвращает:
    {
      "id": 15,
      "title": "Сломан свет",
      "request_type": "repair",
      "status": "new"
    }
    """
    _validate_request_type(request_data.request_type)

    student_id = request_data.student_id or current_user.id
    if not _is_admin(current_user) and student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нельзя создать заявку от имени другого пользователя")

    if request_data.executor_id is not None and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Только администратор может назначать исполнителя")

    student = _get_user_or_404(db, student_id, "Студент")
    executor = None
    if request_data.executor_id is not None:
        executor = _get_user_or_404(db, request_data.executor_id, "Исполнитель")

    dormitory_id = request_data.dormitory_id or student.dormitory_id
    room_id = request_data.room_id or student.room_id
    _validate_dormitory_and_room(db, dormitory_id, room_id)

    service_request = ServiceRequest(
        title=request_data.title,
        description=request_data.description,
        request_type=request_data.request_type,
        status="new",
        student_id=student.id,
        executor_id=executor.id if executor else None,
        dormitory_id=dormitory_id,
        room_id=room_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(service_request)
    db.flush()

    for attachment in request_data.attachments:
        db.add(
            ServiceRequestAttachment(
                service_request_id=service_request.id,
                file_name=attachment.file_name,
                file_url=attachment.file_url,
                uploaded_by_id=current_user.id,
            )
        )

    db.commit()
    db.refresh(service_request)
    return _build_request_response(_get_request_or_404(db, service_request.id))


@router.put("/{request_id}", response_model=ServiceRequestResponse)
def update_service_request(
    request_id: int,
    request_data: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Обновляет заявку: студент может менять свои данные, исполнитель может менять статус, админ может менять всё.

    Что принимает:
    {
      "status": "in_progress",
      "executor_id": 2,
      "resolution_comment": "Передано электрику"
    }

    Что возвращает:
    {
      "id": 15,
      "status": "in_progress",
      "executor_id": 2,
      "resolution_comment": "Передано электрику"
    }
    """
    service_request = _get_request_or_404(db, request_id)
    is_admin = _is_admin(current_user)
    is_owner = service_request.student_id == current_user.id
    is_executor = service_request.executor_id == current_user.id

    if not any([is_admin, is_owner, is_executor]):
        raise HTTPException(status_code=403, detail="Недостаточно прав для изменения заявки")

    if request_data.request_type is not None:
        _validate_request_type(request_data.request_type)
    if request_data.status is not None:
        _validate_request_status(request_data.status)

    if not is_admin:
        if is_owner and any(
            value is not None
            for value in [
                request_data.status,
                request_data.executor_id,
                request_data.student_id,
                request_data.resolution_comment,
            ]
        ):
            raise HTTPException(status_code=403, detail="Студент не может менять статус, исполнителя или владельца заявки")
        if is_executor and any(
            value is not None
            for value in [
                request_data.title,
                request_data.description,
                request_data.request_type,
                request_data.dormitory_id,
                request_data.room_id,
                request_data.student_id,
                request_data.executor_id,
                request_data.attachments,
            ]
        ):
            raise HTTPException(status_code=403, detail="Исполнитель может менять только статус и комментарий решения")

    if request_data.student_id is not None:
        service_request.student_id = _get_user_or_404(db, request_data.student_id, "Студент").id
    if request_data.executor_id is not None:
        service_request.executor_id = _get_user_or_404(db, request_data.executor_id, "Исполнитель").id

    new_dormitory_id = service_request.dormitory_id if request_data.dormitory_id is None else request_data.dormitory_id
    new_room_id = service_request.room_id if request_data.room_id is None else request_data.room_id
    _validate_dormitory_and_room(db, new_dormitory_id, new_room_id)

    if request_data.title is not None:
        service_request.title = request_data.title
    if request_data.description is not None:
        service_request.description = request_data.description
    if request_data.request_type is not None:
        service_request.request_type = request_data.request_type
    if request_data.status is not None:
        service_request.status = request_data.status
    if request_data.dormitory_id is not None:
        service_request.dormitory_id = request_data.dormitory_id
    if request_data.room_id is not None:
        service_request.room_id = request_data.room_id
    if request_data.resolution_comment is not None:
        service_request.resolution_comment = request_data.resolution_comment

    if request_data.status in {"resolved", "rejected", "closed"}:
        service_request.closed_at = datetime.utcnow()
    elif request_data.status is not None:
        service_request.closed_at = None

    if request_data.attachments is not None:
        db.query(ServiceRequestAttachment).filter(
            ServiceRequestAttachment.service_request_id == service_request.id
        ).delete()
        for attachment in request_data.attachments:
            db.add(
                ServiceRequestAttachment(
                    service_request_id=service_request.id,
                    file_name=attachment.file_name,
                    file_url=attachment.file_url,
                    uploaded_by_id=current_user.id,
                )
            )

    service_request.updated_at = datetime.utcnow()
    db.commit()
    return _build_request_response(_get_request_or_404(db, service_request.id))


@router.get("/{request_id}/comments", response_model=list[ServiceRequestCommentResponse])
def get_service_request_comments(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает все комментарии по заявке.

    Что принимает:
    Path-параметр `request_id`, пример:
    {
      "request_id": 15
    }

    Что возвращает:
    [
      {
        "id": 1,
        "author_id": 2,
        "author_name": "Петр Петров",
        "comment": "Заявка принята в работу"
      }
    ]
    """
    service_request = _get_request_or_404(db, request_id)
    if not _can_view_request(current_user, service_request):
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра комментариев")
    return [_build_comment_response(comment) for comment in service_request.comments]


@router.post("/{request_id}/comments", response_model=ServiceRequestCommentResponse)
def add_service_request_comment(
    request_id: int,
    comment_data: ServiceRequestCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Добавляет комментарий к заявке от студента, исполнителя или администратора.

    Что принимает:
    {
      "comment": "Проблема всё ещё актуальна"
    }

    Что возвращает:
    {
      "id": 4,
      "author_id": 5,
      "author_name": "Иван Иванов",
      "comment": "Проблема всё ещё актуальна"
    }
    """
    service_request = _get_request_or_404(db, request_id)
    if not _can_view_request(current_user, service_request):
        raise HTTPException(status_code=403, detail="Недостаточно прав для добавления комментария")

    comment = ServiceRequestComment(
        service_request_id=service_request.id,
        author_id=current_user.id,
        comment=comment_data.comment,
    )
    db.add(comment)
    service_request.updated_at = datetime.utcnow()
    db.commit()

    comment = (
        db.query(ServiceRequestComment)
        .options(joinedload(ServiceRequestComment.author))
        .filter(ServiceRequestComment.id == comment.id)
        .first()
    )
    return _build_comment_response(comment)
