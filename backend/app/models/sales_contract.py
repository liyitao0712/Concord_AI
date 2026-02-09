# app/models/sales_contract.py
# 销售合同管理模型
#
# 功能说明：
# 1. SalesContract - 销售合同表，记录与客户的销售合同
# 2. SalesLine - 销售合同明细表，记录合同中的每个产品行项
# 3. 支持零库存模式（linked_purchase_contract_id 1:1 绑定采购合同）
# 4. 支持库存占用（sales_line 上的 reserved_warehouse_id + reserved_quantity）
#
# 使用方法：
#   from app.models.sales_contract import SalesContract, SalesLine

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Boolean, Integer, Numeric, JSON, Date,
    DateTime, Index, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SalesContract(Base):
    """
    销售合同表

    记录与客户的销售合同信息，包含贸易条款、财务信息、物流信息等。
    支持零库存模式（is_zero_stock=True, linked_purchase_contract_id 关联采购合同）。

    状态流转：
    draft → pending_approval → approved → signed → in_progress
    → partial_shipped → shipped → completed
    任何状态均可 → cancelled
    """

    __tablename__ = "sales_contracts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 合同编号 ====================
    contract_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="合同编号",
    )

    # ==================== 关联 ====================
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="客户 ID",
    )
    contact_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        comment="客户联系人 ID",
    )

    # ==================== 贸易信息 ====================
    trade_term: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="贸易术语（FOB/CIF 等）",
    )
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="付款方式",
    )
    payment_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="付款条款详细描述",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        comment="币种",
    )
    exchange_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 6),
        nullable=True,
        comment="汇率",
    )

    # ==================== 财务汇总 ====================
    subtotal: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="小计（明细行合计）",
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="整单折扣金额",
    )
    tax_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="税额",
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="总金额",
    )
    commission_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="佣金比例 %",
    )
    commission_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="佣金金额",
    )

    # ==================== 物流信息 ====================
    port_of_loading: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="装运港",
    )
    port_of_discharge: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="目的港",
    )
    destination: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="最终目的地",
    )
    shipping_marks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="唛头",
    )

    # ==================== 日期 ====================
    contract_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="合同日期",
    )
    delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="交货日期",
    )
    shipping_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="装运日期",
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="合同有效期",
    )

    # ==================== 状态和模式 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        comment="状态: draft/pending_approval/approved/signed/in_progress/partial_shipped/shipped/completed/cancelled",
    )
    is_zero_stock: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否零库存模式",
    )
    linked_purchase_contract_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("purchase_contracts.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        comment="零库存关联的采购合同 ID（1:1）",
    )

    # ==================== 其他 ====================
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )
    attachments: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="附件列表 [{name, key, storage_type}]",
    )
    tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="标签列表",
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
    customer: Mapped["Customer"] = relationship("Customer")
    contact: Mapped[Optional["Contact"]] = relationship("Contact")
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    linked_purchase_contract: Mapped[Optional["PurchaseContract"]] = relationship(
        "PurchaseContract",
    )
    lines: Mapped[List["SalesLine"]] = relationship(
        "SalesLine",
        back_populates="sales_contract",
        cascade="all, delete-orphan",
        order_by="SalesLine.line_no",
    )

    __table_args__ = (
        Index("ix_sales_contracts_contract_no", "contract_no"),
        Index("ix_sales_contracts_customer_id", "customer_id"),
        Index("ix_sales_contracts_status", "status"),
        Index("ix_sales_contracts_contract_date", "contract_date"),
        Index("ix_sales_contracts_is_zero_stock", "is_zero_stock"),
    )

    def __repr__(self) -> str:
        return f"<SalesContract {self.contract_no}>"


class SalesLine(Base):
    """
    销售合同明细表

    记录销售合同中的每个产品行项，包含数量、单价、财务字段等。
    支持库存占用（reserved_warehouse_id + reserved_quantity）。
    """

    __tablename__ = "sales_lines"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    sales_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sales_contracts.id", ondelete="CASCADE"),
        nullable=False,
        comment="销售合同 ID",
    )
    line_no: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="行号（合同内排序）",
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        comment="产品 ID",
    )

    # ==================== 产品信息（冗余） ====================
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="品名（冗余，防止产品改名影响历史合同）",
    )
    specifications: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="规格",
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="单位",
    )

    # ==================== 数量和价格 ====================
    quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="数量",
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="单价",
    )

    # ==================== 财务字段 ====================
    discount_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0,
        comment="折扣率 %",
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="折扣金额",
    )
    tax_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0,
        comment="税率 %",
    )
    tax_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="税额",
    )
    tax_rebate_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="退税率 %",
    )
    amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="金额（数量 × 单价 - 折扣）",
    )
    amount_with_tax: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        comment="含税金额",
    )

    # ==================== 发货跟踪 ====================
    shipped_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="已发货数量",
    )

    # ==================== 库存占用 ====================
    reserved_warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        comment="占用库存的仓库 ID",
    )
    reserved_quantity: Mapped[float] = mapped_column(
        Numeric(14, 4),
        default=0,
        comment="已占用库存数量",
    )

    # ==================== 其他 ====================
    hs_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="HS 编码",
    )
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
    sales_contract: Mapped["SalesContract"] = relationship(
        "SalesContract",
        back_populates="lines",
    )
    product: Mapped["Product"] = relationship("Product")
    reserved_warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")

    __table_args__ = (
        Index("ix_sales_lines_sales_contract_id", "sales_contract_id"),
        Index("ix_sales_lines_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<SalesLine {self.line_no}: {self.product_name}>"
