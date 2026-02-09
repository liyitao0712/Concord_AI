# app/models/outbound_order.py
# 出仓单管理模型
#
# 功能说明：
# 1. OutboundOrder - 出仓单表，记录货物出仓信息
# 2. OutboundLine - 出仓明细表，记录出仓的每个产品行项
# 3. 出仓确认时减少库存、释放占用、更新销售合同发货数量
#
# 使用方法：
#   from app.models.outbound_order import OutboundOrder, OutboundLine

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Numeric, Date,
    DateTime, Index, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OutboundOrder(Base):
    """
    出仓单表

    记录货物出仓信息，可关联销售合同。

    状态流转：
    draft → confirmed → partial_shipped → shipped
    任何状态均可 → cancelled
    """

    __tablename__ = "outbound_orders"

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
        comment="出仓单号",
    )

    # ==================== 关联 ====================
    warehouse_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        comment="出仓仓库 ID",
    )
    sales_contract_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("sales_contracts.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联销售合同 ID",
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        comment="客户 ID（非合同出仓时使用）",
    )

    # ==================== 状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        comment="状态: draft/confirmed/partial_shipped/shipped/cancelled",
    )

    # ==================== 日期 ====================
    expected_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="预计发货日期",
    )
    actual_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="实际发货日期",
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
    sales_contract: Mapped[Optional["SalesContract"]] = relationship("SalesContract")
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    lines: Mapped[List["OutboundLine"]] = relationship(
        "OutboundLine",
        back_populates="outbound_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_outbound_orders_order_no", "order_no"),
        Index("ix_outbound_orders_warehouse_id", "warehouse_id"),
        Index("ix_outbound_orders_sales_contract_id", "sales_contract_id"),
        Index("ix_outbound_orders_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<OutboundOrder {self.order_no}>"


class OutboundLine(Base):
    """
    出仓明细表

    记录出仓单中的每个产品行项。
    出仓确认时减少库存、释放占用、更新销售合同发货数量。
    """

    __tablename__ = "outbound_lines"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    outbound_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("outbound_orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="出仓单 ID",
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        comment="产品 ID",
    )
    sales_line_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("sales_lines.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联销售明细行 ID",
    )

    # ==================== 数量 ====================
    quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="出仓数量",
    )
    shipped_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="已发货数量（累计）",
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
    outbound_order: Mapped["OutboundOrder"] = relationship(
        "OutboundOrder",
        back_populates="lines",
    )
    product: Mapped["Product"] = relationship("Product")
    sales_line: Mapped[Optional["SalesLine"]] = relationship("SalesLine")

    __table_args__ = (
        Index("ix_outbound_lines_outbound_order_id", "outbound_order_id"),
        Index("ix_outbound_lines_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<OutboundLine product={self.product_id} qty={self.quantity}>"
