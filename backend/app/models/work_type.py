# app/models/work_type.py
# 工作类型模型
#
# 功能说明：
# 1. WorkType - 工作类型定义表，支持 Parent-Child 层级结构
# 2. WorkTypeSuggestion - AI 建议的新工作类型，待人工审批
#
# 使用方法：
#   from app.models.work_type import WorkType, WorkTypeSuggestion

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, Integer, Float, JSON, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkType(Base):
    """
    工作类型定义表

    支持 Parent-Child 树形结构：
    - level=1: 顶级分类（如 ORDER, INQUIRY）
    - level=2: 子分类（如 ORDER_NEW, ORDER_CHANGE）

    由 WorkTypeAnalyzerAgent 自动识别和积累，需人工审核后生效。

    字段说明：
    - code: 唯一标识码（英文大写），如 "ORDER", "ORDER_NEW"
    - name: 显示名称（中文），如 "订单", "新订单"
    - description: 给 LLM 的描述，帮助 LLM 理解这个工作类型
    - examples: 示例文本列表，帮助 LLM 更准确识别
    - keywords: 关键词列表，辅助匹配

    命名规范：
    - 全大写英文 + 下划线分隔
    - 子级 code 必须以父级 code 为前缀：ORDER → ORDER_NEW
    """

    __tablename__ = "work_types"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 层级结构（自引用）
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("work_types.id", ondelete="CASCADE"),
        nullable=True,
        comment="父级 WorkType ID，顶级为 NULL",
    )

    # 基本信息
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="唯一标识码，如 ORDER, ORDER_NEW",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称（中文），如 '订单', '新订单'",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="工作类型描述（给 LLM 参考）",
    )

    # 层级信息
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="层级深度，1=顶级，2=子级",
    )
    path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="完整路径，如 '/ORDER/ORDER_NEW'",
    )

    # LLM 辅助字段
    examples: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="示例文本列表，帮助 LLM 识别",
    )
    keywords: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="关键词列表",
    )

    # 状态标记
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否系统内置（不可删除）",
    )

    # 统计信息
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="使用次数（用于排序和分析）",
    )

    # 来源追踪
    created_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        comment="创建者: system | admin | ai_approved_by_{user_id}",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # 自引用关系
    parent: Mapped[Optional["WorkType"]] = relationship(
        "WorkType",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[List["WorkType"]] = relationship(
        "WorkType",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_work_types_parent_id", "parent_id"),
        Index("ix_work_types_code", "code"),
        Index("ix_work_types_level", "level"),
        Index("ix_work_types_is_active", "is_active"),
    )

    def to_dict(self, include_children: bool = False) -> dict:
        """转换为字典（用于构建 LLM Prompt）"""
        result = {
            "id": self.id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "path": self.path,
            "examples": self.examples or [],
            "keywords": self.keywords or [],
            "is_active": self.is_active,
            "is_system": self.is_system,
            "usage_count": self.usage_count,
            "created_by": self.created_by,
        }
        if include_children and self.children:
            result["children"] = [c.to_dict(include_children=True) for c in self.children]
        return result

    def __repr__(self) -> str:
        return f"<WorkType {self.code}: {self.name}>"


class WorkTypeSuggestion(Base):
    """
    工作类型建议表

    当 WorkTypeAnalyzerAgent 无法匹配现有工作类型时，LLM 会建议新的类型。
    建议会保存到这个表，等待管理员审批。

    审批流程（通过 Temporal Workflow）：
    1. AI 建议新工作类型 → 保存到此表（status=pending）
    2. 启动 WorkTypeSuggestionWorkflow
    3. 通知管理员审批
    4. 管理员批准 → 创建 WorkType 记录
       管理员拒绝 → 标记为 rejected
    """

    __tablename__ = "work_type_suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 建议内容 ====================
    suggested_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="建议的 code",
    )
    suggested_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="建议的名称",
    )
    suggested_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="建议的描述",
    )
    suggested_parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="建议的父级 ID",
    )
    suggested_parent_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的父级 code（冗余，方便展示）",
    )
    suggested_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="建议的层级",
    )
    suggested_examples: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="建议的示例",
    )
    suggested_keywords: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="建议的关键词",
    )

    # ==================== AI 分析信息 ====================
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="AI 置信度 0-1",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI 推理说明",
    )

    # ==================== 触发来源 ====================
    trigger_email_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="触发的邮件 ID",
    )
    trigger_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="触发建议的内容摘要",
    )
    trigger_source: Mapped[str] = mapped_column(
        String(20),
        default="email",
        comment="来源: email | manual | import",
    )

    # ==================== 审批状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="状态: pending | approved | rejected | merged",
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Temporal Workflow ID",
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="审批人 ID",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="审批时间",
    )
    review_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="审批备注",
    )

    # 如果批准，关联创建的 WorkType
    created_work_type_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="创建的 WorkType ID",
    )

    # 如果合并到现有类型
    merged_to_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="合并到的 WorkType ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_work_type_suggestions_status", "status"),
        Index("ix_work_type_suggestions_created_at", "created_at"),
        Index("ix_work_type_suggestions_trigger_email_id", "trigger_email_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkTypeSuggestion {self.suggested_code} ({self.status})>"


# ==================== 种子数据 ====================

SEED_WORK_TYPES = [
    # Level 1: 顶级分类
    {
        "code": "ORDER",
        "name": "订单",
        "description": "与订单相关的邮件，包括新订单、修改、取消等",
        "level": 1,
        "path": "/ORDER",
        "examples": ["我想下单", "订单确认", "采购订单", "PO"],
        "keywords": ["订单", "order", "PO", "采购", "purchase"],
        "is_system": True,
    },
    {
        "code": "INQUIRY",
        "name": "询价",
        "description": "客户询价、询盘、了解产品信息、请求报价",
        "level": 1,
        "path": "/INQUIRY",
        "examples": ["请报价", "询问价格", "product inquiry", "RFQ"],
        "keywords": ["询价", "报价", "inquiry", "quote", "RFQ", "价格"],
        "is_system": True,
    },
    {
        "code": "SHIPMENT",
        "name": "物流",
        "description": "发货、物流跟踪、运输、清关相关",
        "level": 1,
        "path": "/SHIPMENT",
        "examples": ["发货通知", "物流追踪", "shipping details", "提单"],
        "keywords": ["发货", "物流", "shipping", "delivery", "B/L", "提单"],
        "is_system": True,
    },
    {
        "code": "PAYMENT",
        "name": "付款",
        "description": "付款通知、汇款确认、财务、发票相关",
        "level": 1,
        "path": "/PAYMENT",
        "examples": ["付款通知", "汇款底单", "payment confirmation", "invoice"],
        "keywords": ["付款", "汇款", "payment", "remittance", "invoice", "发票"],
        "is_system": True,
    },
    {
        "code": "COMPLAINT",
        "name": "投诉",
        "description": "客户投诉、质量问题、售后问题",
        "level": 1,
        "path": "/COMPLAINT",
        "examples": ["产品质量问题", "投诉", "要求退款", "不满意"],
        "keywords": ["投诉", "质量", "退款", "complaint", "refund", "问题"],
        "is_system": True,
    },
    {
        "code": "OTHER",
        "name": "其他",
        "description": "无法分类的工作类型",
        "level": 1,
        "path": "/OTHER",
        "examples": [],
        "keywords": [],
        "is_system": True,
    },
    # Level 2: 子分类
    {
        "code": "ORDER_NEW",
        "name": "新订单",
        "description": "客户发起新订单、首次采购",
        "level": 2,
        "path": "/ORDER/ORDER_NEW",
        "parent_code": "ORDER",
        "examples": ["新订单", "首次采购", "请报价并下单", "new order"],
        "keywords": ["新订单", "new order", "首次", "下单"],
        "is_system": True,
    },
    {
        "code": "ORDER_CHANGE",
        "name": "订单修改",
        "description": "修改已有订单的数量、规格、交期等",
        "level": 2,
        "path": "/ORDER/ORDER_CHANGE",
        "parent_code": "ORDER",
        "examples": ["修改订单", "更改数量", "变更交期", "revise order"],
        "keywords": ["修改", "更改", "change", "revise", "amendment"],
        "is_system": True,
    },
]
