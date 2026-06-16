from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from api.db.models import DormitoryBlock, DormitoryBlockRoom
from api.repositories.base import BaseRepository


class DormitoryBlockRepository(BaseRepository[DormitoryBlock]):
    def __init__(self, db: Session):
        super().__init__(db, DormitoryBlock)

    def list_filtered(
        self,
        *,
        dormitory_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[DormitoryBlock]:
        query = self.db.query(DormitoryBlock).options(
            joinedload(DormitoryBlock.dormitory),
            joinedload(DormitoryBlock.block_rooms).joinedload(DormitoryBlockRoom.room),
        )
        if dormitory_id is not None:
            query = query.filter(DormitoryBlock.dormitory_id == dormitory_id)
        if is_active is not None:
            query = query.filter(DormitoryBlock.is_active == is_active)
        return query.order_by(DormitoryBlock.name.asc(), DormitoryBlock.id.asc()).all()

    def get_with_relations(self, block_id: int) -> DormitoryBlock | None:
        return (
            self.db.query(DormitoryBlock)
            .options(
                joinedload(DormitoryBlock.dormitory),
                joinedload(DormitoryBlock.block_rooms).joinedload(DormitoryBlockRoom.room),
            )
            .filter(DormitoryBlock.id == block_id)
            .first()
        )

    def get_room_link(self, block_id: int, room_id: int) -> DormitoryBlockRoom | None:
        return (
            self.db.query(DormitoryBlockRoom)
            .options(joinedload(DormitoryBlockRoom.room), joinedload(DormitoryBlockRoom.block))
            .filter(
                DormitoryBlockRoom.block_id == block_id,
                DormitoryBlockRoom.room_id == room_id,
            )
            .first()
        )

    def get_room_binding(self, room_id: int) -> DormitoryBlockRoom | None:
        return (
            self.db.query(DormitoryBlockRoom)
            .options(joinedload(DormitoryBlockRoom.block))
            .filter(DormitoryBlockRoom.room_id == room_id)
            .first()
        )

    def get_block_by_room(self, room_id: int) -> DormitoryBlock | None:
        link = self.get_room_binding(room_id)
        return link.block if link else None

    def list_ordered_rooms(self, block_id: int) -> list[DormitoryBlockRoom]:
        return (
            self.db.query(DormitoryBlockRoom)
            .options(joinedload(DormitoryBlockRoom.room))
            .filter(DormitoryBlockRoom.block_id == block_id)
            .order_by(DormitoryBlockRoom.rotation_order.asc(), DormitoryBlockRoom.id.asc())
            .all()
        )
