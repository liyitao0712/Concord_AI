# app/llm/settings_loader.py
# LLM 设置加载器
#
# 从 llm_model_configs 表加载 LLM 设置，并应用到环境变量
# 这样 LiteLLM 和 Anthropic SDK 可以直接使用
#
# 唯一数据源：llm_model_configs 表（通过 /admin/llm 页面管理）

import os
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

# provider → 环境变量名 映射
_PROVIDER_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "volcengine": "VOLCENGINE_API_KEY",
}


async def load_llm_settings(db: AsyncSession) -> dict:
    """
    从 llm_model_configs 表加载 LLM 设置

    数据源：llm_model_configs 表（唯一来源，通过 /admin/llm 页面管理）

    Returns:
        dict: {
            "default_model": str | None,
            "api_keys": {env_var_name: api_key, ...}
        }
    """
    from app.models import LLMModelConfig

    result = {
        "default_model": None,
        "api_keys": {},
    }

    try:
        # 查询所有已配置且启用的模型
        query = select(LLMModelConfig).where(
            LLMModelConfig.is_enabled == True,
            LLMModelConfig.is_configured == True,
        ).order_by(LLMModelConfig.created_at)

        db_result = await db.execute(query)
        models = db_result.scalars().all()

        if not models:
            logger.warning("[LLM Settings] 数据库中没有已配置的 LLM 模型")
            return result

        # 第一个模型作为默认模型
        result["default_model"] = models[0].model_id

        # 按 provider 提取 API Key（每个 provider 取第一个有 Key 的模型）
        for model in models:
            if model.api_key and model.provider in _PROVIDER_ENV_MAP:
                env_key = _PROVIDER_ENV_MAP[model.provider]
                if env_key not in result["api_keys"]:
                    result["api_keys"][env_key] = model.api_key

    except Exception as e:
        logger.warning(f"[LLM Settings] 从数据库加载设置失败: {e}")

    return result


async def apply_llm_settings(db: AsyncSession) -> None:
    """
    从 llm_model_configs 加载设置并应用到环境变量

    这个函数应该在需要使用 LLM 之前调用。
    会将 API Key 设置到环境变量，供 LiteLLM 和 Anthropic SDK 使用。
    """
    settings = await load_llm_settings(db)

    # 设置默认模型
    if settings["default_model"]:
        os.environ["DEFAULT_LLM_MODEL"] = settings["default_model"]

    # 设置 API Key 到环境变量
    for env_key, api_key in settings["api_keys"].items():
        os.environ[env_key] = api_key
        logger.debug(f"[LLM Settings] 已设置 {env_key}")


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
