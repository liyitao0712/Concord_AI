# app/models/inbound_order.py
# 入仓单管理模型
#
# 功能说明：
# 1. InboundOrder - 入仓单表，记录货物入仓信息
# 2. InboundLine - 入仓明细表，记录入仓的每个产品行项
# 3. 入仓确认时更新库存数量和采购合同收货数量
#
# 使用方法：
#   from app.models.inbound_order import InboundOrder, InboundLine

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Numeric, Date,
    DateTime, Index, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InboundOrder(Base):
    """
    入仓单表

    记录货物入仓信息，可关联采购合同。

    状态流转：
    draft → confirmed → partial_received → received
    任何状态均可 → cancelled
    """

    __tablename__ = "inbound_orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 单号 ====================
    order_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="入仓单号",
    )

    # ==================== 关联 ====================
    warehouse_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        comment="目标仓库 ID",
    )
    purchase_contract_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("purchase_contracts.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联采购合同 ID",
    )
    supplier_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        comment="供应商 ID（非合同入仓时使用）",
    )

    # ==================== 状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        comment="状态: draft/confirmed/partial_received/received/cancelled",
    )

    # ==================== 日期 ====================
    expected_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="预计到货日期",
    )
    actual_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="实际到货日期",
    )

    # ==================== 其他 ====================
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建人 ID",
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
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
        index=True, comment="负责人"
    )
    owner_dept_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True,
        index=True, comment="负责人部门"
    )

    # ==================== 关系 ====================
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    purchase_contract: Mapped[Optional["PurchaseContract"]] = relationship("PurchaseContract")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    created_by_user: Mapped[Optional["User"]] = relationship("User")
    lines: Mapped[List["InboundLine"]] = relationship(
        "InboundLine",
        back_populates="inbound_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_inbound_orders_order_no", "order_no"),
        Index("ix_inbound_orders_warehouse_id", "warehouse_id"),
        Index("ix_inbound_orders_purchase_contract_id", "purchase_contract_id"),
        Index("ix_inbound_orders_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<InboundOrder {self.order_no}>"


class InboundLine(Base):
    """
    入仓明细表

    记录入仓单中的每个产品行项。
    入仓确认时更新库存和采购合同收货数量。
    """

    __tablename__ = "inbound_lines"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    inbound_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inbound_orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="入仓单 ID",
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        comment="产品 ID",
    )
    purchase_line_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("purchase_lines.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联采购明细行 ID",
    )

    # ==================== 数量 ====================
    expected_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="预期数量",
    )
    received_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="实收数量",
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
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

    # ==================== 关系 ====================
    inbound_order: Mapped["InboundOrder"] = relationship(
        "InboundOrder",
        back_populates="lines",
    )
    product: Mapped["Product"] = relationship("Product")
    purchase_line: Mapped[Optional["PurchaseLine"]] = relationship("PurchaseLine")

    __table_args__ = (
        Index("ix_inbound_lines_inbound_order_id", "inbound_order_id"),
        Index("ix_inbound_lines_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<InboundLine product={self.product_id} expected={self.expected_quantity}>"
