from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from api.core.exceptions import (
    ConflictError,
    DatabaseError,
    DormitoryNotFoundError,
    InsufficientPermissionsError,
    NotFoundError,
    RoomNotFoundError,
    ValidationError,
)
from api.db.models import (
    CalendarEvent,
    Dormitory,
    DormitoryBlock,
    DormitoryBlockRoom,
    KitchenDutyAssignment,
    KitchenDutyPlan,
    News,
    Room,
    User,
)
from api.repositories.calendar_event import CalendarEventRepository
from api.repositories.dormitory_block import DormitoryBlockRepository
from api.repositories.kitchen_duty_plan import KitchenDutyPlanRepository
from api.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    DormitoryBlockCreate,
    DormitoryBlockUpdate,
    KitchenDutyPlanCreate,
)
from api.services.user_helpers import user_has_role


ALLOWED_EVENT_KINDS = {
    "repair",
    "water_outage",
    "kitchen_duty",
    "community_work",
    "inspection",
    "other",
}
ALLOWED_SCOPE_TYPES = {"global", "dormitory", "block", "room"}
ALLOWED_STATUSES = {"scheduled", "cancelled", "completed", "draft"}
ALLOWED_SOURCE_TYPES = {"manual", "duty_generated", "news_generated", "event_generated"}
MANAGE_CALENDAR_ROLES = ("admin", "commandant", "council_president", "council_member")
MANAGE_BLOCK_ROLES = ("admin", "commandant")


