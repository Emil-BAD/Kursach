from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from api.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from api.db.models import (
    CalendarEvent,
    CleanlinessHistory,
    Dormitory,
    KitchenDutyPlan,
    Payment,
    PaymentTopUp,
    Product,
    ResidenceHistory,
    RentalBooking,
    RentalListing,
    Role,
    Room,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestComment,
    User,
    UserActivity,
    UserViolation,
)
from api.schemas.common import paginate_response
from api.schemas.product import ProductModeration
from api.schemas.service_request import ServiceRequestCommentCreate, ServiceRequestUpdate
from api.services.admin_dashboard_service import AdminDashboardService
from api.services.admin_permissions_service import AdminPermissionsService
from api.services.payment_v2_service import PaymentV2Service
from api.services.user_helpers import build_user_response


ALLOWED_REQUEST_STATUSES = {"new", "in_progress", "resolved", "rejected", "closed"}
ALLOWED_RENTAL_REVIEW_STATUSES = {"pending", "approved", "rejected"}
ALLOWED_RENTAL_LISTING_STATUSES = {"active", "paused", "archived"}
ALLOWED_RENTAL_AVAILABILITY_STATUSES = {"free", "occupied"}
ALLOWED_TOP_UP_STATUSES = {"submitted", "confirmed", "rejected"}


