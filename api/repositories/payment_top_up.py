# -*- coding: utf-8 -*-
"""Репозиторий для пополнений баланса пользователя."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.db.models import PaymentTopUp
from api.repositories.base import BaseRepository


class PaymentTopUpRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, PaymentTopUp)

    def _base_query(self):
        return self.db.query(PaymentTopUp).options(
            joinedload(PaymentTopUp.user),
            joinedload(PaymentTopUp.reviewed_by),
        )

    def get_with_relations(self, top_up_id: int) -> PaymentTopUp | None:
        return self._base_query().filter(PaymentTopUp.id == top_up_id).first()

    def list_for_user(
        self,
        user_id: int,
        *,
        statuses: Iterable[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PaymentTopUp]:
        query = self._base_query().filter(PaymentTopUp.user_id == user_id)
        if statuses:
            query = query.filter(PaymentTopUp.status.in_(list(statuses)))
        if date_from is not None:
            query = query.filter(func.date(PaymentTopUp.created_at) >= date_from)
        if date_to is not None:
            query = query.filter(func.date(PaymentTopUp.created_at) <= date_to)
        return query.order_by(PaymentTopUp.created_at.desc(), PaymentTopUp.id.desc()).all()

    def sum_confirmed_for_user(self, user_id: int) -> float:
        amount = (
            self.db.query(func.coalesce(func.sum(PaymentTopUp.amount), 0))
            .filter(
                PaymentTopUp.user_id == user_id,
                PaymentTopUp.status == "confirmed",
            )
            .scalar()
        )
        return float(amount or 0)
