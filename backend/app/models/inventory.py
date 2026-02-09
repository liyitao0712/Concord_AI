# app/models/inventory.py
# 库存管理模型
#
# 功能说明：
# 1. Inventory - 库存表，按仓库+产品维度记录库存
# 2. 支持实际库存和占用库存，可用库存 = 实际 - 占用
#
# 使用方法：
#   from app.models.inventory import Inventory

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String, Text, Numeric,
    DateTime, Index, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inventory(Base):
    """
    库存表

    按仓库+产品维度记录库存信息。
    每个仓库的每个产品只有一条记录（UniqueConstraint）。

    - quantity: 实际库存数量
    - reserved_quantity: 被销售合同占用的数量
    - 可用库存 = quantity - reserved_quantity（业务层计算）
    """

    __tablename__ = "inventories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    warehouse_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        comment="仓库 ID",
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="产品 ID",
    )

    # ==================== 库存数量 ====================
    quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="实际库存数量",
    )
    reserved_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="占用数量（被销售合同占用）",
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="单位",
    )

    # ==================== 其他 ====================
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ==================== 权限字段 ====================
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True,
        index=True, comment="所属组织"
    )

    # ==================== 关系 ====================
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="inventories",
    )
    product: Mapped["Product"] = relationship(
        "Product",
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"),
        Index("ix_inventories_warehouse_id", "warehouse_id"),
        Index("ix_inventories_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<Inventory warehouse={self.warehouse_id} product={self.product_id} qty={self.quantity}>"
