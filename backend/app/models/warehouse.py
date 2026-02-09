# app/models/warehouse.py
# 仓库管理模型
#
# 功能说明：
# 1. Warehouse - 仓库表，记录仓库基本信息
# 2. 支持自有、租赁、保税、虚拟等仓库类型
#
# 使用方法：
#   from app.models.warehouse import Warehouse

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Boolean,
    DateTime, Index, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Warehouse(Base):
    """
    仓库表

    记录仓库的基本信息，包括编码、名称、地址、联系人等。
    支持类型: own(自有) / rented(租赁) / bonded(保税) / virtual(虚拟)
    """

    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="仓库编码",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="仓库名称",
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="仓库地址",
    )
    contact_person: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="联系人",
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="联系电话",
    )
    warehouse_type: Mapped[str] = mapped_column(
        String(20),
        default="own",
        comment="仓库类型: own(自有) / rented(租赁) / bonded(保税) / virtual(虚拟)",
    )

    # ==================== 状态 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
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

    # ==================== 权限字段 ====================
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True,
        index=True, comment="所属组织"
    )

    # ==================== 关系 ====================
    inventories: Mapped[List["Inventory"]] = relationship(
        "Inventory",
        back_populates="warehouse",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_warehouses_code", "code"),
        Index("ix_warehouses_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Warehouse {self.code}: {self.name}>"