class AdminModuleService:
    def __init__(self, db: Session):
        self.db = db
        self.permissions = AdminPermissionsService()
        self.dashboard_service = AdminDashboardService(db)
        self.payment_service = PaymentV2Service(db)

    def list_users(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        role_name: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_users")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)

        query = self.db.query(User).options(
            joinedload(User.role),
            joinedload(User.dormitory),
            joinedload(User.room),
        )
        if scoped_dormitory_id is not None:
            query = query.filter(User.dormitory_id == scoped_dormitory_id)
        if room_id is not None:
            query = query.filter(User.room_id == room_id)
        if role_name:
            query = query.join(User.role).filter(func.lower(Role.role_name) == role_name.lower())
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(or_(User.full_name.ilike(pattern), User.student_card.ilike(pattern), User.email.ilike(pattern)))

        total = query.count()
        items = (
            query.order_by(User.full_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "student_card": item.student_card,
                "full_name": item.full_name,
                "role_name": item.role.role_name if item.role else None,
                "dormitory_id": item.dormitory_id,
                "dormitory_name": item.dormitory.name if item.dormitory else None,
                "room_id": item.room_id,
                "room_number": item.room.room_number if item.room else None,
                "group_number": item.group_number,
                "faculty": item.faculty,
                "course": item.course,
                "points_total": (item.points or {}).get("total", 0) if isinstance(item.points, dict) else 0,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def get_user_detail(self, current_user: User, user_id: int) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_users")
        user = (
            self.db.query(User)
            .options(joinedload(User.role), joinedload(User.dormitory), joinedload(User.room))
            .filter(User.id == user_id)
            .first()
        )
        if user is None:
            raise NotFoundError("Пользователь", str(user_id))
        self._ensure_user_in_scope(current_user, user)
        payload = build_user_response(self.db, user).model_dump()
        payload["role_name"] = user.role.role_name if user.role else None
        return payload

    def list_dormitories(self, current_user: User) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_residence")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        query = self.db.query(Dormitory)
        if scoped_dormitory_id is not None:
            query = query.filter(Dormitory.id == scoped_dormitory_id)
        items = query.order_by(Dormitory.id.asc()).all()
        return {
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "address": item.address,
                    "image_urls": item.image_urls or [],
                }
                for item in items
            ],
            "total": len(items),
        }

    def list_rooms(
        self,
        current_user: User,
        *,
        dormitory_id: int | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_residence")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(Room).options(joinedload(Room.dormitory))
        if scoped_dormitory_id is not None:
            query = query.filter(Room.dormitory_id == scoped_dormitory_id)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(Room.room_number.cast(str).ilike(pattern))
        items = query.order_by(Room.room_number.asc()).all()
        return {
            "items": [
                {
                    "id": item.id,
                    "room_number": item.room_number,
                    "capacity": item.capacity,
                    "dormitory_id": item.dormitory_id,
                    "dormitory_name": item.dormitory.name if item.dormitory else None,
                    "cleanliness_points": item.cleanliness_points,
                    "occupants_count": len(item.users),
                }
                for item in items
            ],
            "total": len(items),
        }

    def list_residence_history(
        self,
        current_user: User,
        *,
        user_id: int | None = None,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_residence")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(ResidenceHistory).options(
            joinedload(ResidenceHistory.user),
            joinedload(ResidenceHistory.dormitory),
            joinedload(ResidenceHistory.room),
        )
        if scoped_dormitory_id is not None:
            query = query.filter(ResidenceHistory.dormitory_id == scoped_dormitory_id)
        if user_id is not None:
            query = query.filter(ResidenceHistory.user_id == user_id)
        if room_id is not None:
            query = query.filter(ResidenceHistory.room_id == room_id)

        total = query.count()
        items = (
            query.order_by(ResidenceHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "user_id": item.user_id,
                "user_name": item.user.full_name if item.user else None,
                "dormitory_id": item.dormitory_id,
                "dormitory_name": item.dormitory.name if item.dormitory else None,
                "room_id": item.room_id,
                "room_number": item.room.room_number if item.room else None,
                "check_in_date": item.check_in_date.isoformat() if item.check_in_date else None,
                "check_out_date": item.check_out_date.isoformat() if item.check_out_date else None,
                "eviction_reason": item.eviction_reason,
                "comment": item.comment,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def list_service_requests(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        request_type: str | None = None,
        dormitory_id: int | None = None,
        room_id: int | None = None,
        student_id: int | None = None,
        executor_id: int | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self._service_requests_base_query()
        if scoped_dormitory_id is not None:
            query = query.join(ServiceRequest.student).filter(
                or_(
                    ServiceRequest.dormitory_id == scoped_dormitory_id,
                    and_(ServiceRequest.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if status:
            query = query.filter(ServiceRequest.status == status)
        if request_type:
            query = query.filter(ServiceRequest.request_type == request_type)
        if room_id is not None:
            query = query.filter(ServiceRequest.room_id == room_id)
        if student_id is not None:
            query = query.filter(ServiceRequest.student_id == student_id)
        if executor_id is not None:
            query = query.filter(ServiceRequest.executor_id == executor_id)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(or_(ServiceRequest.title.ilike(pattern), ServiceRequest.description.ilike(pattern)))

        total = query.count()
        items = (
            query.order_by(ServiceRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return paginate_response([self._serialize_service_request(item) for item in items], page, page_size, total)

    def get_service_request_detail(self, current_user: User, request_id: int) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        item = self._get_service_request_or_404(request_id)
        self._ensure_service_request_in_scope(current_user, item)
        return self._serialize_service_request(item, include_relations=True)

    def update_service_request(self, current_user: User, request_id: int, data: ServiceRequestUpdate) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        item = self._get_service_request_or_404(request_id)
        self._ensure_service_request_in_scope(current_user, item)

        if data.status is not None and data.status not in ALLOWED_REQUEST_STATUSES:
            raise ValidationError("Недопустимый статус заявки")

        if data.title is not None:
            item.title = data.title.strip()
        if data.description is not None:
            item.description = data.description.strip()
        if data.request_type is not None:
            item.request_type = data.request_type.strip()
        if data.status is not None:
            item.status = data.status
        if data.dormitory_id is not None:
            item.dormitory_id = data.dormitory_id
        if data.room_id is not None:
            item.room_id = data.room_id
        if data.student_id is not None:
            item.student_id = data.student_id
        if data.executor_id is not None:
            item.executor_id = data.executor_id
        if data.resolution_comment is not None:
            item.resolution_comment = data.resolution_comment.strip() or None
        if data.status in {"resolved", "rejected", "closed"}:
            item.closed_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_service_request(self._get_service_request_or_404(item.id), include_relations=True)

    def assign_service_request(self, current_user: User, request_id: int, executor_id: int) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        item = self._get_service_request_or_404(request_id)
        executor = self.db.query(User).filter(User.id == executor_id).first()
        if executor is None:
            raise NotFoundError("Исполнитель", str(executor_id))
        self._ensure_service_request_in_scope(current_user, item)
        self._ensure_user_in_scope(current_user, executor)
        item.executor_id = executor_id
        if item.status == "new":
            item.status = "in_progress"
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_service_request(self._get_service_request_or_404(item.id), include_relations=True)

    def add_service_request_comment(
        self,
        current_user: User,
        request_id: int,
        data: ServiceRequestCommentCreate,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        item = self._get_service_request_or_404(request_id)
        self._ensure_service_request_in_scope(current_user, item)
        comment = ServiceRequestComment(
            service_request_id=item.id,
            author_id=current_user.id,
            comment=data.comment.strip(),
        )
        item.updated_at = datetime.utcnow()
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return {
            "id": comment.id,
            "author_id": comment.author_id,
            "author_name": current_user.full_name,
            "comment": comment.comment,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }

    def close_service_request(
        self,
        current_user: User,
        request_id: int,
        *,
        resolution_comment: str | None,
        rejected: bool = False,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_requests")
        item = self._get_service_request_or_404(request_id)
        self._ensure_service_request_in_scope(current_user, item)
        item.status = "rejected" if rejected else "closed"
        item.resolution_comment = (resolution_comment or "").strip() or item.resolution_comment
        item.closed_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_service_request(self._get_service_request_or_404(item.id), include_relations=True)

    def get_payments_summary(self, current_user: User, *, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_payments")
        dashboard = self.dashboard_service.get_dashboard(current_user, dormitory_id=dormitory_id)
        return dashboard.get("payments") or {}

    def ensure_payment_payload_in_scope(
        self,
        current_user: User,
        *,
        user_id: int,
        dormitory_id: int | None,
        room_id: int | None,
    ) -> None:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        if scoped_dormitory_id is None:
            return
        target_user = self.db.query(User).filter(User.id == user_id).first()
        if target_user is None:
            raise NotFoundError("Пользователь", str(user_id))
        if target_user.dormitory_id != scoped_dormitory_id:
            raise ForbiddenError("Нельзя работать с начислениями другого общежития")
        if room_id is not None:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if room is None:
                raise NotFoundError("Комната", str(room_id))
            if room.dormitory_id != scoped_dormitory_id:
                raise ForbiddenError("Комната находится вне вашего общежития")

    def ensure_payment_record_in_scope(self, current_user: User, payment_id: int) -> None:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        if scoped_dormitory_id is None:
            return
        payment = self.db.query(Payment).options(joinedload(Payment.user)).filter(Payment.id == payment_id).first()
        if payment is None:
            raise NotFoundError("Начисление", str(payment_id))
        payment_dormitory_id = payment.dormitory_id or (payment.user.dormitory_id if payment.user else None)
        if payment_dormitory_id != scoped_dormitory_id:
            raise ForbiddenError("Нельзя изменять начисления другого общежития")

    def list_payment_top_ups(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_payments")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        query = self.db.query(PaymentTopUp).options(
            joinedload(PaymentTopUp.user),
            joinedload(PaymentTopUp.reviewed_by),
        ).join(PaymentTopUp.user)
        if scoped_dormitory_id is not None:
            query = query.filter(User.dormitory_id == scoped_dormitory_id)
        if status is not None:
            query = query.filter(PaymentTopUp.status == status)
        if user_id is not None:
            query = query.filter(PaymentTopUp.user_id == user_id)

        total = query.count()
        items = (
            query.order_by(PaymentTopUp.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "user_id": item.user_id,
                "user_name": item.user.full_name if item.user else None,
                "amount": float(item.amount or 0),
                "status": item.status,
                "transfer_reference": item.transfer_reference,
                "receipt_file_name": item.receipt_file_name,
                "receipt_file_url": item.receipt_file_url,
                "comment": item.comment,
                "reviewed_by_id": item.reviewed_by_id,
                "reviewed_by_name": item.reviewed_by.full_name if item.reviewed_by else None,
                "credited_at": item.credited_at.isoformat() if item.credited_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def review_payment_top_up(
        self,
        current_user: User,
        top_up_id: int,
        *,
        status: str,
        comment: str | None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_payments")
        if status not in ALLOWED_TOP_UP_STATUSES:
            raise ValidationError("Недопустимый статус пополнения")
        top_up = self.db.query(PaymentTopUp).options(joinedload(PaymentTopUp.user)).filter(PaymentTopUp.id == top_up_id).first()
        if top_up is None:
            raise NotFoundError("Пополнение", str(top_up_id))
        if self.permissions.scoped_dormitory_id(current_user) is not None and top_up.user and top_up.user.dormitory_id != self.permissions.scoped_dormitory_id(current_user):
            raise ForbiddenError("Нельзя менять пополнение другого общежития")
        top_up.status = status
        top_up.comment = comment.strip() if comment else top_up.comment
        top_up.reviewed_by_id = current_user.id
        top_up.updated_at = datetime.utcnow()
        top_up.credited_at = datetime.utcnow() if status == "confirmed" else None
        self.db.commit()
        self.db.refresh(top_up)
        return {
            "id": top_up.id,
            "status": top_up.status,
            "reviewed_by_id": top_up.reviewed_by_id,
            "comment": top_up.comment,
            "credited_at": top_up.credited_at.isoformat() if top_up.credited_at else None,
        }

    def list_market_products(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        category_id: int | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_market")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        query = self.db.query(Product).options(
            joinedload(Product.seller),
            joinedload(Product.category),
            joinedload(Product.dormitory),
        ).join(Product.seller)
        if scoped_dormitory_id is not None:
            query = query.filter(
                or_(
                    Product.dormitory_id == scoped_dormitory_id,
                    and_(Product.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if status is not None:
            query = query.filter(Product.status == status)
        if category_id is not None:
            query = query.filter(Product.category_id == category_id)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(or_(Product.title.ilike(pattern), Product.description.ilike(pattern)))

        total = query.count()
        items = (
            query.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "price": float(item.price or 0),
                "seller_id": item.seller_id,
                "seller_name": item.seller.full_name if item.seller else None,
                "category_id": item.category_id,
                "category_name": item.category.name if item.category else None,
                "dormitory_id": item.dormitory_id,
                "dormitory_name": item.dormitory.name if item.dormitory else None,
                "status": item.status,
                "rejection_reason": item.rejection_reason,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def moderate_market_product(
        self,
        current_user: User,
        product_id: int,
        moderation: ProductModeration,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_market")
        item = self.db.query(Product).options(joinedload(Product.seller)).filter(Product.id == product_id).first()
        if item is None:
            raise NotFoundError("Товар", str(product_id))
        if self.permissions.scoped_dormitory_id(current_user) is not None:
            item_dormitory_id = item.dormitory_id or (item.seller.dormitory_id if item.seller else None)
            if item_dormitory_id != self.permissions.scoped_dormitory_id(current_user):
                raise ForbiddenError("Нельзя модерировать товар другого общежития")
        item.status = moderation.status
        item.rejection_reason = moderation.rejection_reason if moderation.status == "rejected" else None
        self.db.commit()
        self.db.refresh(item)
        return {
            "id": item.id,
            "status": item.status,
            "rejection_reason": item.rejection_reason,
        }

    def list_market_rentals(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        listing_status: str | None = None,
        availability_status: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_market")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        query = self.db.query(RentalListing).options(
            joinedload(RentalListing.owner),
            joinedload(RentalListing.category),
            joinedload(RentalListing.dormitory),
            joinedload(RentalListing.bookings),
        ).join(RentalListing.owner)
        if scoped_dormitory_id is not None:
            query = query.filter(
                or_(
                    RentalListing.dormitory_id == scoped_dormitory_id,
                    and_(RentalListing.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if status is not None:
            query = query.filter(RentalListing.status == status)
        if listing_status is not None:
            query = query.filter(RentalListing.listing_status == listing_status)
        if availability_status is not None:
            query = query.filter(RentalListing.availability_status == availability_status)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(or_(RentalListing.title.ilike(pattern), RentalListing.description.ilike(pattern)))

        total = query.count()
        items = (
            query.order_by(RentalListing.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "title": item.title,
                "daily_price": float(item.daily_price or 0),
                "owner_id": item.owner_id,
                "owner_name": item.owner.full_name if item.owner else None,
                "status": item.status,
                "listing_status": item.listing_status,
                "availability_status": item.availability_status,
                "dormitory_id": item.dormitory_id,
                "dormitory_name": item.dormitory.name if item.dormitory else None,
                "bookings_count": len(item.bookings),
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def moderate_market_rental(
        self,
        current_user: User,
        listing_id: int,
        *,
        status: str | None = None,
        listing_status: str | None = None,
        availability_status: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_market")
        item = self.db.query(RentalListing).options(joinedload(RentalListing.owner)).filter(RentalListing.id == listing_id).first()
        if item is None:
            raise NotFoundError("Объявление аренды", str(listing_id))
        if self.permissions.scoped_dormitory_id(current_user) is not None:
            item_dormitory_id = item.dormitory_id or (item.owner.dormitory_id if item.owner else None)
            if item_dormitory_id != self.permissions.scoped_dormitory_id(current_user):
                raise ForbiddenError("Нельзя модерировать аренду другого общежития")
        if status is not None and status not in ALLOWED_RENTAL_REVIEW_STATUSES:
            raise ValidationError("Недопустимый статус модерации аренды")
        if listing_status is not None and listing_status not in ALLOWED_RENTAL_LISTING_STATUSES:
            raise ValidationError("Недопустимый listing_status")
        if availability_status is not None and availability_status not in ALLOWED_RENTAL_AVAILABILITY_STATUSES:
            raise ValidationError("Недопустимый availability_status")

        if status is not None:
            item.status = status
        if listing_status is not None:
            item.listing_status = listing_status
        if availability_status is not None:
            item.availability_status = availability_status
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return {
            "id": item.id,
            "status": item.status,
            "listing_status": item.listing_status,
            "availability_status": item.availability_status,
        }

    def list_market_bookings(
        self,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_manage_market")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        query = self.db.query(RentalBooking).options(
            joinedload(RentalBooking.listing).joinedload(RentalListing.owner),
            joinedload(RentalBooking.renter),
            joinedload(RentalBooking.approved_by),
        ).join(RentalBooking.listing)
        if scoped_dormitory_id is not None:
            query = query.filter(RentalListing.dormitory_id == scoped_dormitory_id)
        if status is not None:
            query = query.filter(RentalBooking.status == status)
        total = query.count()
        items = (
            query.order_by(RentalBooking.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        serialized = [
            {
                "id": item.id,
                "listing_id": item.listing_id,
                "listing_title": item.listing.title if item.listing else None,
                "renter_id": item.renter_id,
                "renter_name": item.renter.full_name if item.renter else None,
                "status": item.status,
                "start_date": item.start_date.isoformat() if item.start_date else None,
                "end_date": item.end_date.isoformat() if item.end_date else None,
                "total_price": float(item.total_price or 0),
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return paginate_response(serialized, page, page_size, total)

    def report_occupancy(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        dormitories_query = self.db.query(Dormitory).options(joinedload(Dormitory.rooms))
        if scoped_dormitory_id is not None:
            dormitories_query = dormitories_query.filter(Dormitory.id == scoped_dormitory_id)
        dormitories = dormitories_query.order_by(Dormitory.id.asc()).all()
        items = []
        for dormitory in dormitories:
            total_rooms = len(dormitory.rooms)
            total_places = sum(int(room.capacity or 0) for room in dormitory.rooms)
            occupied_places = self.db.query(User).filter(User.dormitory_id == dormitory.id, User.room_id.is_not(None)).count()
            free_places = max(total_places - occupied_places, 0)
            occupancy_percent = round((occupied_places / total_places) * 100, 2) if total_places else 0
            items.append(
                {
                    "dormitory_id": dormitory.id,
                    "dormitory_name": dormitory.name,
                    "total_rooms": total_rooms,
                    "total_places": total_places,
                    "occupied_places": occupied_places,
                    "free_places": free_places,
                    "occupancy_percent": occupancy_percent,
                }
            )
        return {"items": items, "total": len(items)}

    def report_discipline(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        violation_rows = (
            self.db.query(
                UserViolation.user_id,
                func.count(UserViolation.id),
                func.coalesce(func.sum(UserViolation.penalty_points), 0),
            )
            .group_by(UserViolation.user_id)
            .all()
        )
        activity_rows = (
            self.db.query(
                UserActivity.user_id,
                func.count(UserActivity.id),
                func.coalesce(func.sum(UserActivity.earned_points), 0),
            )
            .group_by(UserActivity.user_id)
            .all()
        )
        violation_map = {row[0]: {"count": int(row[1]), "points": int(row[2])} for row in violation_rows}
        activity_map = {row[0]: {"count": int(row[1]), "points": int(row[2])} for row in activity_rows}

        users_query = self.db.query(User).options(joinedload(User.dormitory), joinedload(User.room))
        if scoped_dormitory_id is not None:
            users_query = users_query.filter(User.dormitory_id == scoped_dormitory_id)
        users = users_query.order_by(User.full_name.asc()).all()

        items = []
        total_violations = 0
        total_penalty_points = 0
        total_earned_points = 0
        for user in users:
            v = violation_map.get(user.id, {"count": 0, "points": 0})
            a = activity_map.get(user.id, {"count": 0, "points": 0})
            total_violations += v["count"]
            total_penalty_points += v["points"]
            total_earned_points += a["points"]
            items.append(
                {
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "dormitory_id": user.dormitory_id,
                    "dormitory_name": user.dormitory.name if user.dormitory else None,
                    "room_id": user.room_id,
                    "room_number": user.room.room_number if user.room else None,
                    "total_points": max(0, 100 + a["points"] - v["points"]),
                    "violation_count": v["count"],
                    "penalty_points": v["points"],
                    "activity_count": a["count"],
                    "earned_points": a["points"],
                }
            )
        return {
            "items": items,
            "total_users": len(items),
            "total_violations": total_violations,
            "total_penalty_points": total_penalty_points,
            "total_earned_points": total_earned_points,
        }

    def report_payments(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        payments_section = self.dashboard_service._build_payments_section(current_user, dormitory_id, None, None)
        return payments_section

    def report_service_requests(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self._service_requests_base_query()
        if scoped_dormitory_id is not None:
            query = query.join(ServiceRequest.student).filter(
                or_(
                    ServiceRequest.dormitory_id == scoped_dormitory_id,
                    and_(ServiceRequest.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        items = query.all()
        return {
            "total": len(items),
            "by_status": {status: sum(1 for item in items if item.status == status) for status in ALLOWED_REQUEST_STATUSES},
            "by_type": {request_type: sum(1 for item in items if item.request_type == request_type) for request_type in {"repair", "complaint", "request"}},
        }

    def report_market(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        market_section = self.dashboard_service._build_market_section(current_user, dormitory_id, None, None)
        return market_section

    def report_calendar(self, current_user: User, dormitory_id: int | None = None) -> dict[str, Any]:
        self.permissions.ensure_permission(current_user, "can_view_reports")
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(CalendarEvent)
        if scoped_dormitory_id is not None:
            query = query.filter(or_(CalendarEvent.scope_type == "global", CalendarEvent.dormitory_id == scoped_dormitory_id))
        items = query.all()
        plans_query = self.db.query(KitchenDutyPlan)
        if scoped_dormitory_id is not None:
            plans_query = plans_query.filter(KitchenDutyPlan.dormitory_id == scoped_dormitory_id)
        plans = plans_query.all()
        event_kinds = sorted({item.event_kind for item in items})
        return {
            "total_events": len(items),
            "by_status": {status: sum(1 for item in items if item.status == status) for status in {"scheduled", "cancelled", "completed", "draft"}},
            "by_kind": {kind: sum(1 for item in items if item.event_kind == kind) for kind in event_kinds},
            "active_plans": sum(1 for item in plans if item.status == "generated"),
        }

    def _service_requests_base_query(self):
        return self.db.query(ServiceRequest).options(
            joinedload(ServiceRequest.student),
            joinedload(ServiceRequest.executor),
            joinedload(ServiceRequest.dormitory),
            joinedload(ServiceRequest.room),
            joinedload(ServiceRequest.comments).joinedload(ServiceRequestComment.author),
            joinedload(ServiceRequest.attachments).joinedload(ServiceRequestAttachment.uploaded_by),
        )

    def _get_service_request_or_404(self, request_id: int) -> ServiceRequest:
        item = self._service_requests_base_query().filter(ServiceRequest.id == request_id).first()
        if item is None:
            raise NotFoundError("Заявка", str(request_id))
        return item

    def _ensure_user_in_scope(self, current_user: User, target_user: User) -> None:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        if scoped_dormitory_id is not None and target_user.dormitory_id != scoped_dormitory_id:
            raise ForbiddenError("Пользователь находится вне вашего общежития")

    def _ensure_service_request_in_scope(self, current_user: User, item: ServiceRequest) -> None:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        if scoped_dormitory_id is None:
            return
        target_dormitory_id = item.dormitory_id or (item.student.dormitory_id if item.student else None)
        if target_dormitory_id != scoped_dormitory_id:
            raise ForbiddenError("Заявка относится к другому общежитию")

    def _serialize_service_request(self, item: ServiceRequest, *, include_relations: bool = False) -> dict[str, Any]:
        payload = {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "request_type": item.request_type,
            "status": item.status,
            "student_id": item.student_id,
            "student_name": item.student.full_name if item.student else None,
            "executor_id": item.executor_id,
            "executor_name": item.executor.full_name if item.executor else None,
            "dormitory_id": item.dormitory_id,
            "dormitory_name": item.dormitory.name if item.dormitory else None,
            "room_id": item.room_id,
            "room_number": item.room.room_number if item.room else None,
            "resolution_comment": item.resolution_comment,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "closed_at": item.closed_at.isoformat() if item.closed_at else None,
            "comments_count": len(item.comments),
            "attachments_count": len(item.attachments),
        }
        if include_relations:
            payload["comments"] = [
                {
                    "id": comment.id,
                    "author_id": comment.author_id,
                    "author_name": comment.author.full_name if comment.author else None,
                    "comment": comment.comment,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                }
                for comment in sorted(item.comments, key=lambda value: value.created_at or datetime.min)
            ]
            payload["attachments"] = [
                {
                    "id": attachment.id,
                    "file_name": attachment.file_name,
                    "file_url": attachment.file_url,
                    "uploaded_by_id": attachment.uploaded_by_id,
                    "uploaded_by_name": attachment.uploaded_by.full_name if attachment.uploaded_by else None,
                    "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
                }
                for attachment in sorted(item.attachments, key=lambda value: value.created_at or datetime.min)
            ]
        return payload

