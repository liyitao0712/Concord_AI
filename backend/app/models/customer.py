# app/models/customer.py
# 客户管理模型
#
# 功能说明：
# 1. Customer - 客户（公司）表，记录 B2B 海外客户公司信息
# 2. Contact - 联系人表，记录客户公司的联系人
#
# 使用方法：
#   from app.models.customer import Customer, Contact

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, JSON, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Customer(Base):
    """
    客户（公司）表

    记录 B2B 海外客户公司信息，支持外贸场景所需的全部字段。

    字段分组：
    - 基本信息: name, short_name, country, region
    - 业务信息: industry, company_size, annual_revenue, customer_level
    - 联系信息: email, phone, website, address
    - 贸易信息: payment_terms, shipping_terms
    - 状态: is_active, source
    - 扩展: notes, tags
    """

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="公司全称，如 'Hyde Tools, Inc.'",
    )
    short_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="简称/别名，如 'Hyde'",
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="国家，如 'United States'",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="地区/洲，如 'North America'",
    )

    # ==================== 业务信息 ====================
    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="行业，如 'Tools & Hardware'",
    )
    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="公司规模: small/medium/large/enterprise",
    )
    annual_revenue: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="年营收范围，如 '<1M', '1M-10M', '10M-50M', '>50M'",
    )
    customer_level: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        comment="客户等级: potential/normal/important/vip",
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
        comment="是否活跃客户",
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="客户来源: email/exhibition/referral/website/other",
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
        comment="标签列表，如 ['putty_knife', 'taping_knife']",
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
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_customers_name", "name"),
        Index("ix_customers_country", "country"),
        Index("ix_customers_customer_level", "customer_level"),
        Index("ix_customers_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"


class Contact(Base):
    """
    联系人表

    记录客户公司的联系人信息，一个客户可以有多个联系人。
    支持标记主联系人（is_primary）。
    """

    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 所属客户 ====================
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属客户 ID",
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
        comment="职位/头衔，如 'Purchasing Manager'",
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
        comment="社交媒体，如 {'linkedin': 'url', 'whatsapp': 'number'}",
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
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="contacts",
    )

    __table_args__ = (
        Index("ix_contacts_customer_id", "customer_id"),
        Index("ix_contacts_email", "email"),
        Index("ix_contacts_is_primary", "is_primary"),
        Index("ix_contacts_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Contact {self.name} @ {self.customer_id}>"
