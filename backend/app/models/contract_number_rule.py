# app/models/contract_number_rule.py
# 合同编号规则模型
#
# 功能说明：
# 1. ContractNumberRule - 合同编号规则表，支持自定义编号格式
# 2. 每种类型（销售合同/采购合同/入仓单/出仓单）有独立的编号规则
# 3. 编号格式：前缀 + 分隔符 + 日期 + 分隔符 + 序号
#
# 使用方法：
#   from app.models.contract_number_rule import ContractNumberRule

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String, Text, Boolean, Integer,
    DateTime, Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContractNumberRule(Base):
    """
    合同编号规则表

    允许用户自定义各类单据的编号生成规则。
    每种类型只能有一条规则（UniqueConstraint on rule_type）。

    编号生成示例：SC-20260208-001
    """

    __tablename__ = "contract_number_rules"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 规则定义 ====================
    rule_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="规则类型: sales_contract / purchase_contract / inbound_order / outbound_order",
    )
    prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="前缀，如 SC / PO / IN / OUT",
    )
    date_format: Mapped[str] = mapped_column(
        String(20),
        default="%Y%m%d",
        comment="日期格式，如 %Y%m%d / %Y%m / %y%m%d",
    )
    separator: Mapped[str] = mapped_column(
        String(5),
        default="-",
        comment="分隔符",
    )
    sequence_length: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="序号位数",
    )

    # ==================== 序号状态 ====================
    current_sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="当前序号",
    )
    last_date: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="上次生成编号的日期字符串，用于判断是否重置序号",
    )

    # ==================== 状态 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
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

    __table_args__ = (
        UniqueConstraint("rule_type", "org_id", name="uq_contract_number_rule_type_org"),
        Index("ix_contract_number_rules_rule_type", "rule_type"),
    )

    def __repr__(self) -> str:
        return f"<ContractNumberRule {self.rule_type}: {self.prefix}>"
