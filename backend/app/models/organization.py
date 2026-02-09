# app/models/organization.py
# 组织/公司模型

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Organization(Base):
    """
    组织/公司模型

    多租户体系的顶层实体，每个子公司对应一条记录。
    所有业务数据通过 org_id 关联到组织，实现公司级数据隔离。
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="组织名称"
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="组织编码（唯一标识）"
    )
    logo: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Logo 文件 key"
    )
    contact_info: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="联系信息（JSON）"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    # 关系
    departments = relationship("Department", back_populates="organization", lazy="selectin")
    roles = relationship("Role", back_populates="organization", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, code={self.code})>"
