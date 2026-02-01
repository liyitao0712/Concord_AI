# app/llm/__init__.py
# LLM Gateway 模块
#
# 提供统一的 LLM 调用接口，支持：
# - 多模型切换 (Claude, GPT, 本地模型)
# - Prompt 模板管理
# - 调用日志和监控
# - 流式输出

from app.llm.gateway import (
    LLMGateway,
    llm_gateway,
    chat,
    chat_stream,
)
from app.llm.settings_loader import (
    load_llm_settings,
    apply_llm_settings,
    get_default_model,
)

__all__ = [
    "LLMGateway",
    "llm_gateway",
    "chat",
    "chat_stream",
    "load_llm_settings",
    "apply_llm_settings",
    "get_default_model",
]
