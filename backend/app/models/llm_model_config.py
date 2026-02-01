"""
LLM 模型配置模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class LLMModelConfig(Base):
    """LLM 模型配置表"""
    __tablename__ = "llm_model_configs"

    # 主键
    id = Column(String(36), primary_key=True)

    # 模型标识
    model_id = Column(String(100), unique=True, nullable=False, index=True, comment="模型 ID，如：gemini/gemini-1.5-pro")
    provider = Column(String(50), nullable=False, index=True, comment="提供商：gemini, qwen, anthropic 等")
    model_name = Column(String(100), nullable=False, comment="显示名称：Gemini 1.5 Pro")

    # API 配置
    api_key = Column(Text, nullable=True, comment="该模型的 API Key（敏感）")
    api_endpoint = Column(Text, nullable=True, comment="自定义 API 端点（可选）")

    # 使用统计
    total_requests = Column(Integer, nullable=False, default=0, server_default="0", comment="总请求次数")
    total_tokens = Column(BigInteger, nullable=False, default=0, server_default="0", comment="总消耗 Token 数")
    last_used_at = Column(DateTime, nullable=True, comment="最后使用时间")

    # 状态
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="true", index=True, comment="是否启用")
    is_configured = Column(Boolean, nullable=False, default=False, server_default="false", index=True, comment="是否已配置（有 API Key）")

    # 元数据
    description = Column(Text, nullable=True, comment="模型描述")
    parameters = Column(JSON, nullable=True, comment="默认参数（temperature, max_tokens 等）")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    def to_dict(self, include_api_key: bool = False) -> dict:
        """转换为字典"""
        result = {
            "id": self.id,
            "model_id": self.model_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "api_endpoint": self.api_endpoint,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_enabled": self.is_enabled,
            "is_configured": self.is_configured,
            "description": self.description,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只在需要时包含完整的 API Key
        if include_api_key:
            result["api_key"] = self.api_key
        else:
            # 只显示前几位和后几位，中间用 * 遮蔽
            if self.api_key:
                key = self.api_key
                if len(key) > 10:
                    result["api_key_preview"] = f"{key[:4]}...{key[-4:]}"
                else:
                    result["api_key_preview"] = "****"
            else:
                result["api_key_preview"] = None

        return result
