from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.db.models import CalendarEvent, Event, News, Payment, Product, RentalListing, Room, ServiceRequest, User
from api.services.admin_permissions_service import AdminPermissionsService


SEARCHABLE_TYPES = {
    "user",
    "room",
    "service_request",
    "payment",
    "product",
    "rental",
    "news",
    "event",
    "calendar_event",
}


class AdminSearchService:
    def __init__(self, db: Session):
        self.db = db
        self.permissions = AdminPermissionsService()

    def search(
        self,
        current_user: User,
        *,
        query: str,
        types: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.permissions.ensure_admin_shell_access(current_user)
        clean_query = query.strip()
        if not clean_query:
            return {"query": clean_query, "items": []}

        requested_types = [item for item in (types or list(SEARCHABLE_TYPES)) if item in SEARCHABLE_TYPES]
        allowed_types = self._allowed_types(current_user)
        requested_types = [item for item in requested_types if item in allowed_types]

        results: list[dict[str, Any]] = []
        for search_type in requested_types:
            results.extend(self._search_type(current_user, search_type, clean_query, limit))

        results = results[:limit]
        return {"query": clean_query, "items": results}

    def _allowed_types(self, current_user: User) -> set[str]:
        permissions = self.permissions.permissions_for(current_user)
        allowed: set[str] = set()
        if permissions.get("can_manage_users"):
            allowed.update({"user", "room"})
        if permissions.get("can_manage_requests"):
            allowed.add("service_request")
        if permissions.get("can_manage_payments"):
            allowed.add("payment")
        if permissions.get("can_manage_market"):
            allowed.update({"product", "rental"})
        if permissions.get("can_manage_news"):
            allowed.add("news")
        if permissions.get("can_manage_events"):
            allowed.add("event")
        if permissions.get("can_manage_calendar"):
            allowed.add("calendar_event")
        return allowed

    def _search_type(self, current_user: User, search_type: str, query: str, limit: int) -> list[dict[str, Any]]:
        handlers = {
            "user": self._search_users,
            "room": self._search_rooms,
            "service_request": self._search_service_requests,
            "payment": self._search_payments,
            "product": self._search_products,
            "rental": self._search_rentals,
            "news": self._search_news,
            "event": self._search_events,
            "calendar_event": self._search_calendar_events,
        }
        return handlers[search_type](current_user, query, limit)

    def _search_users(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(User)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(User.dormitory_id == scoped_dormitory_id)
        users = (
            db_query.filter(or_(User.student_card.ilike(pattern), User.full_name.ilike(pattern)))
            .order_by(User.full_name)
            .limit(limit)
            .all()
        )
        return [
            {
                "type": "user",
                "id": item.id,
                "title": f"{item.student_card} — {item.full_name}",
                "subtitle": (
                    f"{item.dormitory.name if item.dormitory else 'Без общежития'}"
                    f"{f', комната {item.room.room_number}' if item.room else ''}"
                ),
                "route": f"/admin/users/{item.id}",
            }
            for item in users
        ]

    def _search_rooms(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(Room)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(Room.dormitory_id == scoped_dormitory_id)
        rooms = db_query.filter(Room.room_number.cast(str).ilike(pattern)).order_by(Room.room_number).limit(limit).all()
        return [
            {
                "type": "room",
                "id": item.id,
                "title": f"Комната {item.room_number}",
                "subtitle": item.dormitory.name if item.dormitory else "Без общежития",
                "route": f"/admin/residence?room_id={item.id}",
            }
            for item in rooms
        ]

    def _search_service_requests(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(ServiceRequest).join(ServiceRequest.student)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(
                or_(
                    ServiceRequest.dormitory_id == scoped_dormitory_id,
                    and_(ServiceRequest.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        items = (
            db_query.filter(or_(ServiceRequest.title.ilike(pattern), ServiceRequest.description.ilike(pattern)))
            .order_by(ServiceRequest.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "type": "service_request",
                "id": item.id,
                "title": f"Заявка #{item.id} — {item.title}",
                "subtitle": f"{item.status} • {item.student.full_name if item.student else 'Unknown'}",
                "route": f"/admin/requests/{item.id}",
            }
            for item in items
        ]

    def _search_payments(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(Payment).join(Payment.user)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(
                or_(
                    Payment.dormitory_id == scoped_dormitory_id,
                    and_(Payment.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        items = (
            db_query.filter(or_(Payment.description.ilike(pattern), Payment.admin_comment.ilike(pattern)))
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "type": "payment",
                "id": item.id,
                "title": f"Счёт #{item.id}",
                "subtitle": f"{float(item.amount or 0):.2f} ₽ • {item.status}",
                "route": f"/admin/payments/{item.id}",
            }
            for item in items
        ]

    def _search_products(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(Product).join(Product.seller)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(
                or_(
                    Product.dormitory_id == scoped_dormitory_id,
                    and_(Product.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        items = db_query.filter(Product.title.ilike(pattern)).order_by(Product.created_at.desc()).limit(limit).all()
        return [
            {
                "type": "product",
                "id": item.id,
                "title": item.title,
                "subtitle": f"{float(item.price or 0):.2f} ₽ • {item.status}",
                "route": f"/admin/market/products/{item.id}",
            }
            for item in items
        ]

    def _search_rentals(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(RentalListing).join(RentalListing.owner)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(
                or_(
                    RentalListing.dormitory_id == scoped_dormitory_id,
                    and_(RentalListing.dormitory_id.is_(None), User.dormitory_id == scoped_dormitory_id),
                )
            )
        items = db_query.filter(RentalListing.title.ilike(pattern)).order_by(RentalListing.created_at.desc()).limit(limit).all()
        return [
            {
                "type": "rental",
                "id": item.id,
                "title": item.title,
                "subtitle": f"{float(item.daily_price or 0):.2f} ₽/день • {item.status}",
                "route": f"/admin/market/rentals/{item.id}",
            }
            for item in items
        ]

    def _search_news(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(News)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(or_(News.dormitory_id == scoped_dormitory_id, News.dormitory_id.is_(None)))
        items = db_query.filter(News.title.ilike(pattern)).order_by(News.created_at.desc()).limit(limit).all()
        return [
            {
                "type": "news",
                "id": item.id,
                "title": item.title,
                "subtitle": item.content[:80],
                "route": f"/admin/news/{item.id}",
            }
            for item in items
        ]

    def _search_events(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(Event)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(or_(Event.dormitory_id == scoped_dormitory_id, Event.dormitory_id.is_(None)))
        items = db_query.filter(Event.title.ilike(pattern)).order_by(Event.created_at.desc()).limit(limit).all()
        return [
            {
                "type": "event",
                "id": item.id,
                "title": item.title,
                "subtitle": item.location,
                "route": f"/admin/events/{item.id}",
            }
            for item in items
        ]

    def _search_calendar_events(self, current_user: User, query: str, limit: int) -> list[dict[str, Any]]:
        scoped_dormitory_id = self.permissions.scoped_dormitory_id(current_user)
        pattern = f"%{query}%"
        db_query = self.db.query(CalendarEvent)
        if scoped_dormitory_id is not None:
            db_query = db_query.filter(
                or_(
                    CalendarEvent.scope_type == "global",
                    CalendarEvent.dormitory_id == scoped_dormitory_id,
                )
            )
        items = db_query.filter(CalendarEvent.title.ilike(pattern)).order_by(CalendarEvent.created_at.desc()).limit(limit).all()
        return [
            {
                "type": "calendar_event",
                "id": item.id,
                "title": item.title,
                "subtitle": item.event_kind,
                "route": f"/admin/calendar/{item.id}",
            }
            for item in items
        ]
