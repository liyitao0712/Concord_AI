# app/models/supplier.py
# 供应商管理模型
#
# 功能说明：
# 1. Supplier - 供应商（公司）表，记录供应商公司信息
# 2. SupplierContact - 供应商联系人表，记录供应商公司的联系人
#
# 使用方法：
#   from app.models.supplier import Supplier, SupplierContact

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, JSON, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Supplier(Base):
    """
    供应商（公司）表

    记录供应商公司信息，支持外贸场景所需的全部字段。

    字段分组：
    - 基本信息: name, short_name, country, region
    - 业务信息: industry, company_size, main_products, supplier_level
    - 联系信息: email, phone, website, address
    - 贸易信息: payment_terms, shipping_terms
    - 状态: is_active, source
    - 扩展: notes, tags
    """

    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="公司全称",
    )
    short_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="简称/别名",
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="国家",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="地区/洲",
    )

    # ==================== 业务信息 ====================
    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="行业",
    )
    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="公司规模: small/medium/large/enterprise",
    )
    main_products: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="主营产品描述",
    )
    supplier_level: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        comment="供应商等级: potential/normal/important/strategic",
    )

    # ==================== 联系信息 ====================
    email: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="公司主邮箱",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="公司电话",
    )
    website: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="公司网站",
    )
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="公司地址",
    )

    # ==================== 贸易信息 ====================
    payment_terms: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="付款条款，如 'T/T 30 days', 'L/C at sight'",
    )
    shipping_terms: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="贸易术语（Incoterms），如 'FOB', 'CIF', 'EXW'",
    )

    # ==================== 状态信息 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否活跃供应商",
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="供应商来源: email/exhibition/referral/website/1688/other",
    )

    # ==================== 扩展信息 ====================
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )
    tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="标签列表",
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
    contacts: Mapped[List["SupplierContact"]] = relationship(
        "SupplierContact",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_suppliers_name", "name"),
        Index("ix_suppliers_country", "country"),
        Index("ix_suppliers_supplier_level", "supplier_level"),
        Index("ix_suppliers_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"


class SupplierContact(Base):
    """
    供应商联系人表

    记录供应商公司的联系人信息，一个供应商可以有多个联系人。
    支持标记主联系人（is_primary）。
    """

    __tablename__ = "supplier_contacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 所属供应商 ====================
    supplier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属供应商 ID",
    )

    # ==================== 基本信息 ====================
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="联系人姓名",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="职位/头衔",
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="部门",
    )

    # ==================== 联系方式 ====================
    email: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="邮箱",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="座机",
    )
    mobile: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="手机",
    )
    social_media: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="社交媒体，如 {'wechat': 'id', 'whatsapp': 'number'}",
    )

    # ==================== 状态 ====================
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否主联系人",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否活跃",
    )

    # ==================== 扩展 ====================
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
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="contacts",
    )

    __table_args__ = (
        Index("ix_supplier_contacts_supplier_id", "supplier_id"),
        Index("ix_supplier_contacts_email", "email"),
        Index("ix_supplier_contacts_is_primary", "is_primary"),
        Index("ix_supplier_contacts_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<SupplierContact {self.name} @ {self.supplier_id}>"
