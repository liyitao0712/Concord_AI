# app/models/user.py
# 用户数据模型
#
# 功能说明：
# 1. 定义 users 表的结构
# 2. 存储用户基本信息和认证信息
# 3. 关联组织、部门、角色，支持多租户权限体系

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    用户模型

    通过 org_id 实现多租户隔离，通过 role_id 关联动态角色，
    通过 UserDepartment 支持多部门归属。
    """

    __tablename__ = "users"

    # ==================== 主键 ====================
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # ==================== 认证信息 ====================
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False,
        comment="用户邮箱，用于登录"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希值"
    )

    # ==================== 用户信息 ====================
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="用户名称"
    )

    # ==================== 组织与权限 ====================
    # 所属组织（多租户隔离的关键字段）
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True,
        index=True, comment="所属组织（超管可为 NULL）"
    )
    # 主部门（冗余自 UserDepartment，方便查询）
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True,
        index=True, comment="主部门"
    )
    # 动态角色
    role_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("roles.id"), nullable=True,
        index=True, comment="角色"
    )
    # 直属上级
    supervisor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
        comment="直属上级"
    )
    # 超级管理员标记（系统级，不依赖角色表）
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="是否超级管理员"
    )

    # 保留旧 role 字段用于过渡期兼容
    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False,
        comment="旧角色字段（过渡期保留）：admin/user"
    )

    # ==================== 状态标志 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否激活"
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True, comment="更新时间"
    )

    # ==================== 关系 ====================
    organization = relationship("Organization", foreign_keys=[org_id])
    department = relationship("Department", foreign_keys=[department_id])
    role_ref = relationship("Role", foreign_keys=[role_id])
    supervisor = relationship("User", remote_side="User.id", foreign_keys=[supervisor_id])
    user_departments = relationship("UserDepartment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

    @property
    def is_admin(self) -> bool:
        """向后兼容：判断是否管理员（超管或旧 admin 角色）"""
        return self.is_super_admin or self.role == "admin"
