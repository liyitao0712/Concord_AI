# app/models/supplier_quotation.py
# 供应商报价单管理模型
#
# 功能说明：
# 1. SupplierQuotation - 供应商报价单表，记录供应商给我们的报价
# 2. SupplierQuotationLine - 供应商报价单明细表，记录报价中的每个产品行项
#
# 使用方法：
#   from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationLine

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Integer, Numeric, JSON, Date,
    DateTime, Index, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SupplierQuotation(Base):
    """
    供应商报价单表

    记录供应商给我们的报价信息，可从供应商询价单（SupplierRFQ）流转而来。
    可进一步流转为采购合同（PurchaseContract）。

    状态流转：
    draft → received → reviewing → accepted / rejected / expired
    任何状态均可 → cancelled
    """

    __tablename__ = "supplier_quotations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 报价单编号 ====================
    quotation_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="报价单编号",
    )

    # ==================== 关联 ====================
    supplier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="供应商 ID",
    )
    contact_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("supplier_contacts.id", ondelete="SET NULL"),
        nullable=True,
        comment="供应商联系人 ID",
    )
    linked_supplier_rfq_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("supplier_rfqs.id", ondelete="SET NULL"),
        nullable=True,
        comment="来源供应商询价单 ID",
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

    # ==================== 日期 ====================
    quotation_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="报价日期",
    )
    valid_until: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="报价有效期",
    )

    # ==================== 状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        comment="状态: draft/received/reviewing/accepted/rejected/expired/cancelled",
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
    supplier: Mapped["Supplier"] = relationship("Supplier")
    contact: Mapped[Optional["SupplierContact"]] = relationship("SupplierContact")
    linked_supplier_rfq: Mapped[Optional["SupplierRFQ"]] = relationship("SupplierRFQ")
    created_by_user: Mapped[Optional["User"]] = relationship("User")
    lines: Mapped[List["SupplierQuotationLine"]] = relationship(
        "SupplierQuotationLine",
        back_populates="supplier_quotation",
        cascade="all, delete-orphan",
        order_by="SupplierQuotationLine.line_no",
    )

    __table_args__ = (
        Index("ix_supplier_quotations_quotation_no", "quotation_no"),
        Index("ix_supplier_quotations_supplier_id", "supplier_id"),
        Index("ix_supplier_quotations_status", "status"),
        Index("ix_supplier_quotations_quotation_date", "quotation_date"),
        Index("ix_supplier_quotations_linked_supplier_rfq_id", "linked_supplier_rfq_id"),
    )

    def __repr__(self) -> str:
        return f"<SupplierQuotation {self.quotation_no}>"


class SupplierQuotationLine(Base):
    """
    供应商报价单明细表

    记录供应商报价单中的每个产品行项，包含数量、单价、财务字段等。
    """

    __tablename__ = "supplier_quotation_lines"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    supplier_quotation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("supplier_quotations.id", ondelete="CASCADE"),
        nullable=False,
        comment="供应商报价单 ID",
    )
    line_no: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="行号（报价单内排序）",
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
        comment="品名（冗余，防止产品改名影响历史记录）",
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
    supplier_quotation: Mapped["SupplierQuotation"] = relationship(
        "SupplierQuotation",
        back_populates="lines",
    )
    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        Index("ix_supplier_quotation_lines_supplier_quotation_id", "supplier_quotation_id"),
        Index("ix_supplier_quotation_lines_product_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<SupplierQuotationLine {self.line_no}: {self.product_name}>"
