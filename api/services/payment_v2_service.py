# -*- coding: utf-8 -*-
"""Бизнес-логика API v2 для оплат и внутреннего баланса студента."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from api.core.exceptions import (
    ConflictError,
    DatabaseError,
    DatabaseUnavailableError,
    DormitoryNotFoundError,
    ForbiddenError,
    NotFoundError,
    RoomNotFoundError,
    UserNotFoundError,
    ValidationError,
)
from api.db.models import Dormitory, Payment, PaymentAccountSettings, PaymentTopUp, Room, User
from api.repositories.payment import PaymentRepository
from api.repositories.payment_account_settings import PaymentAccountSettingsRepository
from api.repositories.payment_top_up import PaymentTopUpRepository
from api.schemas.payment_v2 import (
    PaymentAccountSettingsResponse,
    PaymentAccountSettingsUpdate,
    PaymentBalanceResponse,
    PaymentChartResponse,
    PaymentCurrentListResponse,
    PaymentDashboardResponse,
    PaymentHistoryEntryResponse,
    PaymentHistoryListResponse,
    PaymentInvoiceCreateV2,
    PaymentInvoiceListResponse,
    PaymentInvoiceUpdateV2,
    PaymentInvoiceV2Response,
    PaymentPayResultResponse,
    PaymentSummaryItemResponse,
    PaymentTopUpCreate,
    PaymentTopUpPreviewResponse,
    PaymentTopUpResponse,
)
from api.services.user_helpers import user_has_role


ALLOWED_INVOICE_STATUSES = {"pending", "paid", "overdue", "cancelled", "partially_paid"}
ALLOWED_TOP_UP_STATUSES = {"submitted", "confirmed", "rejected"}
ALLOWED_PAYMENT_CHANNELS = {"wallet", "bank_transfer", "cash", "manual", "external"}
MANAGE_PAYMENT_ROLES = {"admin", "commandant", "council_president", "council_member"}
MANAGE_PAYMENT_SETTINGS_ROLES = {"admin", "commandant"}
CURRENT_INVOICE_STATUSES = {"pending", "overdue", "partially_paid"}


class PaymentV2Service:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.account_repo = PaymentAccountSettingsRepository(db)
        self.top_up_repo = PaymentTopUpRepository(db)

    def get_balance(self, current_user: User) -> PaymentBalanceResponse:
        try:
            total_top_ups = self.top_up_repo.sum_confirmed_for_user(current_user.id)
            wallet_spent = self.payment_repo.sum_wallet_paid_for_user(current_user.id)
            pending_amount = self.payment_repo.sum_amount_for_user(current_user.id, {"pending", "partially_paid"})
            overdue_amount = self._get_overdue_amount(current_user.id)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        balance = max(0.0, round(total_top_ups - wallet_spent, 2))
        return PaymentBalanceResponse(
            balance=balance,
            total_top_ups=round(total_top_ups, 2),
            total_wallet_spent=round(wallet_spent, 2),
            pending_amount=round(pending_amount, 2),
            overdue_amount=round(overdue_amount, 2),
        )

    def get_dashboard(
        self,
        current_user: User,
        *,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        history_limit: int = 20,
    ) -> PaymentDashboardResponse:
        if status is not None:
            self._validate_invoice_status(status)

        current_list = self.list_current(current_user, status=status)
        history_list = self.list_history(
            current_user,
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=history_limit,
        )
        balance = self.get_balance(current_user)
        chart = self._build_chart(current_user.id)

        summary = [
            self._summary_item("balance", "Баланс", balance.balance),
            self._summary_item("to_pay", "К оплате", balance.pending_amount + balance.overdue_amount),
            self._summary_item("overdue", "Просрочено", balance.overdue_amount),
            self._summary_item("top_ups", "Пополнено", balance.total_top_ups),
        ]

        account = None
        settings = self.account_repo.get_current()
        if settings is not None:
            account = self._build_account_response(settings)

        return PaymentDashboardResponse(
            balance=balance.balance,
            summary=summary,
            current=current_list.items,
            history=history_list.items,
            chart=chart,
            top_up_account=account,
        )

    def list_current(
        self,
        current_user: User,
        *,
        status: str | None = None,
    ) -> PaymentCurrentListResponse:
        if status is not None:
            if status not in CURRENT_INVOICE_STATUSES:
                raise ValidationError(
                    "Для текущих начислений доступны только статусы: "
                    f"{sorted(CURRENT_INVOICE_STATUSES)}"
                )

        try:
            items = self.payment_repo.list_current_for_user(
                current_user.id,
                statuses={status} if status else CURRENT_INVOICE_STATUSES,
            )
            self._normalize_invoice_statuses(items)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        serialized = [
            self._build_invoice_response(item, current_user=current_user)
            for item in items
            if item.status in CURRENT_INVOICE_STATUSES and (status is None or item.status == status)
        ]
        return PaymentCurrentListResponse(items=serialized, total=len(serialized))

    def list_history(
        self,
        current_user: User,
        *,
        direction: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
    ) -> PaymentHistoryListResponse:
        if direction is not None and direction not in {"incoming", "outgoing"}:
            raise ValidationError("direction должен быть incoming или outgoing")
        if status is not None and status not in ALLOWED_TOP_UP_STATUSES.union({"paid"}):
            raise ValidationError(
                "Для истории доступны только статусы: "
                f"{sorted(ALLOWED_TOP_UP_STATUSES.union({'paid'}))}"
            )

        try:
            top_ups = []
            if direction in {None, "incoming"}:
                if status is None or status in ALLOWED_TOP_UP_STATUSES:
                    top_up_statuses = {status} if status in ALLOWED_TOP_UP_STATUSES else None
                    top_ups = self.top_up_repo.list_for_user(
                        current_user.id,
                        statuses=top_up_statuses,
                        date_from=date_from,
                        date_to=date_to,
                    )

            payments = []
            if direction in {None, "outgoing"} and status in {None, "paid"}:
                payments = self.payment_repo.list_paid_for_user(
                    current_user.id,
                    date_from=date_from,
                    date_to=date_to,
                )
                self._normalize_invoice_statuses(payments)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        items = [
            *[self._build_history_from_top_up(item) for item in top_ups],
            *[self._build_history_from_payment(item) for item in payments],
        ]
        items.sort(key=lambda item: item.occurred_at, reverse=True)

        if limit > 0:
            items = items[:limit]

        return PaymentHistoryListResponse(items=items, total=len(items))

    def preview_top_up(self, current_user: User, amount: float) -> PaymentTopUpPreviewResponse:
        if amount <= 0:
            raise ValidationError("Сумма пополнения должна быть больше нуля")

        settings = self._get_account_settings_or_raise()
        return PaymentTopUpPreviewResponse(
            amount=round(float(amount), 2),
            transfer_reference=self._generate_transfer_reference(current_user.id),
            account=self._build_account_response(settings),
        )

    def create_top_up(self, current_user: User, data: PaymentTopUpCreate) -> PaymentTopUpResponse:
        settings = self._get_account_settings_or_raise()
        now = datetime.utcnow()

        try:
            top_up = self.top_up_repo.create(
                user_id=current_user.id,
                amount=Decimal(str(round(data.amount, 2))),
                status="confirmed",
                transfer_reference=self._generate_transfer_reference(current_user.id),
                account_number_snapshot=settings.account_number,
                recipient_name_snapshot=settings.recipient_name,
                bank_name_snapshot=settings.bank_name,
                receipt_file_name=data.receipt_file_name,
                receipt_file_url=data.receipt_file_url,
                comment=data.comment,
                reviewed_by_id=settings.updated_by_id,
                credited_at=now,
                created_at=now,
                updated_at=now,
            )
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        balance_after = self.get_balance(current_user).balance
        return self._build_top_up_response(top_up, balance_after=balance_after)

    def pay_invoice(self, current_user: User, payment_id: int) -> PaymentPayResultResponse:
        try:
            payment = self.payment_repo.get_with_relations(payment_id)
        except OperationalError:
            raise DatabaseUnavailableError()

        if payment is None:
            raise NotFoundError("Начисление", str(payment_id))
        if payment.user_id != current_user.id:
            raise ForbiddenError("Нельзя оплачивать чужие начисления")

        self._normalize_invoice_statuses([payment])

        if payment.status not in CURRENT_INVOICE_STATUSES:
            raise ConflictError("Это начисление уже не требует оплаты")

        balance = self.get_balance(current_user)
        amount = float(payment.amount or 0)
        if balance.balance < amount:
            raise ConflictError("Недостаточно средств на внутреннем балансе")

        payment.status = "paid"
        payment.payment_channel = "wallet"
        payment.paid_at = datetime.utcnow()
        payment.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(payment)
        except OperationalError:
            self.db.rollback()
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        balance_after = self.get_balance(current_user).balance
        return PaymentPayResultResponse(
            message="Счет успешно оплачен с внутреннего баланса",
            balance_after=balance_after,
            invoice=self._build_invoice_response(payment, current_user=current_user),
        )

    def get_account_settings(self, current_user: User) -> PaymentAccountSettingsResponse:
        settings = self._get_account_settings_or_raise()
        return self._build_account_response(settings)

    def update_account_settings(
        self,
        current_user: User,
        data: PaymentAccountSettingsUpdate,
    ) -> PaymentAccountSettingsResponse:
        self._ensure_role(current_user, MANAGE_PAYMENT_SETTINGS_ROLES)

        existing = self.account_repo.get_current()
        payload = {
            "account_number": data.account_number,
            "recipient_name": data.recipient_name,
            "bank_name": data.bank_name,
            "payment_instructions": data.payment_instructions,
            "updated_by_id": current_user.id,
            "updated_at": datetime.utcnow(),
        }

        try:
            if existing is None:
                existing = self.account_repo.create(
                    **payload,
                    created_at=datetime.utcnow(),
                )
            else:
                existing = self.account_repo.update(existing, **payload)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        return self._build_account_response(existing)

    def list_invoices_for_manager(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        user_id: int | None = None,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PaymentInvoiceListResponse:
        self._ensure_role(current_user, MANAGE_PAYMENT_ROLES)
        if status is not None:
            self._validate_invoice_status(status)

        skip = (page - 1) * page_size

        try:
            items = self.payment_repo.list_for_admin(
                user_id=user_id,
                dormitory_id=dormitory_id,
                room_id=room_id,
                status=status,
                date_from=date_from,
                date_to=date_to,
                skip=skip,
                limit=page_size,
            )
            total = self.payment_repo.count_for_admin(
                user_id=user_id,
                dormitory_id=dormitory_id,
                room_id=room_id,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )
            self._normalize_invoice_statuses(items)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        return PaymentInvoiceListResponse(
            items=[self._build_invoice_response(item, current_user=current_user) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_invoice(
        self,
        current_user: User,
        data: PaymentInvoiceCreateV2,
    ) -> PaymentInvoiceV2Response:
        self._ensure_role(current_user, MANAGE_PAYMENT_ROLES)
        self._validate_invoice_status(data.status)
        user, dormitory, room = self._validate_invoice_targets(
            user_id=data.user_id,
            dormitory_id=data.dormitory_id,
            room_id=data.room_id,
            period_start=data.period_start,
            period_end=data.period_end,
        )

        try:
            payment = self.payment_repo.create(
                user_id=user.id,
                dormitory_id=dormitory.id if dormitory else None,
                room_id=room.id if room else None,
                period_start=data.period_start,
                period_end=data.period_end,
                amount=Decimal(str(round(data.amount, 2))),
                status=data.status,
                description=data.description,
                due_date=data.due_date,
                admin_comment=data.admin_comment,
                created_by_id=current_user.id,
                payment_channel="manual" if data.status == "paid" else None,
                paid_at=datetime.utcnow() if data.status == "paid" else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        payment = self.payment_repo.get_with_relations(payment.id) or payment
        return self._build_invoice_response(payment, current_user=current_user)

    def update_invoice(
        self,
        current_user: User,
        payment_id: int,
        data: PaymentInvoiceUpdateV2,
    ) -> PaymentInvoiceV2Response:
        self._ensure_role(current_user, MANAGE_PAYMENT_ROLES)
        payment = self.payment_repo.get_with_relations(payment_id)
        if payment is None:
            raise NotFoundError("Начисление", str(payment_id))

        if data.status is not None:
            self._validate_invoice_status(data.status)
        if data.payment_channel is not None:
            self._validate_payment_channel(data.payment_channel)

        new_period_start = data.period_start or payment.period_start
        new_period_end = data.period_end or payment.period_end
        new_dormitory_id = payment.dormitory_id if data.dormitory_id is None else data.dormitory_id
        new_room_id = payment.room_id if data.room_id is None else data.room_id
        self._validate_invoice_targets(
            user_id=payment.user_id,
            dormitory_id=new_dormitory_id,
            room_id=new_room_id,
            period_start=new_period_start,
            period_end=new_period_end,
        )

        update_payload = {
            "period_start": new_period_start,
            "period_end": new_period_end,
            "updated_at": datetime.utcnow(),
        }
        if data.amount is not None:
            update_payload["amount"] = Decimal(str(round(data.amount, 2)))
        if data.description is not None:
            update_payload["description"] = data.description
        if data.due_date is not None:
            update_payload["due_date"] = data.due_date
        if data.dormitory_id is not None:
            update_payload["dormitory_id"] = data.dormitory_id
        if data.room_id is not None:
            update_payload["room_id"] = data.room_id
        if data.admin_comment is not None:
            update_payload["admin_comment"] = data.admin_comment

        new_status = data.status or payment.status
        new_channel = data.payment_channel if data.payment_channel is not None else payment.payment_channel

        if data.status is not None:
            update_payload["status"] = data.status
            if data.status == "paid":
                update_payload["paid_at"] = payment.paid_at or datetime.utcnow()
                update_payload["payment_channel"] = new_channel or "manual"
            else:
                update_payload["paid_at"] = None
                if data.status in CURRENT_INVOICE_STATUSES or data.status == "cancelled":
                    update_payload["payment_channel"] = None if data.payment_channel is None else data.payment_channel

        if new_status == "paid" and data.payment_channel is not None:
            update_payload["payment_channel"] = data.payment_channel
        elif data.payment_channel is not None and new_status != "paid":
            update_payload["payment_channel"] = data.payment_channel

        try:
            payment = self.payment_repo.update(payment, **update_payload)
        except OperationalError:
            raise DatabaseUnavailableError()
        except SQLAlchemyError:
            self.db.rollback()
            raise DatabaseError()

        payment = self.payment_repo.get_with_relations(payment.id) or payment
        return self._build_invoice_response(payment, current_user=current_user)

    def _build_invoice_response(self, payment: Payment, *, current_user: User) -> PaymentInvoiceV2Response:
        return PaymentInvoiceV2Response(
            id=payment.id,
            user_id=payment.user_id,
            user_name=payment.user.full_name if payment.user else "Unknown",
            dormitory_id=payment.dormitory_id,
            dormitory_name=payment.dormitory.name if payment.dormitory else None,
            room_id=payment.room_id,
            room_number=payment.room.room_number if payment.room else None,
            title=self._build_invoice_title(payment),
            description=payment.description,
            period=self._build_invoice_period_label(payment),
            period_start=payment.period_start,
            period_end=payment.period_end,
            amount=round(float(payment.amount or 0), 2),
            status=payment.status,
            status_text=self._status_text(payment.status),
            due_date=payment.due_date,
            paid_at=payment.paid_at,
            payment_channel=payment.payment_channel,
            admin_comment=payment.admin_comment,
            created_by_id=payment.created_by_id,
            created_by_name=payment.created_by.full_name if payment.created_by else None,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            can_pay=(
                payment.user_id == current_user.id
                and payment.status in CURRENT_INVOICE_STATUSES
            ),
        )

    def _build_history_from_top_up(self, top_up: PaymentTopUp) -> PaymentHistoryEntryResponse:
        return PaymentHistoryEntryResponse(
            id=f"topup-{top_up.id}",
            entry_type="top_up",
            direction="incoming",
            title="Пополнение баланса",
            description=top_up.comment,
            period=self._top_up_period_label(top_up),
            amount=round(float(top_up.amount or 0), 2),
            status=top_up.status,
            status_text=self._top_up_status_text(top_up.status),
            occurred_at=top_up.credited_at or top_up.created_at,
            payment_channel="bank_transfer",
            related_top_up_id=top_up.id,
            receipt_file_name=top_up.receipt_file_name,
            transfer_reference=top_up.transfer_reference,
        )

    def _build_history_from_payment(self, payment: Payment) -> PaymentHistoryEntryResponse:
        return PaymentHistoryEntryResponse(
            id=f"payment-{payment.id}",
            entry_type="invoice_payment",
            direction="outgoing",
            title=self._build_invoice_title(payment),
            description=payment.description,
            period=self._build_invoice_period_label(payment),
            amount=round(float(payment.amount or 0), 2),
            status=payment.status,
            status_text=self._status_text(payment.status),
            occurred_at=payment.paid_at or payment.updated_at or payment.created_at,
            payment_channel=payment.payment_channel or "external",
            related_payment_id=payment.id,
        )

    def _build_top_up_response(self, top_up: PaymentTopUp, *, balance_after: float) -> PaymentTopUpResponse:
        return PaymentTopUpResponse(
            id=top_up.id,
            user_id=top_up.user_id,
            amount=round(float(top_up.amount or 0), 2),
            status=top_up.status,
            status_text=self._top_up_status_text(top_up.status),
            transfer_reference=top_up.transfer_reference,
            account_number=top_up.account_number_snapshot,
            recipient_name=top_up.recipient_name_snapshot,
            bank_name=top_up.bank_name_snapshot,
            receipt_file_name=top_up.receipt_file_name,
            receipt_file_url=top_up.receipt_file_url,
            comment=top_up.comment,
            credited_at=top_up.credited_at,
            created_at=top_up.created_at,
            balance_after=balance_after,
        )

    def _build_account_response(self, settings: PaymentAccountSettings) -> PaymentAccountSettingsResponse:
        return PaymentAccountSettingsResponse(
            account_number=settings.account_number,
            recipient_name=settings.recipient_name,
            bank_name=settings.bank_name,
            payment_instructions=settings.payment_instructions,
            updated_by_id=settings.updated_by_id,
            updated_by_name=settings.updated_by.full_name if settings.updated_by else None,
            updated_at=settings.updated_at,
        )

    def _build_chart(self, user_id: int) -> PaymentChartResponse:
        top_ups = self.top_up_repo.list_for_user(user_id, statuses={"confirmed"})
        payments = self.payment_repo.list_paid_for_user(user_id)

        month_keys = []
        current = date.today().replace(day=1)
        for offset in range(5, -1, -1):
            year = current.year
            month = current.month - offset
            while month <= 0:
                month += 12
                year -= 1
            month_keys.append((year, month))

        incoming_map = defaultdict(float)
        outgoing_map = defaultdict(float)

        for item in top_ups:
            stamp = item.credited_at or item.created_at
            incoming_map[(stamp.year, stamp.month)] += float(item.amount or 0)
        for item in payments:
            stamp = item.paid_at or item.updated_at or item.created_at
            outgoing_map[(stamp.year, stamp.month)] += float(item.amount or 0)

        labels = []
        incoming_values = []
        outgoing_values = []
        net_values = []

        for year, month in month_keys:
            labels.append(self._month_label(month))
            incoming_amount = round(incoming_map[(year, month)], 2)
            outgoing_amount = round(outgoing_map[(year, month)], 2)
            incoming_values.append(incoming_amount)
            outgoing_values.append(outgoing_amount)
            net_values.append(round(incoming_amount - outgoing_amount, 2))

        return PaymentChartResponse(
            labels=labels,
            values=outgoing_values,
            incoming_values=incoming_values,
            outgoing_values=outgoing_values,
            net_values=net_values,
        )

    def _get_account_settings_or_raise(self) -> PaymentAccountSettings:
        settings = self.account_repo.get_current()
        if settings is None:
            raise ValidationError("Реквизиты для пополнения пока не настроены комендантом")
        return settings

    def _ensure_role(self, current_user: User, allowed_roles: set[str]) -> None:
        if not user_has_role(current_user, *sorted(allowed_roles)):
            raise ForbiddenError("Недостаточно прав для работы с оплатами")

    def _validate_invoice_targets(
        self,
        *,
        user_id: int,
        dormitory_id: int | None,
        room_id: int | None,
        period_start: date,
        period_end: date,
    ) -> tuple[User, Dormitory | None, Room | None]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise UserNotFoundError(user_id)
        if period_end < period_start:
            raise ValidationError("Дата окончания периода не может быть раньше даты начала")

        dormitory = None
        room = None
        if dormitory_id is not None:
            dormitory = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
            if dormitory is None:
                raise DormitoryNotFoundError(dormitory_id)

        if room_id is not None:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if room is None:
                raise RoomNotFoundError(room_id)
            if dormitory is not None and room.dormitory_id != dormitory.id:
                raise ValidationError("Комната не относится к указанному общежитию")
            if dormitory is None:
                dormitory = room.dormitory

        return user, dormitory, room

    def _normalize_invoice_statuses(self, payments: list[Payment]) -> None:
        today = date.today()
        changed = False
        for payment in payments:
            if payment.status == "pending" and payment.due_date and payment.due_date < today:
                payment.status = "overdue"
                payment.updated_at = datetime.utcnow()
                changed = True
        if changed:
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
                raise

    def _build_invoice_title(self, payment: Payment) -> str:
        if payment.description:
            return payment.description.strip().splitlines()[0][:120]
        if payment.period_start == payment.period_end:
            return f"Начисление за {payment.period_start.strftime('%d.%m.%Y')}"
        return f"Начисление {payment.period_start.strftime('%d.%m.%Y')} - {payment.period_end.strftime('%d.%m.%Y')}"

    def _build_invoice_period_label(self, payment: Payment) -> str:
        if payment.status == "paid" and payment.paid_at:
            return f"Оплачено {payment.paid_at.strftime('%d.%m.%Y')}"
        if payment.due_date:
            return f"до {payment.due_date.strftime('%d.%m.%Y')}"
        return f"{payment.period_start.strftime('%d.%m.%Y')} - {payment.period_end.strftime('%d.%m.%Y')}"

    def _top_up_period_label(self, top_up: PaymentTopUp) -> str:
        stamp = top_up.credited_at or top_up.created_at
        prefix = "Пополнено" if top_up.status == "confirmed" else "Отправлено"
        return f"{prefix} {stamp.strftime('%d.%m.%Y')}"

    def _generate_transfer_reference(self, user_id: int) -> str:
        return f"TOPUP-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    def _summary_item(self, key: str, label: str, amount: float) -> PaymentSummaryItemResponse:
        rounded = round(float(amount or 0), 2)
        return PaymentSummaryItemResponse(
            key=key,
            label=label,
            amount=rounded,
            value=self._format_money(rounded),
        )

    def _format_money(self, amount: float) -> str:
        formatted = f"{amount:,.2f}".replace(",", " ").replace(".00", "")
        return f"{formatted} ₽"

    def _get_overdue_amount(self, user_id: int) -> float:
        items = self.payment_repo.list_current_for_user(user_id, statuses={"pending", "overdue"})
        self._normalize_invoice_statuses(items)
        total = sum(float(item.amount or 0) for item in items if item.status == "overdue")
        return round(total, 2)

    def _validate_invoice_status(self, status: str) -> None:
        if status not in ALLOWED_INVOICE_STATUSES:
            raise ValidationError(
                "Недопустимый статус счета. "
                f"Допустимые значения: {sorted(ALLOWED_INVOICE_STATUSES)}"
            )

    def _validate_payment_channel(self, channel: str) -> None:
        if channel not in ALLOWED_PAYMENT_CHANNELS:
            raise ValidationError(
                "Недопустимый канал оплаты. "
                f"Допустимые значения: {sorted(ALLOWED_PAYMENT_CHANNELS)}"
            )

    def _status_text(self, status: str) -> str:
        return {
            "pending": "К оплате",
            "paid": "Оплачено",
            "overdue": "Просрочено",
            "cancelled": "Отменено",
            "partially_paid": "Частично оплачено",
        }.get(status, status)

    def _top_up_status_text(self, status: str) -> str:
        return {
            "submitted": "Чек отправлен",
            "confirmed": "Пополнение подтверждено",
            "rejected": "Пополнение отклонено",
        }.get(status, status)

    def _month_label(self, month: int) -> str:
        return {
            1: "Янв",
            2: "Фев",
            3: "Мар",
            4: "Апр",
            5: "Май",
            6: "Июн",
            7: "Июл",
            8: "Авг",
            9: "Сен",
            10: "Окт",
            11: "Ноя",
            12: "Дек",
        }[month]
