# app/llm/settings_loader.py
# LLM 设置加载器
#
# 从数据库加载 LLM 设置，并应用到环境变量
# 这样 LiteLLM 可以直接使用

import os
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def load_llm_settings(db: AsyncSession) -> dict:
    """
    从数据库加载 LLM 设置

    Returns:
        dict: {
            "default_model": str,
            "anthropic_api_key": str | None,
            "openai_api_key": str | None,
        }
    """
    from app.models.settings import SystemSetting
    from app.models import LLMModelConfig

    # 从 llm_model_config 表获取第一个已配置的模型作为默认模型
    model_query = select(LLMModelConfig).where(
        LLMModelConfig.is_enabled == True,
        LLMModelConfig.is_configured == True
    ).order_by(LLMModelConfig.created_at).limit(1)
    model_result = await db.execute(model_query)
    first_model = model_result.scalar_one_or_none()

    result = {
        "default_model": first_model.model_id if first_model else None,
        "anthropic_api_key": app_settings.ANTHROPIC_API_KEY or None,
        "openai_api_key": app_settings.OPENAI_API_KEY or None,
    }

    try:
        # 查询 LLM 相关设置
        query = select(SystemSetting).where(SystemSetting.category == "llm")
        db_result = await db.execute(query)
        settings_list = db_result.scalars().all()

        for setting in settings_list:
            if setting.key == "llm.default_model":
                result["default_model"] = setting.value
            elif setting.key == "llm.anthropic_api_key":
                result["anthropic_api_key"] = setting.value
            elif setting.key == "llm.openai_api_key":
                result["openai_api_key"] = setting.value

    except Exception as e:
        logger.warning(f"[LLM Settings] 从数据库加载设置失败，使用默认值: {e}")

    return result


async def apply_llm_settings(db: AsyncSession) -> None:
    """
    加载 LLM 设置并应用到环境变量

    这个函数应该在需要使用 LLM 之前调用
    """
    settings = await load_llm_settings(db)

    # 设置 API Key 到环境变量（LiteLLM 会自动读取）
    if settings["anthropic_api_key"]:
        os.environ["ANTHROPIC_API_KEY"] = settings["anthropic_api_key"]
        logger.debug("[LLM Settings] 已设置 ANTHROPIC_API_KEY")

    if settings["openai_api_key"]:
        os.environ["OPENAI_API_KEY"] = settings["openai_api_key"]
        logger.debug("[LLM Settings] 已设置 OPENAI_API_KEY")


async def get_default_model(db: AsyncSession) -> str:
    """获取默认模型名称"""
    settings = await load_llm_settings(db)
    return settings["default_model"]


async def load_agent_config(db: AsyncSession, agent_name: str) -> dict:
    """
    加载特定 Agent 的配置

    Args:
        db: 数据库会话
        agent_name: Agent 名称，如 "chat_agent"

    Returns:
        dict: {
            "model": str | None,           # 模型 ID，如 "gemini/gemini-1.5-pro"
            "temperature": float | None,   # 温度参数
            "max_tokens": int | None,      # 最大 Token 数
            "enabled": bool                # 是否启用
        }
    """
    from app.models.settings import SystemSetting

    result = {
        "model": None,
        "temperature": None,
        "max_tokens": None,
        "enabled": True,
    }

    try:
        # 查询 agent.{agent_name}.* 的所有配置
        prefix = f"agent.{agent_name}."
        query = select(SystemSetting).where(
            SystemSetting.category == "agent",
            SystemSetting.key.like(f"{prefix}%")
        )
        db_result = await db.execute(query)
        settings_list = db_result.scalars().all()

        for setting in settings_list:
            key_suffix = setting.key.replace(prefix, "")
            if key_suffix == "model":
                result["model"] = setting.value
            elif key_suffix == "temperature":
                try:
                    result["temperature"] = float(setting.value)
                except (ValueError, TypeError):
                    logger.warning(f"[Agent Config] 无法解析 {agent_name} 的 temperature: {setting.value}")
            elif key_suffix == "max_tokens":
                try:
                    result["max_tokens"] = int(setting.value)
                except (ValueError, TypeError):
                    logger.warning(f"[Agent Config] 无法解析 {agent_name} 的 max_tokens: {setting.value}")
            elif key_suffix == "enabled":
                result["enabled"] = setting.value.lower() == "true"

        logger.debug(f"[Agent Config] 加载 {agent_name} 配置: {result}")

    except Exception as e:
        logger.warning(f"[Agent Config] 从数据库加载 {agent_name} 配置失败: {e}")

    return result
