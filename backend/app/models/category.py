# app/models/category.py
# 品类管理模型
#
# 功能说明：
# 1. Category - 品类表，支持多级树形结构（自引用）
#
# 使用方法：
#   from app.models.category import Category

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, Numeric, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    """
    品类表

    支持多级树形结构，通过 parent_id 自引用实现父子关系。
    根品类的 parent_id 为 NULL。

    品类编码规则：
    - 根品类: 两位数字，如 "01", "02"
    - 子品类: 父编码-两位数字，如 "01-01", "01-02"
    - 支持多级: "01-01-01"

    字段分组：
    - 基本信息: code, name, name_en, description
    - 层级关系: parent_id
    - 税率信息: vat_rate, tax_rebate_rate
    """

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="品类编码，如 01、01-01、01-01-01",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="品类中文名",
    )
    name_en: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="品类英文名",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="品类描述",
    )

    # ==================== 层级关系 ====================
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        comment="父品类 ID，根品类为 NULL",
    )

    # ==================== 税率信息 ====================
    vat_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="增值税率（%），如 13.00",
    )
    tax_rebate_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="退税率（%），如 13.00",
    )

    # ==================== 图片 ====================
    image_key: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="图片存储路径 key",
    )
    image_storage_type: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="图片存储类型: oss 或 local",
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
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
    )

    __table_args__ = (
        Index("ix_categories_code", "code"),
        Index("ix_categories_parent_id", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<Category {self.code} {self.name}>"
