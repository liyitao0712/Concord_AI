# app/models/prompt.py
# Prompt 模板数据模型
#
# 设计说明：
# 1. Prompt 存储在数据库，支持管理员在前端修改
# 2. 代码中只保留默认值作为 fallback
# 3. 支持版本管理，便于回滚
# 4. 支持变量插值 (Jinja2 风格)

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    JSON,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Prompt(Base):
    """
    Prompt 模板模型

    用于存储 LLM 调用的提示词模板，支持：
    - 管理员在线编辑
    - 版本管理
    - 变量定义
    - 多语言（可选）

    Example:
        prompt = Prompt(
            name="intent_classifier",
            category="agent",
            content="你是一个意图分类助手。请分析以下内容：\n\n{{content}}\n\n请返回意图类型。",
            variables={"content": "用户输入的内容"},
            description="用于分类用户意图的提示词",
        )
    """

    __tablename__ = "prompts"

    # 主键
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="主键ID"
    )

    # 名称（唯一标识，代码中使用）
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Prompt 名称（代码标识符）"
    )

    # 分类
    category = Column(
        String(50),
        nullable=False,
        default="general",
        comment="分类：agent, tool, system, chat"
    )

    # 显示名称（管理后台展示）
    display_name = Column(
        String(200),
        nullable=True,
        comment="显示名称（中文）"
    )

    # Prompt 内容（支持 Jinja2 变量）
    content = Column(
        Text,
        nullable=False,
        comment="Prompt 模板内容"
    )

    # 变量定义（JSON，描述可用变量）
    variables = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="变量定义 {变量名: 说明}"
    )

    # 描述说明
    description = Column(
        Text,
        nullable=True,
        comment="用途说明"
    )

    # 版本号
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="版本号"
    )

    # 是否激活
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )

    # 模型建议（可选）
    model_hint = Column(
        String(50),
        nullable=True,
        comment="建议使用的模型：claude-3-opus, gpt-4, etc."
    )

    # 时间戳
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )

    # 创建者
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="创建者用户ID"
    )

    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="最后修改者用户ID"
    )

    # 索引
    __table_args__ = (
        Index("ix_prompts_category", "category"),
        Index("ix_prompts_active", "is_active"),
    )

    def __repr__(self):
        return f"<Prompt(name='{self.name}', version={self.version})>"

    def render(self, **kwargs) -> str:
        """
        渲染 Prompt 模板

        使用简单的字符串替换（Jinja2 风格）

        Args:
            **kwargs: 变量值

        Returns:
            str: 渲染后的 Prompt

        Example:
            prompt.render(content="用户的邮件内容...")
        """
        result = self.content
        for key, value in kwargs.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result


class PromptHistory(Base):
    """
    Prompt 历史版本

    每次修改 Prompt 时自动保存历史版本，支持回滚
    """

    __tablename__ = "prompt_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="主键ID"
    )

    # 关联的 Prompt
    prompt_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="原 Prompt ID"
    )

    prompt_name = Column(
        String(100),
        nullable=False,
        comment="Prompt 名称（冗余存储，防止原记录删除）"
    )

    # 历史内容
    content = Column(
        Text,
        nullable=False,
        comment="历史版本内容"
    )

    variables = Column(
        JSON,
        nullable=True,
        comment="历史版本变量"
    )

    version = Column(
        Integer,
        nullable=False,
        comment="版本号"
    )

    # 修改信息
    changed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="修改时间"
    )

    changed_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="修改者用户ID"
    )

    change_reason = Column(
        String(500),
        nullable=True,
        comment="修改原因"
    )

    __table_args__ = (
        Index("ix_prompt_history_prompt_id", "prompt_id"),
        Index("ix_prompt_history_version", "prompt_id", "version"),
    )
