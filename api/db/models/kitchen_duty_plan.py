# -*- coding: utf-8 -*-
from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import relationship

from api.db.models.base import Base


class KitchenDutyPlan(Base):
    __tablename__ = "kitchen_duty_plans"
    __table_args__ = (
        CheckConstraint("month_end >= month_start", name="chk_kitchen_duty_plans_dates"),
        CheckConstraint(
            "status IN ('draft', 'generated', 'cancelled')",
            name="chk_kitchen_duty_plans_status",
        ),
        Index("idx_kitchen_duty_plans_dormitory_id", "dormitory_id"),
        Index("idx_kitchen_duty_plans_block_id", "block_id"),
        Index("idx_kitchen_duty_plans_month_start", "month_start"),
        Index("idx_kitchen_duty_plans_status", "status"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id", ondelete="RESTRICT"), nullable=False)
    block_id = Column(Integer, ForeignKey("dormitory_blocks.id", ondelete="RESTRICT"), nullable=False)
    month_start = Column(Date, nullable=False)
    month_end = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, server_default="draft")
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    dormitory = relationship("Dormitory", back_populates="kitchen_duty_plans")
    block = relationship("DormitoryBlock", back_populates="kitchen_duty_plans")
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_kitchen_duty_plans",
    )
    assignments = relationship(
        "KitchenDutyAssignment",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="KitchenDutyAssignment.duty_date",
    )
