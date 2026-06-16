# -*- coding: utf-8 -*-
"""API v2 - платежи, внутренний баланс и пополнения."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import User
from api.schemas.payment_v2 import (
    PaymentAccountSettingsResponse,
    PaymentAccountSettingsUpdate,
    PaymentBalanceEnvelope,
    PaymentCurrentListResponse,
    PaymentDashboardEnvelope,
    PaymentHistoryListResponse,
    PaymentInvoiceCreateV2,
    PaymentInvoiceListResponse,
    PaymentInvoiceUpdateV2,
    PaymentInvoiceV2Response,
    PaymentPayResultEnvelope,
    PaymentTopUpCreate,
    PaymentTopUpEnvelope,
    PaymentTopUpPreviewResponse,
)
from api.services.payment_v2_service import PaymentV2Service


router = APIRouter(prefix="/api/v2/payments", tags=["payments-v2"])


@router.get("/dashboard", response_model=PaymentDashboardEnvelope)
def get_payments_dashboard(
    status: str | None = Query(default=None, description="Фильтр по статусу счета или истории"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    history_limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return {
        "data": service.get_dashboard(
            current_user,
            status=status,
            date_from=date_from,
            date_to=date_to,
            history_limit=history_limit,
        )
    }


@router.get("/balance", response_model=PaymentBalanceEnvelope)
def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return {"data": service.get_balance(current_user)}


@router.get("/current", response_model=PaymentCurrentListResponse)
def list_current_invoices(
    status: str | None = Query(default=None, description="pending, overdue, partially_paid"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.list_current(current_user, status=status)


@router.get("/history", response_model=PaymentHistoryListResponse)
def list_payment_history(
    direction: str | None = Query(default=None, description="incoming или outgoing"),
    status: str | None = Query(default=None, description="paid / confirmed / rejected / submitted"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.list_history(
        current_user,
        direction=direction,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/account", response_model=PaymentAccountSettingsResponse)
def get_top_up_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.get_account_settings(current_user)


@router.put("/account", response_model=PaymentAccountSettingsResponse)
def update_top_up_account(
    data: PaymentAccountSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.update_account_settings(current_user, data)


@router.get("/top-up-preview", response_model=PaymentTopUpPreviewResponse)
def preview_top_up(
    amount: float = Query(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.preview_top_up(current_user, amount)


@router.post("/top-ups", response_model=PaymentTopUpEnvelope)
def create_top_up(
    data: PaymentTopUpCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return {"data": service.create_top_up(current_user, data)}


@router.post("/invoices/{payment_id}/pay", response_model=PaymentPayResultEnvelope)
def pay_invoice(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return {"data": service.pay_invoice(current_user, payment_id)}


@router.get("/invoices", response_model=PaymentInvoiceListResponse)
def list_invoices_for_manager(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    dormitory_id: int | None = Query(default=None),
    room_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.list_invoices_for_manager(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        user_id=user_id,
        dormitory_id=dormitory_id,
        room_id=room_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/invoices", response_model=PaymentInvoiceV2Response)
def create_invoice(
    data: PaymentInvoiceCreateV2,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.create_invoice(current_user, data)


@router.patch("/invoices/{payment_id}", response_model=PaymentInvoiceV2Response)
def update_invoice(
    payment_id: int,
    data: PaymentInvoiceUpdateV2,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentV2Service(db)
    return service.update_invoice(current_user, payment_id, data)
