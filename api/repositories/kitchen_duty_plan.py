from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from api.db.models import (
    DormitoryBlock,
    DormitoryBlockRoom,
    KitchenDutyAssignment,
    KitchenDutyPlan,
)
from api.repositories.base import BaseRepository


class KitchenDutyPlanRepository(BaseRepository[KitchenDutyPlan]):
    def __init__(self, db: Session):
        super().__init__(db, KitchenDutyPlan)

    def list_filtered(
        self,
        *,
        dormitory_id: int | None = None,
        block_id: int | None = None,
        month: date | None = None,
        status: str | None = None,
    ) -> list[KitchenDutyPlan]:
        query = self.db.query(KitchenDutyPlan).options(
            joinedload(KitchenDutyPlan.dormitory),
            joinedload(KitchenDutyPlan.block),
            joinedload(KitchenDutyPlan.created_by),
        )
        if dormitory_id is not None:
            query = query.filter(KitchenDutyPlan.dormitory_id == dormitory_id)
        if block_id is not None:
            query = query.filter(KitchenDutyPlan.block_id == block_id)
        if month is not None:
            query = query.filter(
                KitchenDutyPlan.month_start <= month,
                KitchenDutyPlan.month_end >= month,
            )
        if status:
            query = query.filter(KitchenDutyPlan.status == status)
        return query.order_by(KitchenDutyPlan.month_start.desc(), KitchenDutyPlan.id.desc()).all()

    def get_with_relations(self, plan_id: int) -> KitchenDutyPlan | None:
        return (
            self.db.query(KitchenDutyPlan)
            .options(
                joinedload(KitchenDutyPlan.dormitory),
                joinedload(KitchenDutyPlan.block)
                .joinedload(DormitoryBlock.block_rooms)
                .joinedload(DormitoryBlockRoom.room),
                joinedload(KitchenDutyPlan.created_by),
                joinedload(KitchenDutyPlan.assignments)
                .joinedload(KitchenDutyAssignment.room),
                joinedload(KitchenDutyPlan.assignments)
                .joinedload(KitchenDutyAssignment.calendar_event),
            )
            .filter(KitchenDutyPlan.id == plan_id)
            .first()
        )

    def list_assignments(self, plan_id: int) -> list[KitchenDutyAssignment]:
        return (
            self.db.query(KitchenDutyAssignment)
            .options(
                joinedload(KitchenDutyAssignment.room),
                joinedload(KitchenDutyAssignment.calendar_event),
            )
            .filter(KitchenDutyAssignment.plan_id == plan_id)
            .order_by(KitchenDutyAssignment.duty_date.asc(), KitchenDutyAssignment.id.asc())
            .all()
        )
