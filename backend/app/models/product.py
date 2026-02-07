# app/models/product.py
# 产品管理模型
#
# 功能说明：
# 1. Product - 产品表，记录外贸产品信息
# 2. ProductSupplier - 产品-供应商关联表，支持多对多并附带业务字段
#
# 使用方法：
#   from app.models.product import Product, ProductSupplier

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Boolean, Integer, Numeric, JSON,
    DateTime, Index, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    """
    产品表

    记录外贸产品完整信息，包含基本信息、价格贸易信息等。

    字段分组：
    - 基本信息: name, model_number, specifications, unit
    - 价格贸易: moq, reference_price, currency, hs_code, origin, material, packaging
    - 媒体和描述: images, description, tags
    - 状态: status, notes
    - 关联: category_id
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联品类 ====================
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="所属品类 ID",
    )

    # ==================== 基本信息 ====================
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="品名",
    )
    model_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="型号",
    )
    specifications: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="规格",
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="单位，如 PCS/SET/KG",
    )

    # ==================== 价格贸易信息 ====================
    moq: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最小起订量",
    )
    reference_price: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="参考价格",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        comment="币种",
    )
    hs_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="HS 编码",
    )
    origin: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="产地",
    )
    material: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="材质",
    )
    packaging: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="包装方式",
    )

    # ==================== 媒体和描述 ====================
    images: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="产品图片 URL 列表",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="产品描述",
    )
    tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="标签列表",
    )

    # ==================== 状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        comment="状态: active/inactive/discontinued",
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
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="products",
    )
    product_suppliers: Mapped[List["ProductSupplier"]] = relationship(
        "ProductSupplier",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_status", "status"),
        Index("ix_products_name", "name"),
        Index("ix_products_hs_code", "hs_code"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.name}>"


class ProductSupplier(Base):
    """
    产品-供应商关联表

    记录产品与供应商的多对多关系，附带供应价格、MOQ、交期等业务字段。
    同一产品和供应商只能关联一次（唯一约束）。
    """

    __tablename__ = "product_suppliers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="产品 ID",
    )
    supplier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        comment="供应商 ID",
    )

    # ==================== 供应信息 ====================
    supply_price: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="供应价格",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        comment="币种",
    )
    moq: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="该供应商的最小起订量",
    )
    lead_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="交期（天）",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否首选供应商",
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
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="product_suppliers",
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
    )

    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
        Index("ix_product_suppliers_product_id", "product_id"),
        Index("ix_product_suppliers_supplier_id", "supplier_id"),
    )

    def __repr__(self) -> str:
        return f"<ProductSupplier product={self.product_id} supplier={self.supplier_id}>"
