# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaymentSummaryItemResponse(BaseModel):
    key: str
    label: str
    amount: float
    value: str


class PaymentAccountSettingsResponse(BaseModel):
    account_number: str
    recipient_name: str
    bank_name: Optional[str] = None
    payment_instructions: Optional[str] = None
    updated_by_id: Optional[int] = None
    updated_by_name: Optional[str] = None
    updated_at: Optional[datetime] = None


class PaymentAccountSettingsUpdate(BaseModel):
    account_number: str = Field(..., min_length=4, max_length=100)
    recipient_name: str = Field(..., min_length=2, max_length=200)
    bank_name: Optional[str] = Field(default=None, max_length=200)
    payment_instructions: Optional[str] = None


class PaymentInvoiceV2Response(BaseModel):
    id: int
    user_id: int
    user_name: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    room_id: Optional[int] = None
    room_number: Optional[int] = None
    title: str
    description: Optional[str] = None
    period: str
    period_start: date
    period_end: date
    amount: float
    status: str
    status_text: str
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    payment_channel: Optional[str] = None
    admin_comment: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    can_pay: bool = False


class PaymentInvoiceCreateV2(BaseModel):
    user_id: int
    period_start: date
    period_end: date
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=3)
    due_date: Optional[date] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    admin_comment: Optional[str] = None
    status: str = "pending"


class PaymentInvoiceUpdateV2(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, min_length=3)
    due_date: Optional[date] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    admin_comment: Optional[str] = None
    status: Optional[str] = None
    payment_channel: Optional[str] = None


class PaymentHistoryEntryResponse(BaseModel):
    id: str
    entry_type: str
    direction: str
    title: str
    description: Optional[str] = None
    period: str
    amount: float
    status: str
    status_text: str
    occurred_at: datetime
    payment_channel: Optional[str] = None
    related_payment_id: Optional[int] = None
    related_top_up_id: Optional[int] = None
    receipt_file_name: Optional[str] = None
    transfer_reference: Optional[str] = None


class PaymentTopUpPreviewResponse(BaseModel):
    amount: float
    transfer_reference: str
    account: PaymentAccountSettingsResponse


class PaymentTopUpCreate(BaseModel):
    amount: float = Field(..., gt=0)
    receipt_file_name: Optional[str] = Field(default=None, max_length=255)
    receipt_file_url: Optional[str] = Field(default=None, max_length=500)
    comment: Optional[str] = None


class PaymentTopUpResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    status: str
    status_text: str
    transfer_reference: str
    account_number: str
    recipient_name: str
    bank_name: Optional[str] = None
    receipt_file_name: Optional[str] = None
    receipt_file_url: Optional[str] = None
    comment: Optional[str] = None
    credited_at: Optional[datetime] = None
    created_at: datetime
    balance_after: float


class PaymentBalanceResponse(BaseModel):
    balance: float
    total_top_ups: float
    total_wallet_spent: float
    pending_amount: float
    overdue_amount: float


class PaymentChartResponse(BaseModel):
    labels: list[str]
    values: list[float]
    incoming_values: list[float]
    outgoing_values: list[float]
    net_values: list[float]


class PaymentDashboardResponse(BaseModel):
    balance: float
    summary: list[PaymentSummaryItemResponse]
    current: list[PaymentInvoiceV2Response]
    history: list[PaymentHistoryEntryResponse]
    chart: PaymentChartResponse
    top_up_account: Optional[PaymentAccountSettingsResponse] = None


class PaymentDashboardEnvelope(BaseModel):
    data: PaymentDashboardResponse


class PaymentBalanceEnvelope(BaseModel):
    data: PaymentBalanceResponse


class PaymentHistoryListResponse(BaseModel):
    items: list[PaymentHistoryEntryResponse]
    total: int


class PaymentCurrentListResponse(BaseModel):
    items: list[PaymentInvoiceV2Response]
    total: int


class PaymentInvoiceListResponse(BaseModel):
    items: list[PaymentInvoiceV2Response]
    total: int
    page: int
    page_size: int


class PaymentTopUpEnvelope(BaseModel):
    data: PaymentTopUpResponse


class PaymentPayResultResponse(BaseModel):
    message: str
    balance_after: float
    invoice: PaymentInvoiceV2Response


class PaymentPayResultEnvelope(BaseModel):
    data: PaymentPayResultResponse
