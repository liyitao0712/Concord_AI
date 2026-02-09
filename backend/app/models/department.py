# app/models/department.py
# 部门模型（树形结构）

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(Base):
    """
    部门模型（树形自引用）

    通过 parent_id 自引用构成部门树。
    用于数据权限中的 department_tree 范围查询。
    """

    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False,
        index=True, comment="所属组织"
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True,
        index=True, comment="上级部门（NULL 表示顶级）"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="部门名称"
    )
    code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="部门编码"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="排序"
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
    organization = relationship("Organization", back_populates="departments")
    parent = relationship("Department", remote_side="Department.id", backref="children")

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name={self.name}, org_id={self.org_id})>"
