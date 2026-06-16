# -*- coding: utf-8 -*-
"""Репозиторий для общих реквизитов пополнения."""
from sqlalchemy.orm import Session, joinedload

from api.db.models import PaymentAccountSettings
from api.repositories.base import BaseRepository


class PaymentAccountSettingsRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, PaymentAccountSettings)

    def get_current(self) -> PaymentAccountSettings | None:
        return (
            self.db.query(PaymentAccountSettings)
            .options(joinedload(PaymentAccountSettings.updated_by))
            .order_by(PaymentAccountSettings.id.desc())
            .first()
        )