class CalendarService:
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = CalendarEventRepository(db)
        self.block_repo = DormitoryBlockRepository(db)
        self.plan_repo = KitchenDutyPlanRepository(db)

    def list_events(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_kind: str | None = None,
        status: str | None = None,
        scope_type: str | None = None,
        dormitory_id: int | None = None,
        block_id: int | None = None,
        room_id: int | None = None,
    ) -> dict[str, Any]:
        self._validate_optional_event_filters(event_kind, status, scope_type)
        user_block_id = self._resolve_user_block_id(current_user.room_id)
        can_view_all = self._can_manage_calendar(current_user)
        skip = (page - 1) * page_size
        items = self.event_repo.list_filtered(
            skip=skip,
            limit=page_size,
            can_view_all=can_view_all,
            user_dormitory_id=current_user.dormitory_id,
            user_block_id=user_block_id,
            user_room_id=current_user.room_id,
            date_from=date_from,
            date_to=date_to,
            event_kind=event_kind,
            status=status,
            scope_type=scope_type,
            dormitory_id=dormitory_id if can_view_all else None,
            block_id=block_id if can_view_all else None,
            room_id=room_id if can_view_all else None,
        )
        total = self.event_repo.count_filtered(
            can_view_all=can_view_all,
            user_dormitory_id=current_user.dormitory_id,
            user_block_id=user_block_id,
            user_room_id=current_user.room_id,
            date_from=date_from,
            date_to=date_to,
            event_kind=event_kind,
            status=status,
            scope_type=scope_type,
            dormitory_id=dormitory_id if can_view_all else None,
            block_id=block_id if can_view_all else None,
            room_id=room_id if can_view_all else None,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": [self._serialize_event(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "meta": {
                "user_dormitory_id": current_user.dormitory_id,
                "user_block_id": user_block_id,
                "user_room_id": current_user.room_id,
            },
        }

    def get_event_detail(self, *, current_user: User, event_id: int) -> dict[str, Any]:
        event = self._get_event_or_404(event_id)
        self._ensure_event_visible_for_user(event, current_user)
        return self._serialize_event(event)

    def get_my_duty(
        self,
        *,
        current_user: User,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        if current_user.room_id is None:
            return {"items": [], "total": 0}
        events = self.event_repo.list_my_duty(
            room_id=current_user.room_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        items = [self._serialize_event(item) for item in events if item.status != "draft"]
        return {"items": items, "total": len(items)}

    def get_month_view(
        self,
        *,
        current_user: User,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        month_end = next_month - timedelta(days=1)
        date_from = datetime.combine(month_start, time.min)
        date_to = datetime.combine(month_end, time.max)

        listing = self.list_events(
            current_user=current_user,
            page=1,
            page_size=500,
            date_from=date_from,
            date_to=date_to,
        )
        items = listing["items"]
        dates_with_events = sorted({item["start_at"].date().isoformat() for item in items})
        nearest_duty_payload = self.get_my_duty(
            current_user=current_user,
            date_from=date_from,
            date_to=date_to,
            limit=1,
        )
        return {
            "year": year,
            "month": month,
            "items": items,
            "dates_with_events": dates_with_events,
            "nearest_duty": nearest_duty_payload["items"][0] if nearest_duty_payload["items"] else None,
        }

    def create_event(self, *, current_user: User, data: CalendarEventCreate) -> dict[str, Any]:
        self._require_manage_calendar(current_user)
        self._validate_event_payload(data)
        scope = self._resolve_scope_entities(
            scope_type=data.scope_type,
            dormitory_id=data.dormitory_id,
            block_id=data.block_id,
            room_id=data.room_id,
            related_news_id=data.related_news_id,
        )
        event = CalendarEvent(
            title=data.title.strip(),
            description=data.description.strip(),
            event_kind=data.event_kind,
            scope_type=data.scope_type,
            status=data.status,
            start_at=data.start_at,
            end_at=data.end_at,
            is_all_day=data.is_all_day,
            location=data.location.strip() if data.location else None,
            dormitory_id=scope["dormitory_id"],
            block_id=scope["block_id"],
            room_id=scope["room_id"],
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
            related_news_id=scope["related_news_id"],
            source_type="manual",
            metadata_json=data.metadata_json or None,
        )
        try:
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_event(self._get_event_or_404(event.id))

    def update_event(
        self,
        *,
        current_user: User,
        event_id: int,
        data: CalendarEventUpdate,
    ) -> dict[str, Any]:
        self._require_manage_calendar(current_user)
        event = self._get_event_or_404(event_id)
        payload = data.model_dump(exclude_unset=True)
        if not payload:
            return self._serialize_event(event)

        merged = {
            "title": payload.get("title", event.title),
            "description": payload.get("description", event.description),
            "event_kind": payload.get("event_kind", event.event_kind),
            "scope_type": payload.get("scope_type", event.scope_type),
            "status": payload.get("status", event.status),
            "start_at": payload.get("start_at", event.start_at),
            "end_at": payload.get("end_at", event.end_at),
            "is_all_day": payload.get("is_all_day", event.is_all_day),
            "location": payload.get("location", event.location),
            "dormitory_id": payload.get("dormitory_id", event.dormitory_id),
            "block_id": payload.get("block_id", event.block_id),
            "room_id": payload.get("room_id", event.room_id),
            "related_news_id": payload.get("related_news_id", event.related_news_id),
            "metadata_json": payload.get("metadata_json", event.metadata_json),
        }
        normalized_data = CalendarEventCreate(**merged)
        self._validate_event_payload(normalized_data)
        scope = self._resolve_scope_entities(
            scope_type=normalized_data.scope_type,
            dormitory_id=normalized_data.dormitory_id,
            block_id=normalized_data.block_id,
            room_id=normalized_data.room_id,
            related_news_id=normalized_data.related_news_id,
        )
        event.title = normalized_data.title.strip()
        event.description = normalized_data.description.strip()
        event.event_kind = normalized_data.event_kind
        event.scope_type = normalized_data.scope_type
        event.status = normalized_data.status
        event.start_at = normalized_data.start_at
        event.end_at = normalized_data.end_at
        event.is_all_day = normalized_data.is_all_day
        event.location = normalized_data.location.strip() if normalized_data.location else None
        event.dormitory_id = scope["dormitory_id"]
        event.block_id = scope["block_id"]
        event.room_id = scope["room_id"]
        event.related_news_id = scope["related_news_id"]
        event.metadata_json = normalized_data.metadata_json or None
        event.updated_by_id = current_user.id
        try:
            self.db.commit()
            self.db.refresh(event)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_event(self._get_event_or_404(event.id))

    def cancel_event(
        self,
        *,
        current_user: User,
        event_id: int,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._require_manage_calendar(current_user)
        event = self._get_event_or_404(event_id)
        event.status = "cancelled"
        metadata = dict(event.metadata_json or {})
        if reason:
            metadata["cancel_reason"] = reason
        event.metadata_json = metadata or None
        event.updated_by_id = current_user.id
        try:
            self.db.commit()
            self.db.refresh(event)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_event(event)

    def list_blocks(
        self,
        *,
        current_user: User,
        dormitory_id: int | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        blocks = self.block_repo.list_filtered(dormitory_id=dormitory_id, is_active=is_active)
        return {"items": [self._serialize_block(item, include_rooms=True) for item in blocks], "total": len(blocks)}

    def create_block(self, *, current_user: User, data: DormitoryBlockCreate) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        dormitory = self.db.query(Dormitory).filter(Dormitory.id == data.dormitory_id).first()
        if dormitory is None:
            raise DormitoryNotFoundError(data.dormitory_id)
        block = DormitoryBlock(
            dormitory_id=data.dormitory_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            kitchen_label=data.kitchen_label.strip() if data.kitchen_label else None,
        )
        try:
            self.db.add(block)
            self.db.commit()
            self.db.refresh(block)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_block(self.block_repo.get_with_relations(block.id))

    def update_block(
        self,
        *,
        current_user: User,
        block_id: int,
        data: DormitoryBlockUpdate,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        block = self._get_block_or_404(block_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"] is not None:
            block.name = payload["name"].strip()
        if "description" in payload:
            block.description = payload["description"].strip() if payload["description"] else None
        if "kitchen_label" in payload:
            block.kitchen_label = payload["kitchen_label"].strip() if payload["kitchen_label"] else None
        if "is_active" in payload:
            block.is_active = payload["is_active"]
        try:
            self.db.commit()
            self.db.refresh(block)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_block(self.block_repo.get_with_relations(block.id))

    def add_room_to_block(
        self,
        *,
        current_user: User,
        block_id: int,
        room_id: int,
        rotation_order: int,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        block = self._get_block_or_404(block_id)
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if room is None:
            raise RoomNotFoundError(room_id)
        if room.dormitory_id != block.dormitory_id:
            raise ValidationError("Комната принадлежит другому общежитию и не может быть привязана к этому блоку")
        if self.block_repo.get_room_link(block_id, room_id):
            raise ConflictError("Комната уже привязана к этому блоку")
        existing_binding = self.block_repo.get_room_binding(room_id)
        if existing_binding:
            raise ConflictError("Комната уже привязана к другому блоку")
        link = DormitoryBlockRoom(
            block_id=block_id,
            room_id=room_id,
            rotation_order=rotation_order,
        )
        try:
            self.db.add(link)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_block(self.block_repo.get_with_relations(block_id))

    def update_block_room(
        self,
        *,
        current_user: User,
        block_id: int,
        room_id: int,
        rotation_order: int,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        link = self.block_repo.get_room_link(block_id, room_id)
        if link is None:
            raise NotFoundError("Привязка комнаты к блоку")
        link.rotation_order = rotation_order
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_block(self.block_repo.get_with_relations(block_id))

    def remove_room_from_block(
        self,
        *,
        current_user: User,
        block_id: int,
        room_id: int,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        link = self.block_repo.get_room_link(block_id, room_id)
        if link is None:
            raise NotFoundError("Привязка комнаты к блоку")
        try:
            self.db.delete(link)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return {"success": True, "block_id": block_id, "room_id": room_id}

    def create_duty_plan(
        self,
        *,
        current_user: User,
        data: KitchenDutyPlanCreate,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        self._validate_plan_dates(data.month_start, data.month_end)
        dormitory = self.db.query(Dormitory).filter(Dormitory.id == data.dormitory_id).first()
        if dormitory is None:
            raise DormitoryNotFoundError(data.dormitory_id)
        block = self._get_block_or_404(data.block_id)
        if block.dormitory_id != data.dormitory_id:
            raise ValidationError("Блок не принадлежит указанному общежитию")
        plan = KitchenDutyPlan(
            dormitory_id=data.dormitory_id,
            block_id=data.block_id,
            month_start=data.month_start,
            month_end=data.month_end,
            status="draft",
            created_by_id=current_user.id,
            comment=data.comment.strip() if data.comment else None,
        )
        try:
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_plan(self.plan_repo.get_with_relations(plan.id), include_details=True)

    def generate_duty_plan(
        self,
        *,
        current_user: User,
        plan_id: int,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        plan = self._get_plan_or_404(plan_id)
        if plan.status == "generated":
            raise ConflictError("План уже сгенерирован")
        room_links = self.block_repo.list_ordered_rooms(plan.block_id)
        if not room_links:
            raise ValidationError("Для блока не задан список комнат для дежурств")
        if plan.assignments:
            raise ConflictError("У плана уже есть назначения, повторная генерация недоступна")

        current_date = plan.month_start
        room_index = 0
        created_assignments: list[KitchenDutyAssignment] = []
        while current_date <= plan.month_end:
            room_link = room_links[room_index % len(room_links)]
            event = CalendarEvent(
                title=f"Дежурство по кухне: комната {room_link.room.room_number}",
                description=f"Комната {room_link.room.room_number} дежурит по кухне блока {plan.block.name}",
                event_kind="kitchen_duty",
                scope_type="room",
                status="scheduled",
                start_at=datetime.combine(current_date, time.min),
                end_at=datetime.combine(current_date, time.max),
                is_all_day=True,
                location=plan.block.kitchen_label or f"Кухня блока {plan.block.name}",
                dormitory_id=plan.dormitory_id,
                block_id=plan.block_id,
                room_id=room_link.room_id,
                created_by_id=current_user.id,
                updated_by_id=current_user.id,
                source_type="duty_generated",
                metadata_json={
                    "plan_id": plan.id,
                    "duty_order": room_index + 1,
                    "rotation_order": room_link.rotation_order,
                },
            )
            self.db.add(event)
            self.db.flush()

            assignment = KitchenDutyAssignment(
                plan_id=plan.id,
                calendar_event_id=event.id,
                room_id=room_link.room_id,
                duty_date=current_date,
                duty_order=room_index + 1,
            )
            self.db.add(assignment)
            created_assignments.append(assignment)

            current_date += timedelta(days=1)
            room_index += 1

        plan.status = "generated"
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_plan(self.plan_repo.get_with_relations(plan.id), include_details=True)

    def list_duty_plans(
        self,
        *,
        current_user: User,
        dormitory_id: int | None = None,
        block_id: int | None = None,
        month: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        plans = self.plan_repo.list_filtered(
            dormitory_id=dormitory_id,
            block_id=block_id,
            month=month,
            status=status,
        )
        return {"items": [self._serialize_plan(plan, include_details=False) for plan in plans], "total": len(plans)}

    def get_duty_plan_detail(self, *, current_user: User, plan_id: int) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        plan = self._get_plan_or_404(plan_id)
        return self._serialize_plan(plan, include_details=True)

    def cancel_duty_plan(self, *, current_user: User, plan_id: int) -> dict[str, Any]:
        self._require_manage_blocks(current_user)
        plan = self._get_plan_or_404(plan_id)
        plan.status = "cancelled"
        today = date.today()
        for assignment in plan.assignments:
            if assignment.duty_date >= today and assignment.calendar_event:
                assignment.calendar_event.status = "cancelled"
                assignment.calendar_event.updated_by_id = current_user.id
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError() from exc
        return self._serialize_plan(self.plan_repo.get_with_relations(plan.id), include_details=True)

    def _serialize_event(self, event: CalendarEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_kind": event.event_kind,
            "scope_type": event.scope_type,
            "status": event.status,
            "start_at": event.start_at,
            "end_at": event.end_at,
            "is_all_day": bool(event.is_all_day),
            "location": event.location,
            "dormitory_id": event.dormitory_id,
            "dormitory_name": event.dormitory.name if event.dormitory else None,
            "block_id": event.block_id,
            "block_name": event.block.name if event.block else None,
            "room_id": event.room_id,
            "room_number": event.room.room_number if event.room else None,
            "created_by_id": event.created_by_id,
            "created_by_name": event.created_by.full_name if event.created_by else None,
            "updated_by_id": event.updated_by_id,
            "updated_by_name": event.updated_by.full_name if event.updated_by else None,
            "related_news_id": event.related_news_id,
            "related_event_id": event.related_event_id,
            "source_type": event.source_type,
            "metadata_json": event.metadata_json or {},
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }

    def _serialize_block(self, block: DormitoryBlock, *, include_rooms: bool = True) -> dict[str, Any]:
        payload = {
            "id": block.id,
            "dormitory_id": block.dormitory_id,
            "dormitory_name": block.dormitory.name if block.dormitory else None,
            "name": block.name,
            "description": block.description,
            "kitchen_label": block.kitchen_label,
            "is_active": bool(block.is_active),
            "created_at": block.created_at,
            "updated_at": block.updated_at,
        }
        if include_rooms:
            rooms = sorted(block.block_rooms, key=lambda item: (item.rotation_order, item.id))
            payload["rooms"] = [
                {
                    "room_id": link.room_id,
                    "room_number": link.room.room_number if link.room else None,
                    "rotation_order": link.rotation_order,
                }
                for link in rooms
            ]
        return payload

    def _serialize_assignment(self, assignment: KitchenDutyAssignment) -> dict[str, Any]:
        return {
            "id": assignment.id,
            "room_id": assignment.room_id,
            "room_number": assignment.room.room_number if assignment.room else None,
            "duty_date": assignment.duty_date,
            "duty_order": assignment.duty_order,
            "calendar_event_id": assignment.calendar_event_id,
            "event_status": assignment.calendar_event.status if assignment.calendar_event else None,
        }

    def _serialize_plan(self, plan: KitchenDutyPlan, *, include_details: bool) -> dict[str, Any]:
        payload = {
            "id": plan.id,
            "dormitory_id": plan.dormitory_id,
            "dormitory_name": plan.dormitory.name if plan.dormitory else None,
            "block_id": plan.block_id,
            "block_name": plan.block.name if plan.block else None,
            "month_start": plan.month_start,
            "month_end": plan.month_end,
            "status": plan.status,
            "created_by_id": plan.created_by_id,
            "created_by_name": plan.created_by.full_name if plan.created_by else None,
            "comment": plan.comment,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }
        if include_details:
            room_links = self.block_repo.list_ordered_rooms(plan.block_id)
            assignments = sorted(plan.assignments, key=lambda item: (item.duty_date, item.id))
            payload["rooms"] = [
                {
                    "room_id": link.room_id,
                    "room_number": link.room.room_number if link.room else None,
                    "rotation_order": link.rotation_order,
                }
                for link in room_links
            ]
            payload["assignments"] = [self._serialize_assignment(item) for item in assignments]
            payload["events"] = [
                self._serialize_event(item.calendar_event)
                for item in assignments
                if item.calendar_event is not None
            ]
        return payload

    def _get_event_or_404(self, event_id: int) -> CalendarEvent:
        event = self.event_repo.get_with_relations(event_id)
        if event is None:
            raise NotFoundError("Календарное событие", event_id)
        return event

    def _get_block_or_404(self, block_id: int) -> DormitoryBlock:
        block = self.block_repo.get_with_relations(block_id)
        if block is None:
            raise NotFoundError("Блок общежития", block_id)
        return block

    def _get_plan_or_404(self, plan_id: int) -> KitchenDutyPlan:
        plan = self.plan_repo.get_with_relations(plan_id)
        if plan is None:
            raise NotFoundError("План дежурств", plan_id)
        return plan

    def _resolve_user_block_id(self, room_id: int | None) -> int | None:
        if room_id is None:
            return None
        block = self.block_repo.get_block_by_room(room_id)
        return block.id if block else None

    def _ensure_event_visible_for_user(self, event: CalendarEvent, current_user: User) -> None:
        if self._can_manage_calendar(current_user):
            return
        user_block_id = self._resolve_user_block_id(current_user.room_id)
        if event.status == "draft":
            raise NotFoundError("Календарное событие", event.id)
        if event.scope_type == "global":
            return
        if event.scope_type == "dormitory" and event.dormitory_id == current_user.dormitory_id:
            return
        if event.scope_type == "block" and event.block_id == user_block_id:
            return
        if event.scope_type == "room" and event.room_id == current_user.room_id:
            return
        raise NotFoundError("Календарное событие", event.id)

    def _validate_optional_event_filters(
        self,
        event_kind: str | None,
        status: str | None,
        scope_type: str | None,
    ) -> None:
        if event_kind and event_kind not in ALLOWED_EVENT_KINDS:
            raise ValidationError("Недопустимый event_kind")
        if status and status not in ALLOWED_STATUSES:
            raise ValidationError("Недопустимый status")
        if scope_type and scope_type not in ALLOWED_SCOPE_TYPES:
            raise ValidationError("Недопустимый scope_type")

    def _validate_event_payload(self, data: CalendarEventCreate) -> None:
        if data.event_kind not in ALLOWED_EVENT_KINDS:
            raise ValidationError("Недопустимый event_kind")
        if data.scope_type not in ALLOWED_SCOPE_TYPES:
            raise ValidationError("Недопустимый scope_type")
        if data.status not in ALLOWED_STATUSES:
            raise ValidationError("Недопустимый status")
        if data.end_at < data.start_at:
            raise ValidationError("end_at не может быть раньше start_at")

    def _validate_plan_dates(self, month_start: date, month_end: date) -> None:
        if month_end < month_start:
            raise ValidationError("month_end не может быть раньше month_start")
        if month_start.year != month_end.year or month_start.month != month_end.month:
            raise ValidationError("План дежурств должен находиться в рамках одного календарного месяца")

    def _resolve_scope_entities(
        self,
        *,
        scope_type: str,
        dormitory_id: int | None,
        block_id: int | None,
        room_id: int | None,
        related_news_id: int | None,
    ) -> dict[str, int | None]:
        dormitory = None
        block = None
        room = None
        if dormitory_id is not None:
            dormitory = self.db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
            if dormitory is None:
                raise DormitoryNotFoundError(dormitory_id)
        if block_id is not None:
            block = self.db.query(DormitoryBlock).filter(DormitoryBlock.id == block_id).first()
            if block is None:
                raise NotFoundError("Блок общежития", block_id)
        if room_id is not None:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if room is None:
                raise RoomNotFoundError(room_id)
        if related_news_id is not None:
            news = self.db.query(News).filter(News.id == related_news_id).first()
            if news is None:
                raise NotFoundError("Новость", related_news_id)

        resolved_dormitory_id = dormitory_id
        resolved_block_id = block_id
        resolved_room_id = room_id

        if scope_type == "global":
            resolved_dormitory_id = None
            resolved_block_id = None
            resolved_room_id = None
        elif scope_type == "dormitory":
            if dormitory is None:
                raise ValidationError("scope_type=dormitory требует dormitory_id")
            resolved_block_id = None
            resolved_room_id = None
        elif scope_type == "block":
            if block is None:
                raise ValidationError("scope_type=block требует block_id")
            resolved_dormitory_id = block.dormitory_id
            resolved_room_id = None
            if dormitory is not None and dormitory.id != block.dormitory_id:
                raise ValidationError("Блок не принадлежит указанному общежитию")
        elif scope_type == "room":
            if room is None:
                raise ValidationError("scope_type=room требует room_id")
            resolved_dormitory_id = room.dormitory_id
            if block is not None and block.dormitory_id != room.dormitory_id:
                raise ValidationError("Комната и блок принадлежат разным общежитиям")
            if block is None:
                block = self.block_repo.get_block_by_room(room.id)
            resolved_block_id = block.id if block else None
            if dormitory is not None and dormitory.id != room.dormitory_id:
                raise ValidationError("Комната не принадлежит указанному общежитию")

        return {
            "dormitory_id": resolved_dormitory_id,
            "block_id": resolved_block_id,
            "room_id": resolved_room_id,
            "related_news_id": related_news_id,
        }

    def _can_manage_calendar(self, user: User) -> bool:
        return user_has_role(user, *MANAGE_CALENDAR_ROLES)

    def _require_manage_calendar(self, user: User) -> None:
        if not self._can_manage_calendar(user):
            raise InsufficientPermissionsError()

    def _require_manage_blocks(self, user: User) -> None:
        if not user_has_role(user, *MANAGE_BLOCK_ROLES):
            raise InsufficientPermissionsError()
