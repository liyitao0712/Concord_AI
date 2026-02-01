# app/llm/prompts/__init__.py
# Prompt 管理模块
#
# 提供 Prompt 的加载、渲染、缓存功能
# 优先从数据库加载，fallback 到默认值

from app.llm.prompts.manager import (
    PromptManager,
    prompt_manager,
    get_prompt,
    render_prompt,
)
from app.llm.prompts.defaults import DEFAULT_PROMPTS

__all__ = [
    "PromptManager",
    "prompt_manager",
    "get_prompt",
    "render_prompt",
    "DEFAULT_PROMPTS",
]
