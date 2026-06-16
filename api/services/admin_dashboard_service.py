from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from api.db.models import (
    ActionLog,
    CalendarEvent,
    CleanlinessHistory,
    KitchenDutyPlan,
    Payment,
    PaymentTopUp,
    Product,
    RentalBooking,
    RentalListing,
    Room,
    ServiceRequest,
    User,
    UserActivity,
    UserViolation,
)
from api.services.admin_permissions_service import AdminPermissionsService


class AdminDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.permissions = AdminPermissionsService()

    def get_bootstrap(self, current_user: User) -> dict[str, Any]:
        self.permissions.ensure_admin_shell_access(current_user)
        counters = self._build_counters(current_user)
        permissions = self.permissions.permissions_for(current_user)
        scope = self.permissions.scope_for(current_user)
        return {
            "me": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "student_card": current_user.student_card,
                "role_name": current_user.role.role_name if current_user.role else None,
            },
            "role": current_user.role.role_name if current_user.role else None,
            "scope": {
                "mode": scope.mode,
                "dormitory_id": scope.dormitory_id,
                "dormitory_name": scope.dormitory_name,
            },
            "permissions": permissions,
            "modules": self.permissions.build_modules(current_user, counters),
            "counters": counters,
            "feature_flags": {
                "payments_v2_enabled": True,
                "calendar_enabled": True,
                "notifications_enabled": True,
                "reports_enabled": True,
            },
            "dashboard_preview": self._build_dashboard_preview(current_user),
        }

    def get_dashboard(
        self,
        current_user: User,
        *,
        dormitory_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        self.permissions.ensure_admin_shell_access(current_user)
        permissions = self.permissions.permissions_for(current_user)

        occupancy = self._build_occupancy_section(current_user, dormitory_id) if permissions.get("can_manage_residence") or permissions.get("can_view_reports") else None
        service_requests = self._build_service_requests_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_requests") else None
        payments = self._build_payments_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_payments") else None
        market = self._build_market_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_market") else None
        calendar = self._build_calendar_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_calendar") else None
        discipline = self._build_discipline_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_discipline") or permissions.get("can_view_reports") else None
        cleanliness = self._build_cleanliness_section(current_user, dormitory_id, date_from, date_to) if permissions.get("can_manage_cleanliness") else None
        activity_feed = self.get_activity_feed(current_user, dormitory_id=dormitory_id)

        return {
            "occupancy": occupancy,
            "service_requests": service_requests,
            "payments": payments,
            "market": market,
            "calendar": calendar,
            "discipline": discipline,
            "cleanliness": cleanliness,
            "activity_feed": activity_feed["items"],
        }

    def get_activity_feed(
        self,
        current_user: User,
        *,
        dormitory_id: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.permissions.ensure_admin_shell_access(current_user)
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(ActionLog).options(joinedload(ActionLog.user))
        if scoped_dormitory_id is not None:
            query = query.join(ActionLog.user).filter(User.dormitory_id == scoped_dormitory_id)
        items = query.order_by(desc(ActionLog.created_at)).limit(limit).all()
        serialized = [
            {
                "id": item.id,
                "action": item.action_type,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "description": item.description,
                "performed_by": item.user.full_name if item.user else "Unknown",
                "performed_by_id": item.user_id,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        return {"items": serialized, "total": len(serialized)}

    def _build_dashboard_preview(self, current_user: User) -> dict[str, Any]:
        occupancy = self._build_occupancy_section(current_user, None)
        service_requests = self._build_service_requests_section(current_user, None, None, None)
        payments = self._build_payments_section(current_user, None, None, None)
        return {
            "occupancy_percent": occupancy["occupancy_percent"],
            "open_requests": service_requests["open_requests"],
            "unpaid_amount": payments["pending_amount"],
        }

    def _build_counters(self, current_user: User) -> dict[str, int]:
        service_requests = self._build_service_requests_section(current_user, None, None, None)
        payments = self._build_payments_section(current_user, None, None, None)
        market = self._build_market_section(current_user, None, None, None)
        calendar = self._build_calendar_section(current_user, None, None, None)
        discipline = self._build_discipline_section(current_user, None, None, None)
        cleanliness = self._build_cleanliness_section(current_user, None, None, None)
        return {
            "new_requests": int(service_requests["new"]),
            "overdue_invoices": int(payments["overdue_count"]),
            "pending_top_ups": int(payments["top_up_pending_count"]),
            "products_on_moderation": int(market["products_pending"]),
            "rentals_on_moderation": int(market["rentals_pending"]),
            "upcoming_calendar_events": int(calendar["upcoming_events"]),
            "new_violations": int(discipline["new_violations"]),
            "rooms_below_threshold": int(cleanliness["rooms_below_threshold"]),
        }

    def _build_occupancy_section(self, current_user: User, dormitory_id: int | None) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        rooms_query = self.db.query(Room)
        users_query = self.db.query(User).filter(User.room_id.is_not(None))
        if scoped_dormitory_id is not None:
            rooms_query = rooms_query.filter(Room.dormitory_id == scoped_dormitory_id)
            users_query = users_query.filter(User.dormitory_id == scoped_dormitory_id)

        rooms = rooms_query.all()
        total_rooms = len(rooms)
        total_places = sum(int(room.capacity or 0) for room in rooms)
        occupied_places = users_query.count()
        free_places = max(total_places - occupied_places, 0)
        occupancy_percent = round((occupied_places / total_places) * 100, 2) if total_places else 0.0

        return {
            "total_rooms": total_rooms,
            "total_places": total_places,
            "occupied_places": occupied_places,
            "free_places": free_places,
            "occupancy_percent": occupancy_percent,
        }

    def _build_service_requests_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(ServiceRequest).join(ServiceRequest.student)
        if scoped_dormitory_id is not None:
            query = query.filter(
                or_(
                    ServiceRequest.dormitory_id == scoped_dormitory_id,
                    and_(ServiceRequest.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if date_from is not None:
            query = query.filter(ServiceRequest.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            query = query.filter(ServiceRequest.created_at <= datetime.combine(date_to, datetime.max.time()))

        items = query.all()
        resolved_recent_threshold = datetime.utcnow() - timedelta(days=30)
        return {
            "new": sum(1 for item in items if item.status == "new"),
            "in_progress": sum(1 for item in items if item.status == "in_progress"),
            "resolved_recent": sum(1 for item in items if item.status == "resolved" and item.updated_at and item.updated_at >= resolved_recent_threshold),
            "rejected": sum(1 for item in items if item.status == "rejected"),
            "closed": sum(1 for item in items if item.status == "closed"),
            "open_requests": sum(1 for item in items if item.status in {"new", "in_progress"}),
            "total": len(items),
        }

    def _build_payments_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        invoice_query = self.db.query(Payment).join(Payment.user)
        if scoped_dormitory_id is not None:
            invoice_query = invoice_query.filter(
                or_(
                    Payment.dormitory_id == scoped_dormitory_id,
                    and_(Payment.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if date_from is not None:
            invoice_query = invoice_query.filter(Payment.period_end >= date_from)
        if date_to is not None:
            invoice_query = invoice_query.filter(Payment.period_start <= date_to)
        invoices = invoice_query.all()

        top_up_query = self.db.query(PaymentTopUp).join(PaymentTopUp.user)
        if scoped_dormitory_id is not None:
            top_up_query = top_up_query.filter(User.dormitory_id == scoped_dormitory_id)
        if date_from is not None:
            top_up_query = top_up_query.filter(PaymentTopUp.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            top_up_query = top_up_query.filter(PaymentTopUp.created_at <= datetime.combine(date_to, datetime.max.time()))
        top_ups = top_up_query.all()

        pending_amount = round(
            sum(float(item.amount or 0) for item in invoices if item.status in {"pending", "overdue", "partially_paid"}),
            2,
        )
        overdue_amount = round(
            sum(float(item.amount or 0) for item in invoices if item.status == "overdue"),
            2,
        )

        return {
            "pending_count": sum(1 for item in invoices if item.status in {"pending", "partially_paid"}),
            "overdue_count": sum(1 for item in invoices if item.status == "overdue"),
            "paid_count": sum(1 for item in invoices if item.status == "paid"),
            "pending_amount": pending_amount,
            "overdue_amount": overdue_amount,
            "top_up_pending_count": sum(1 for item in top_ups if item.status == "submitted"),
            "top_up_confirmed_amount": round(sum(float(item.amount or 0) for item in top_ups if item.status == "confirmed"), 2),
        }

    def _build_market_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)

        product_query = self.db.query(Product).join(Product.seller)
        if scoped_dormitory_id is not None:
            product_query = product_query.filter(
                or_(
                    Product.dormitory_id == scoped_dormitory_id,
                    and_(Product.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if date_from is not None:
            product_query = product_query.filter(Product.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            product_query = product_query.filter(Product.created_at <= datetime.combine(date_to, datetime.max.time()))
        products = product_query.all()

        rental_query = self.db.query(RentalListing).join(RentalListing.owner)
        if scoped_dormitory_id is not None:
            rental_query = rental_query.filter(
                or_(
                    RentalListing.dormitory_id == scoped_dormitory_id,
                    and_(RentalListing.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        if date_from is not None:
            rental_query = rental_query.filter(RentalListing.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            rental_query = rental_query.filter(RentalListing.created_at <= datetime.combine(date_to, datetime.max.time()))
        rentals = rental_query.all()

        booking_query = self.db.query(RentalBooking).join(RentalBooking.listing)
        if scoped_dormitory_id is not None:
            booking_query = booking_query.filter(RentalListing.dormitory_id == scoped_dormitory_id)
        if date_from is not None:
            booking_query = booking_query.filter(RentalBooking.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            booking_query = booking_query.filter(RentalBooking.created_at <= datetime.combine(date_to, datetime.max.time()))
        bookings = booking_query.all()

        return {
            "products_pending": sum(1 for item in products if item.status == "pending"),
            "products_rejected": sum(1 for item in products if item.status == "rejected"),
            "rentals_pending": sum(1 for item in rentals if item.status == "pending"),
            "rentals_active": sum(1 for item in rentals if item.listing_status == "active"),
            "bookings_pending": sum(1 for item in bookings if item.status == "pending"),
        }

    def _build_calendar_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        now = datetime.utcnow()

        event_query = self.db.query(CalendarEvent)
        if scoped_dormitory_id is not None:
            event_query = event_query.filter(
                or_(
                    CalendarEvent.scope_type == "global",
                    CalendarEvent.dormitory_id == scoped_dormitory_id,
                )
            )
        if date_from is not None:
            event_query = event_query.filter(CalendarEvent.end_at >= datetime.combine(date_from, datetime.min.time()))
        else:
            event_query = event_query.filter(CalendarEvent.end_at >= now)
        if date_to is not None:
            event_query = event_query.filter(CalendarEvent.start_at <= datetime.combine(date_to, datetime.max.time()))

        events = event_query.all()

        plans_query = self.db.query(KitchenDutyPlan)
        if scoped_dormitory_id is not None:
            plans_query = plans_query.filter(KitchenDutyPlan.dormitory_id == scoped_dormitory_id)
        plans = plans_query.all()

        return {
            "upcoming_events": sum(1 for item in events if item.status == "scheduled"),
            "upcoming_duties": sum(1 for item in events if item.status == "scheduled" and item.event_kind == "kitchen_duty"),
            "cancelled_events": sum(1 for item in events if item.status == "cancelled"),
            "active_plans": sum(1 for item in plans if item.status == "generated"),
        }

    def _build_discipline_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        violation_query = self.db.query(UserViolation).join(UserViolation.user)
        activity_query = self.db.query(UserActivity).join(UserActivity.user)
        if scoped_dormitory_id is not None:
            violation_query = violation_query.filter(User.dormitory_id == scoped_dormitory_id)
            activity_query = activity_query.filter(User.dormitory_id == scoped_dormitory_id)
        if date_from is not None:
            violation_query = violation_query.filter(UserViolation.violation_date >= datetime.combine(date_from, datetime.min.time()))
            activity_query = activity_query.filter(UserActivity.activity_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            violation_query = violation_query.filter(UserViolation.violation_date <= datetime.combine(date_to, datetime.max.time()))
            activity_query = activity_query.filter(UserActivity.activity_date <= datetime.combine(date_to, datetime.max.time()))

        new_violations = violation_query.count()
        recent_activities = activity_query.count()

        top_rooms_query = (
            self.db.query(
                Room.id.label("room_id"),
                Room.room_number.label("room_number"),
                func.count(UserViolation.id).label("violations_count"),
            )
            .join(User, User.room_id == Room.id)
            .join(UserViolation, UserViolation.user_id == User.id)
            .group_by(Room.id, Room.room_number)
            .order_by(desc("violations_count"))
        )
        if scoped_dormitory_id is not None:
            top_rooms_query = top_rooms_query.filter(Room.dormitory_id == scoped_dormitory_id)

        top_problem_rooms = [
            {
                "room_id": row.room_id,
                "room_number": row.room_number,
                "violations_count": int(row.violations_count),
            }
            for row in top_rooms_query.limit(5).all()
        ]

        return {
            "new_violations": new_violations,
            "activities_recent": recent_activities,
            "top_problem_rooms": top_problem_rooms,
        }

    def _build_cleanliness_section(
        self,
        current_user: User,
        dormitory_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user, dormitory_id)
        query = self.db.query(CleanlinessHistory).options(
            joinedload(CleanlinessHistory.room),
            joinedload(CleanlinessHistory.assigned_by_user),
        )
        if scoped_dormitory_id is not None:
            query = query.join(CleanlinessHistory.room).filter(Room.dormitory_id == scoped_dormitory_id)
        if date_from is not None:
            query = query.filter(CleanlinessHistory.assigned_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            query = query.filter(CleanlinessHistory.assigned_at <= datetime.combine(date_to, datetime.max.time()))

        latest_checks_raw = query.order_by(desc(CleanlinessHistory.assigned_at)).limit(5).all()
        latest_checks = [
            {
                "id": item.id,
                "room_id": item.room_id,
                "room_number": item.room.room_number if item.room else None,
                "score": item.score,
                "assigned_by": item.assigned_by_user.full_name if item.assigned_by_user else None,
                "assigned_at": item.assigned_at.isoformat() if item.assigned_at else None,
            }
            for item in latest_checks_raw
        ]

        rooms_below_threshold = (
            query.filter(CleanlinessHistory.score < 3)
            .with_entities(func.count(func.distinct(CleanlinessHistory.room_id)))
            .scalar()
            or 0
        )

        return {
            "latest_checks": latest_checks,
            "rooms_below_threshold": int(rooms_below_threshold),
        }
