# app/models/project.py
# 项目管理模型
#
# 功能说明：
# 1. Project - 项目表，支持多种项目类型和多实体关联
# 2. ProjectAssociation - 项目关联表（多态 junction），将项目与客户/供应商/合同/产品关联
#
# 使用方法：
#   from app.models.project import Project, ProjectAssociation

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, JSON, DateTime, Date, Integer, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    """
    项目表

    支持多种项目类型（研发/订单/采购/销售 等），
    通过 ProjectAssociation 实现与客户/供应商/合同/产品的多对多关联。

    状态流转：
    draft → active → on_hold / completed / cancelled
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="项目名称",
    )
    project_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        comment="项目类型: general/research/order/purchase/sales 等",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="项目描述",
    )

    # ==================== 状态与优先级 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        comment="状态: draft/active/on_hold/completed/cancelled",
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default="medium",
        comment="优先级: low/medium/high/urgent",
    )

    # ==================== 日期 ====================
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="开始日期",
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="截止日期",
    )

    # ==================== 负责人 ====================
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="项目负责人 ID",
    )

    # ==================== 扩展 ====================
    tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="标签列表",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )

    # ==================== 审计 ====================
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
    owner_dept_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True,
        index=True, comment="负责人部门"
    )

    # ==================== 关系 ====================
    associations: Mapped[List["ProjectAssociation"]] = relationship(
        "ProjectAssociation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Task.sort_order",
    )

    __table_args__ = (
        Index("ix_projects_name", "name"),
        Index("ix_projects_project_type", "project_type"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_priority", "priority"),
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.status})>"


class ProjectAssociation(Base):
    """
    项目关联表（多态 junction table）

    通过 entity_type + entity_id 实现一个项目与多种业务实体的多对多关联。
    支持的 entity_type: customer / supplier / purchase_contract / sales_contract / product
    """

    __tablename__ = "project_associations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="项目 ID",
    )
    entity_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="实体类型: customer/supplier/purchase_contract/sales_contract/product/inbound_order/outbound_order/client_rfq/quotation/supplier_rfq/supplier_quotation",
    )
    entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        comment="实体 ID",
    )

    # ==================== 扩展 ====================
    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="关联备注",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # ==================== 关系 ====================
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="associations",
    )

    __table_args__ = (
        Index("ix_project_associations_project_id", "project_id"),
        Index("ix_project_associations_entity_type", "entity_type"),
        Index("ix_project_associations_entity_id", "entity_id"),
        Index(
            "uq_project_entity",
            "project_id", "entity_type", "entity_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<ProjectAssociation {self.project_id} -> {self.entity_type}:{self.entity_id}>"
