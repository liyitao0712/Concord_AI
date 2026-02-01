# app/models/intent.py
# 意图模型
#
# 功能说明：
# 1. Intent - 意图定义表，存储所有可识别的意图
# 2. IntentSuggestion - AI 建议的新意图，待人工审批
#
# 使用方法：
#   from app.models.intent import Intent, IntentSuggestion

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, Integer, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Intent(Base):
    """
    意图定义表

    存储系统可识别的所有意图类型，RouterAgent 会从这里加载意图列表，
    动态构建 Prompt 让 LLM 进行分类。

    字段说明：
    - name: 意图唯一标识（英文），如 "inquiry", "complaint"
    - label: 显示名称（中文），如 "询价", "投诉"
    - description: 给 LLM 的描述，帮助 LLM 理解这个意图
    - examples: 示例消息列表，帮助 LLM 更准确分类
    - keywords: 关键词列表，辅助匹配

    处理配置：
    - default_handler: 默认处理方式 "agent" | "workflow"
    - handler_config: 处理器配置 JSON
      - agent: {"agent_name": "ChatAgent", "reply_prompt": "..."}
      - workflow: {"workflow_name": "QuoteWorkflow"}

    升级条件（什么时候需要人工审批）：
    - escalation_rules: 升级规则 JSON
      - {"amount_gt": 10000} - 金额大于阈值
      - {"keywords": ["紧急", "合同"]} - 包含关键词
      - {"always": true} - 总是升级
    - escalation_workflow: 升级时使用的 Workflow 名称
    """

    __tablename__ = "intents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="意图标识（英文）",
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称（中文）",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="意图描述（给 LLM）",
    )
    examples: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="示例消息列表",
    )
    keywords: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="关键词列表",
    )

    # 默认处理方式
    default_handler: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="agent",
        comment="默认处理方式: agent | workflow",
    )
    handler_config: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="处理器配置",
    )

    # 升级条件
    escalation_rules: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="升级规则",
    )
    escalation_workflow: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="升级 Workflow 名称",
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="优先级（高优先级先匹配）",
    )

    # 元数据
    created_by: Mapped[str] = mapped_column(
        String(50),
        default="system",
        comment="创建者: system | admin | ai",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_intents_is_active", "is_active"),
        Index("ix_intents_priority", "priority"),
    )

    def to_dict(self) -> dict:
        """转换为字典（用于构建 LLM Prompt）"""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "examples": self.examples or [],
            "keywords": self.keywords or [],
        }

    def __repr__(self) -> str:
        return f"<Intent {self.name}: {self.label}>"


class IntentSuggestion(Base):
    """
    意图建议表

    当 RouterAgent 无法匹配现有意图时，LLM 会建议新的意图。
    建议会保存到这个表，等待管理员审批。

    审批流程：
    1. AI 建议新意图 → 保存到此表（status=pending）
    2. 启动 IntentSuggestionWorkflow
    3. 通知管理员审批
    4. 管理员批准 → 创建 Intent 记录
       管理员拒绝 → 标记为 rejected
    """

    __tablename__ = "intent_suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 建议内容
    suggested_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="建议的意图名称",
    )
    suggested_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="建议的显示名称",
    )
    suggested_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="建议的描述",
    )
    suggested_handler: Mapped[str] = mapped_column(
        String(50),
        default="agent",
        comment="建议的处理方式",
    )
    suggested_examples: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="建议的示例",
    )

    # 触发来源
    trigger_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="触发建议的原始消息",
    )
    trigger_event_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="关联的事件 ID",
    )
    trigger_source: Mapped[str] = mapped_column(
        String(20),
        default="email",
        comment="消息来源: email | feishu | web",
    )

    # 审批状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="状态: pending | approved | rejected | merged",
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="审批 Workflow ID",
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

    # 如果批准，关联创建的 Intent
    created_intent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="创建的意图 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_intent_suggestions_status", "status"),
        Index("ix_intent_suggestions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<IntentSuggestion {self.suggested_name} ({self.status})>"


# ==================== 种子数据 ====================

SEED_INTENTS = [
    {
        "name": "inquiry",
        "label": "询价",
        "description": "客户询问产品价格、要求报价、咨询产品信息",
        "examples": [
            "请问产品A多少钱？",
            "能给我发一份报价单吗？",
            "我想了解一下你们的产品价格",
        ],
        "keywords": ["价格", "报价", "多少钱", "费用", "成本"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "QuoteAgent"},
        "escalation_rules": {"amount_gt": 10000},
        "escalation_workflow": "QuoteApprovalWorkflow",
        "priority": 10,
    },
    {
        "name": "complaint",
        "label": "投诉",
        "description": "客户投诉、表达不满、问题反馈、质量问题",
        "examples": [
            "你们的产品质量太差了",
            "我要投诉",
            "这个问题一直没解决",
        ],
        "keywords": ["投诉", "不满", "差", "问题", "退货", "退款"],
        "default_handler": "workflow",
        "handler_config": {"workflow_name": "ComplaintWorkflow"},
        "escalation_rules": {"always": True},
        "escalation_workflow": "ComplaintWorkflow",
        "priority": 20,
    },
    {
        "name": "order",
        "label": "订单",
        "description": "客户下单、确认采购、订购产品",
        "examples": [
            "我要订购100个产品A",
            "请帮我下单",
            "确认采购",
        ],
        "keywords": ["订购", "下单", "采购", "购买", "要买"],
        "default_handler": "workflow",
        "handler_config": {"workflow_name": "OrderWorkflow"},
        "priority": 15,
    },
    {
        "name": "follow_up",
        "label": "跟进",
        "description": "客户跟进之前的事项、询问进度、催促",
        "examples": [
            "上次的报价怎么样了？",
            "订单发货了吗？",
            "进度如何？",
        ],
        "keywords": ["进度", "怎么样了", "跟进", "催", "上次"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent", "notify": True},
        "priority": 5,
    },
    {
        "name": "greeting",
        "label": "问候",
        "description": "打招呼、闲聊、无特定业务意图",
        "examples": [
            "你好",
            "在吗？",
            "早上好",
        ],
        "keywords": ["你好", "在吗", "早上好", "下午好", "晚上好"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent"},
        "priority": 0,
    },
    {
        "name": "other",
        "label": "其他",
        "description": "无法分类的消息、不明确的意图",
        "examples": [],
        "keywords": [],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent", "notify": True},
        "priority": -1,
    },
]
