# -*- coding: utf-8 -*-
"""Репозиторий для работы с начислениями по платежам."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.db.models import Payment
from api.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Payment)

    def _base_query(self):
        return self.db.query(Payment).options(
            joinedload(Payment.user),
            joinedload(Payment.dormitory),
            joinedload(Payment.room),
            joinedload(Payment.created_by),
        )

    def get_with_relations(self, payment_id: int) -> Payment | None:
        return self._base_query().filter(Payment.id == payment_id).first()

    def list_current_for_user(
        self,
        user_id: int,
        statuses: Iterable[str] | None = None,
    ) -> list[Payment]:
        query = self._base_query().filter(Payment.user_id == user_id)
        if statuses:
            query = query.filter(Payment.status.in_(list(statuses)))
        return query.order_by(Payment.due_date.asc().nullslast(), Payment.id.desc()).all()

    def list_paid_for_user(
        self,
        user_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Payment]:
        query = self._base_query().filter(
            Payment.user_id == user_id,
            Payment.status == "paid",
            Payment.paid_at.isnot(None),
        )
        if date_from is not None:
            query = query.filter(func.date(Payment.paid_at) >= date_from)
        if date_to is not None:
            query = query.filter(func.date(Payment.paid_at) <= date_to)
        return query.order_by(Payment.paid_at.desc(), Payment.id.desc()).all()

    def list_for_admin(
        self,
        *,
        user_id: int | None = None,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Payment]:
        query = self._base_query()
        if user_id is not None:
            query = query.filter(Payment.user_id == user_id)
        if dormitory_id is not None:
            query = query.filter(Payment.dormitory_id == dormitory_id)
        if room_id is not None:
            query = query.filter(Payment.room_id == room_id)
        if status:
            query = query.filter(Payment.status == status)
        if date_from is not None:
            query = query.filter(Payment.period_end >= date_from)
        if date_to is not None:
            query = query.filter(Payment.period_start <= date_to)

        return (
            query.order_by(Payment.created_at.desc(), Payment.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_for_admin(
        self,
        *,
        user_id: int | None = None,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        query = self.db.query(Payment)
        if user_id is not None:
            query = query.filter(Payment.user_id == user_id)
        if dormitory_id is not None:
            query = query.filter(Payment.dormitory_id == dormitory_id)
        if room_id is not None:
            query = query.filter(Payment.room_id == room_id)
        if status:
            query = query.filter(Payment.status == status)
        if date_from is not None:
            query = query.filter(Payment.period_end >= date_from)
        if date_to is not None:
            query = query.filter(Payment.period_start <= date_to)
        return query.count()

    def sum_amount_for_user(self, user_id: int, statuses: Iterable[str]) -> float:
        amount = (
            self.db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.user_id == user_id,
                Payment.status.in_(list(statuses)),
            )
            .scalar()
        )
        return float(amount or 0)

    def sum_wallet_paid_for_user(self, user_id: int) -> float:
        amount = (
            self.db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.user_id == user_id,
                Payment.status == "paid",
                Payment.payment_channel == "wallet",
            )
            .scalar()
        )
        return float(amount or 0)
