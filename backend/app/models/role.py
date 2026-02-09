# app/models/role.py
# 角色与权限模型

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Role(Base):
    """
    角色模型

    每个组织可独立定义角色。org_id 为 NULL 表示系统级角色（如超管）。
    角色通过 RolePermission 关联功能权限，通过 RoleDataScope 配置数据范围。
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True,
        index=True, comment="所属组织（NULL=系统级角色）"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色名称"
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色编码"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="角色描述"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否系统预置（不可删除）"
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
    organization = relationship("Organization", back_populates="roles")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    data_scopes = relationship("RoleDataScope", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, code={self.code})>"


class Permission(Base):
    """
    功能权限定义（全局预置）

    定义系统中所有可控制的资源和操作。
    由系统初始化时预置，管理员不直接增删，只通过 RolePermission 关联。
    """

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="资源标识，如 customer, purchase_contract"
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="操作类型：read, create, update, delete"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="权限描述"
    )

    def __repr__(self) -> str:
        return f"<Permission(resource={self.resource}, action={self.action})>"


class RolePermission(Base):
    """角色-功能权限关联"""

    __tablename__ = "role_permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # 关系
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")

    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class RoleDataScope(Base):
    """
    角色-数据范围配置

    定义某角色对某资源的数据可见范围。
    scope_type 取值：self, department, department_tree, organization, all, custom
    """

    __tablename__ = "role_data_scopes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="资源标识，如 customer, purchase_contract"
    )
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="self",
        comment="数据范围：self/department/department_tree/organization/all/custom"
    )
    custom_dept_ids: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="scope_type=custom 时的自定义部门ID列表"
    )

    # 关系
    role = relationship("Role", back_populates="data_scopes")

    def __repr__(self) -> str:
        return f"<RoleDataScope(role_id={self.role_id}, resource={self.resource}, scope_type={self.scope_type})>"
