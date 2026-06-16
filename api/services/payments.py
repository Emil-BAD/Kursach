# -*- coding: utf-8 -*-
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_admin, get_current_user
from api.db.database import get_db
from api.db.models import Dormitory, Payment, Room, User
from api.schemas.payment import PaymentCreate, PaymentExportResponse, PaymentListResponse, PaymentResponse, PaymentUpdate

router = APIRouter(prefix="/payments")

ALLOWED_PAYMENT_STATUSES = {"pending", "paid", "overdue", "cancelled", "partially_paid"}


def _build_payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        user_id=payment.user_id,
        user_name=payment.user.full_name if payment.user else "Unknown",
        dormitory_id=payment.dormitory_id,
        dormitory_name=payment.dormitory.name if payment.dormitory else None,
        room_id=payment.room_id,
        room_number=payment.room.room_number if payment.room else None,
        period_start=payment.period_start,
        period_end=payment.period_end,
        amount=float(payment.amount),
        status=payment.status,
        description=payment.description,
        due_date=payment.due_date,
        paid_at=payment.paid_at,
        admin_comment=payment.admin_comment,
        created_by_id=payment.created_by_id,
        created_by_name=payment.created_by.full_name if payment.created_by else None,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


def _get_payment_or_404(db: Session, payment_id: int) -> Payment:
    payment = (
        db.query(Payment)
        .options(
            joinedload(Payment.user),
            joinedload(Payment.dormitory),
            joinedload(Payment.room),
            joinedload(Payment.created_by),
        )
        .filter(Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Начисление не найдено")
    return payment


def _validate_payment_status(status: str) -> None:
    if status not in ALLOWED_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус оплаты. Допустимые значения: {sorted(ALLOWED_PAYMENT_STATUSES)}",
        )


def _validate_payment_data(
    db: Session,
    user_id: int,
    dormitory_id: int | None,
    room_id: int | None,
    period_start,
    period_end,
) -> tuple[User, Dormitory | None, Room | None]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if period_end < period_start:
        raise HTTPException(status_code=400, detail="Дата окончания периода не может быть раньше даты начала")

    dormitory = None
    room = None

    if dormitory_id is not None:
        dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            raise HTTPException(status_code=404, detail="Общежитие не найдено")

    if room_id is not None:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        if dormitory_id is not None and room.dormitory_id != dormitory_id:
            raise HTTPException(status_code=400, detail="Комната не относится к указанному общежитию")
        if dormitory is None:
            dormitory = room.dormitory

    return user, dormitory, room


@router.get("/export", response_model=PaymentExportResponse)
def export_payments_by_period(
    date_from: date,
    date_to: date,
    status: str | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Возвращает выгрузку начислений за период для админки в виде JSON со сводными суммами.

    Что принимает:
    Query-параметры, например:
    {
      "date_from": "2026-04-01",
      "date_to": "2026-04-30",
      "status": "pending"
    }

    Что возвращает:
    {
      "items": [],
      "total": 0,
      "total_amount": 0,
      "paid_amount": 0,
      "pending_amount": 0
    }
    """
    query = db.query(Payment).options(
        joinedload(Payment.user),
        joinedload(Payment.dormitory),
        joinedload(Payment.room),
        joinedload(Payment.created_by),
    )

    if date_to < date_from:
        raise HTTPException(status_code=400, detail="Дата окончания периода не может быть раньше даты начала")

    query = query.filter(Payment.period_start >= date_from, Payment.period_end <= date_to)
    if status:
        _validate_payment_status(status)
        query = query.filter(Payment.status == status)
    if user_id is not None:
        query = query.filter(Payment.user_id == user_id)

    payments = query.order_by(Payment.period_start.desc(), Payment.id.desc()).all()
    items = [_build_payment_response(item) for item in payments]
    total_amount = round(sum(item.amount for item in items), 2)
    paid_amount = round(sum(item.amount for item in items if item.status == "paid"), 2)
    pending_amount = round(sum(item.amount for item in items if item.status != "paid"), 2)

    return PaymentExportResponse(
        items=items,
        total=len(items),
        total_amount=total_amount,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
    )


@router.get("", response_model=PaymentListResponse)
def get_payments(
    status: str | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает начисления по оплатам. Администратор видит всё, студент — только свои записи.

    Что принимает:
    Query-параметры, например:
    {
      "status": "pending",
      "user_id": 5
    }

    Что возвращает:
    {
      "items": [
        {
          "id": 8,
          "user_id": 5,
          "amount": 3500.0,
          "status": "pending"
        }
      ],
      "total": 1
    }
    """
    query = db.query(Payment).options(
        joinedload(Payment.user),
        joinedload(Payment.dormitory),
        joinedload(Payment.room),
        joinedload(Payment.created_by),
    )

    is_admin = bool(current_user.role and current_user.role.role_name == "admin")
    if not is_admin:
        query = query.filter(Payment.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(Payment.user_id == user_id)

    if status:
        _validate_payment_status(status)
        query = query.filter(Payment.status == status)

    payments = query.order_by(Payment.period_start.desc(), Payment.id.desc()).all()
    return PaymentListResponse(
        items=[_build_payment_response(item) for item in payments],
        total=len(payments),
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Что делает:
    Возвращает одно начисление по ID.

    Что принимает:
    Path-параметр `payment_id`, пример:
    {
      "payment_id": 8
    }

    Что возвращает:
    {
      "id": 8,
      "amount": 3500.0,
      "status": "pending",
      "user_id": 5
    }
    """
    payment = _get_payment_or_404(db, payment_id)
    is_admin = bool(current_user.role and current_user.role.role_name == "admin")
    if not is_admin and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра начисления")
    return _build_payment_response(payment)


@router.post("", response_model=PaymentResponse)
def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Создаёт начисление за период проживания или дополнительную оплату.

    Что принимает:
    {
      "user_id": 5,
      "period_start": "2026-04-01",
      "period_end": "2026-04-30",
      "amount": 3500,
      "status": "pending",
      "description": "Оплата проживания за апрель",
      "due_date": "2026-05-10"
    }

    Что возвращает:
    {
      "id": 8,
      "user_id": 5,
      "amount": 3500.0,
      "status": "pending"
    }
    """
    _validate_payment_status(payment_data.status or "pending")
    user, dormitory, room = _validate_payment_data(
        db,
        payment_data.user_id,
        payment_data.dormitory_id,
        payment_data.room_id,
        payment_data.period_start,
        payment_data.period_end,
    )

    payment = Payment(
        user_id=user.id,
        dormitory_id=dormitory.id if dormitory else None,
        room_id=room.id if room else None,
        period_start=payment_data.period_start,
        period_end=payment_data.period_end,
        amount=payment_data.amount,
        status=payment_data.status or "pending",
        description=payment_data.description,
        due_date=payment_data.due_date,
        admin_comment=payment_data.admin_comment,
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        paid_at=datetime.utcnow() if payment_data.status == "paid" else None,
    )
    db.add(payment)
    db.commit()
    return _build_payment_response(_get_payment_or_404(db, payment.id))


@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Что делает:
    Обновляет начисление и позволяет администратору корректировать сумму, статус, период и комментарий.

    Что принимает:
    {
      "amount": 3200,
      "status": "paid",
      "admin_comment": "Корректировка после перерасчёта"
    }

    Что возвращает:
    {
      "id": 8,
      "amount": 3200.0,
      "status": "paid",
      "admin_comment": "Корректировка после перерасчёта"
    }
    """
    payment = _get_payment_or_404(db, payment_id)

    new_period_start = payment.period_start if payment_data.period_start is None else payment_data.period_start
    new_period_end = payment.period_end if payment_data.period_end is None else payment_data.period_end
    new_user_id = payment.user_id
    new_dormitory_id = payment.dormitory_id if payment_data.dormitory_id is None else payment_data.dormitory_id
    new_room_id = payment.room_id if payment_data.room_id is None else payment_data.room_id

    _validate_payment_data(db, new_user_id, new_dormitory_id, new_room_id, new_period_start, new_period_end)

    if payment_data.status is not None:
        _validate_payment_status(payment_data.status)
        payment.status = payment_data.status

    if payment_data.period_start is not None:
        payment.period_start = payment_data.period_start
    if payment_data.period_end is not None:
        payment.period_end = payment_data.period_end
    if payment_data.amount is not None:
        payment.amount = payment_data.amount
    if payment_data.description is not None:
        payment.description = payment_data.description
    if payment_data.due_date is not None:
        payment.due_date = payment_data.due_date
    if payment_data.dormitory_id is not None:
        payment.dormitory_id = payment_data.dormitory_id
    if payment_data.room_id is not None:
        payment.room_id = payment_data.room_id
    if payment_data.admin_comment is not None:
        payment.admin_comment = payment_data.admin_comment

    if payment_data.paid_at is not None:
        payment.paid_at = payment_data.paid_at
    elif payment.status == "paid" and payment.paid_at is None:
        payment.paid_at = datetime.utcnow()
    elif payment.status != "paid":
        payment.paid_at = None

    payment.updated_at = datetime.utcnow()
    db.commit()
    return _build_payment_response(_get_payment_or_404(db, payment.id))
