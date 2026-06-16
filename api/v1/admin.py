from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import User
from api.schemas.payment_v2 import (
    PaymentAccountSettingsResponse,
    PaymentAccountSettingsUpdate,
    PaymentInvoiceCreateV2,
    PaymentInvoiceListResponse,
    PaymentInvoiceUpdateV2,
    PaymentInvoiceV2Response,
)
from api.schemas.product import ProductModeration
from api.schemas.service_request import ServiceRequestCommentCreate, ServiceRequestUpdate
from api.services.admin_bootstrap_service import AdminBootstrapService
from api.services.admin_dashboard_service import AdminDashboardService
from api.services.admin_module_service import AdminModuleService
from api.services.admin_search_service import AdminSearchService


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/bootstrap", response_model=dict)
def get_admin_bootstrap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminBootstrapService(db).get_bootstrap(current_user)


@router.get("/dashboard", response_model=dict)
def get_admin_dashboard(
    dormitory_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminDashboardService(db).get_dashboard(
        current_user,
        dormitory_id=dormitory_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/activity-feed", response_model=dict)
def get_admin_activity_feed(
    dormitory_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminDashboardService(db).get_activity_feed(
        current_user,
        dormitory_id=dormitory_id,
        limit=limit,
    )


@router.get("/search", response_model=dict)
def search_admin_entities(
    q: str = Query(..., min_length=1),
    types: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed_types = [item.strip() for item in types.split(",")] if types else None
    return AdminSearchService(db).search(
        current_user,
        query=q,
        types=parsed_types,
        limit=limit,
    )


@router.get("/users", response_model=dict)
def list_admin_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    dormitory_id: int | None = Query(default=None),
    room_id: int | None = Query(default=None),
    role_name: str | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_users(
        current_user,
        page=page,
        page_size=page_size,
        dormitory_id=dormitory_id,
        room_id=room_id,
        role_name=role_name,
        q=q,
    )


@router.get("/users/{user_id}", response_model=dict)
def get_admin_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).get_user_detail(current_user, user_id)


@router.get("/dormitories", response_model=dict)
def list_admin_dormitories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_dormitories(current_user)


@router.get("/rooms", response_model=dict)
def list_admin_rooms(
    dormitory_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_rooms(
        current_user,
        dormitory_id=dormitory_id,
        q=q,
    )


@router.get("/residence/history", response_model=dict)
def list_admin_residence_history(
    user_id: int | None = Query(default=None),
    dormitory_id: int | None = Query(default=None),
    room_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_residence_history(
        current_user,
        user_id=user_id,
        dormitory_id=dormitory_id,
        room_id=room_id,
        page=page,
        page_size=page_size,
    )


@router.get("/service-requests", response_model=dict)
def list_admin_service_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    request_type: str | None = Query(default=None),
    dormitory_id: int | None = Query(default=None),
    room_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    executor_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_service_requests(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        request_type=request_type,
        dormitory_id=dormitory_id,
        room_id=room_id,
        student_id=student_id,
        executor_id=executor_id,
        q=q,
    )


@router.get("/service-requests/{request_id}", response_model=dict)
def get_admin_service_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).get_service_request_detail(current_user, request_id)


@router.patch("/service-requests/{request_id}", response_model=dict)
def update_admin_service_request(
    request_id: int,
    data: ServiceRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).update_service_request(current_user, request_id, data)


@router.post("/service-requests/{request_id}/assign", response_model=dict)
def assign_admin_service_request(
    request_id: int,
    executor_id: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).assign_service_request(current_user, request_id, executor_id)


@router.post("/service-requests/{request_id}/comment", response_model=dict)
def add_admin_service_request_comment(
    request_id: int,
    data: ServiceRequestCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).add_service_request_comment(current_user, request_id, data)


@router.post("/service-requests/{request_id}/close", response_model=dict)
def close_admin_service_request(
    request_id: int,
    resolution_comment: str | None = Body(default=None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).close_service_request(
        current_user,
        request_id,
        resolution_comment=resolution_comment,
        rejected=False,
    )


@router.post("/service-requests/{request_id}/reject", response_model=dict)
def reject_admin_service_request(
    request_id: int,
    resolution_comment: str | None = Body(default=None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).close_service_request(
        current_user,
        request_id,
        resolution_comment=resolution_comment,
        rejected=True,
    )


@router.get("/payments/summary", response_model=dict)
def get_admin_payments_summary(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).get_payments_summary(current_user, dormitory_id=dormitory_id)


@router.get("/payments/invoices", response_model=PaymentInvoiceListResponse)
def list_admin_payment_invoices(
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
    service = AdminModuleService(db)
    scoped_dormitory_id = service.permissions.scoped_dormitory_id(current_user, dormitory_id)
    return service.payment_service.list_invoices_for_manager(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        user_id=user_id,
        dormitory_id=scoped_dormitory_id,
        room_id=room_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/payments/invoices", response_model=PaymentInvoiceV2Response)
def create_admin_payment_invoice(
    data: PaymentInvoiceCreateV2,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AdminModuleService(db)
    service.ensure_payment_payload_in_scope(
        current_user,
        user_id=data.user_id,
        dormitory_id=data.dormitory_id,
        room_id=data.room_id,
    )
    return service.payment_service.create_invoice(current_user, data)


@router.patch("/payments/invoices/{payment_id}", response_model=PaymentInvoiceV2Response)
def update_admin_payment_invoice(
    payment_id: int,
    data: PaymentInvoiceUpdateV2,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AdminModuleService(db)
    service.ensure_payment_record_in_scope(current_user, payment_id)
    return service.payment_service.update_invoice(current_user, payment_id, data)


@router.get("/payments/top-ups", response_model=dict)
def list_admin_payment_top_ups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_payment_top_ups(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        user_id=user_id,
    )


@router.patch("/payments/top-ups/{top_up_id}", response_model=dict)
def review_admin_payment_top_up(
    top_up_id: int,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).review_payment_top_up(
        current_user,
        top_up_id,
        status=str(payload.get("status") or ""),
        comment=payload.get("comment"),
    )


@router.get("/payments/account", response_model=PaymentAccountSettingsResponse)
def get_admin_payment_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).payment_service.get_account_settings(current_user)


@router.put("/payments/account", response_model=PaymentAccountSettingsResponse)
def update_admin_payment_account(
    data: PaymentAccountSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).payment_service.update_account_settings(current_user, data)


@router.get("/market/products", response_model=dict)
def list_admin_market_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_market_products(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        category_id=category_id,
        q=q,
    )


@router.patch("/market/products/{product_id}/moderate", response_model=dict)
def moderate_admin_market_product(
    product_id: int,
    moderation: ProductModeration,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).moderate_market_product(current_user, product_id, moderation)


@router.get("/market/rentals", response_model=dict)
def list_admin_market_rentals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    listing_status: str | None = Query(default=None),
    availability_status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_market_rentals(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        listing_status=listing_status,
        availability_status=availability_status,
        q=q,
    )


@router.patch("/market/rentals/{listing_id}/moderate", response_model=dict)
def moderate_admin_market_rental(
    listing_id: int,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).moderate_market_rental(
        current_user,
        listing_id,
        status=payload.get("status"),
        listing_status=payload.get("listing_status"),
        availability_status=payload.get("availability_status"),
    )


@router.get("/market/bookings", response_model=dict)
def list_admin_market_bookings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).list_market_bookings(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get("/reports/occupancy", response_model=dict)
def get_admin_report_occupancy(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_occupancy(current_user, dormitory_id=dormitory_id)


@router.get("/reports/discipline", response_model=dict)
def get_admin_report_discipline(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_discipline(current_user, dormitory_id=dormitory_id)


@router.get("/reports/payments", response_model=dict)
def get_admin_report_payments(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_payments(current_user, dormitory_id=dormitory_id)


@router.get("/reports/service-requests", response_model=dict)
def get_admin_report_service_requests(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_service_requests(current_user, dormitory_id=dormitory_id)


@router.get("/reports/market", response_model=dict)
def get_admin_report_market(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_market(current_user, dormitory_id=dormitory_id)


@router.get("/reports/calendar", response_model=dict)
def get_admin_report_calendar(
    dormitory_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AdminModuleService(db).report_calendar(current_user, dormitory_id=dormitory_id)
