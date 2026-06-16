# -*- coding: utf-8 -*-
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    user_id: int
    period_start: date
    period_end: date
    amount: float
    status: Optional[str] = "pending"
    description: Optional[str] = None
    due_date: Optional[date] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    admin_comment: Optional[str] = None


class PaymentUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    admin_comment: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    room_id: Optional[int] = None
    room_number: Optional[int] = None
    period_start: date
    period_end: date
    amount: float
    status: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    admin_comment: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int


class PaymentExportResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    total_amount: float
    paid_amount: float
    pending_amount: float
