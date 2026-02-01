# app/api/settings.py
# 系统设置 API
#
# 提供系统配置的管理接口（仅管理员）：
# - LLM 配置（模型、API Key）
# - 邮件配置
# - 其他系统设置

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.core.config import settings as app_settings
from app.core.logging import get_logger
from app.models.user import User
from app.models.settings import SystemSetting

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


# ==================== Schema ====================

class LLMConfigResponse(BaseModel):
    """LLM 配置响应"""
    default_model: str
    available_models: list[dict]
    anthropic_configured: bool
    openai_configured: bool
    volcengine_configured: bool = False  # 豆包
    anthropic_key_preview: Optional[str] = None
    openai_key_preview: Optional[str] = None
    volcengine_key_preview: Optional[str] = None


class LLMConfigUpdate(BaseModel):
    """LLM 配置更新"""
    default_model: Optional[str] = None
    custom_model_id: Optional[str] = None  # 自定义模型 ID（如火山引擎 Endpoint ID）
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    volcengine_api_key: Optional[str] = None  # 豆包 API Key


class EmailConfigResponse(BaseModel):
    """邮件配置响应"""
    smtp_configured: bool
    imap_configured: bool
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None


class EmailConfigUpdate(BaseModel):
    """邮件配置更新"""
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: Optional[bool] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None


class SettingItem(BaseModel):
    """单个设置项"""
    key: str
    value: str
    category: str
    description: Optional[str] = None
    is_sensitive: bool = False


class FeishuConfigResponse(BaseModel):
    """飞书配置响应"""
    enabled: bool = False
    configured: bool = False
    app_id: Optional[str] = None
    app_id_preview: Optional[str] = None  # 遮蔽后的 App ID
    app_secret_configured: bool = False
    encrypt_key_configured: bool = False
    verification_token_configured: bool = False


class FeishuConfigUpdate(BaseModel):
    """飞书配置更新"""
    enabled: Optional[bool] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    encrypt_key: Optional[str] = None
    verification_token: Optional[str] = None


class OSSConfigResponse(BaseModel):
    """OSS 配置响应"""
    configured: bool = False
    endpoint: Optional[str] = None
    bucket: Optional[str] = None
    access_key_id_preview: Optional[str] = None
    access_key_secret_configured: bool = False


class OSSConfigUpdate(BaseModel):
    """OSS 配置更新"""
    endpoint: Optional[str] = None
    bucket: Optional[str] = None
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None


# ==================== 可用模型列表 ====================

AVAILABLE_MODELS = [
    # Anthropic Claude 4 (最新)
    {
        "id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "provider": "anthropic",
        "description": "最强大的 Claude 模型，适合复杂任务",
        "recommended": True,
    },
    {
        "id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "provider": "anthropic",
        "description": "Claude 4 Sonnet 模型，性能均衡",
    },
    # Anthropic Claude 3.5
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "description": "Claude 3.5 Sonnet，性价比高",
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "description": "Claude 3.5 Haiku，快速高效",
    },
    # Anthropic Claude 3
    {
        "id": "claude-3-opus-20240229",
        "name": "Claude 3 Opus",
        "provider": "anthropic",
        "description": "Claude 3 最强大的模型",
    },
    {
        "id": "claude-3-sonnet-20240229",
        "name": "Claude 3 Sonnet",
        "provider": "anthropic",
        "description": "Claude 3 平衡性能和成本",
    },
    {
        "id": "claude-3-haiku-20240307",
        "name": "Claude 3 Haiku",
        "provider": "anthropic",
        "description": "Claude 3 最快速的模型，适合简单任务",
    },
    # OpenAI GPT
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "description": "OpenAI 最新多模态模型",
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "description": "GPT-4 优化版本，更快更便宜",
    },
    {
        "id": "gpt-4",
        "name": "GPT-4",
        "provider": "openai",
        "description": "OpenAI 强大的推理模型",
    },
    {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "description": "性价比高的快速模型",
    },
    # 字节跳动豆包 (Volcengine)
    # 注意：豆包需要使用火山引擎控制台的 Endpoint ID
    # 格式：volcengine/<endpoint_id>
    # 用户需要在火山引擎创建推理接入点后获取 ID
    {
        "id": "volcengine/ep-xxxxxxxx",
        "name": "豆包 (自定义)",
        "provider": "volcengine",
        "description": "请替换 ep-xxxxxxxx 为您的火山引擎 Endpoint ID",
        "custom_endpoint": True,
    },
]


# ==================== 辅助函数 ====================

def mask_api_key(key: str) -> str:
    """遮蔽 API Key，只显示前后几位"""
    if not key or len(key) < 12:
        return "***"
    return f"{key[:8]}...{key[-4:]}"


async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """获取设置值"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(
    db: AsyncSession,
    key: str,
    value: str,
    category: str,
    description: str = None,
    is_sensitive: bool = False,
):
    """设置或更新设置值"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = SystemSetting(
            key=key,
            value=value,
            category=category,
            description=description,
            is_sensitive=is_sensitive,
        )
        db.add(setting)

    await db.commit()


# ==================== LLM 配置接口 ====================

@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 LLM 配置

    返回当前的 LLM 模型设置和 API Key 配置状态
    """
    # 获取数据库中保存的设置
    db_model = await get_setting(db, "llm.default_model")
    db_anthropic_key = await get_setting(db, "llm.anthropic_api_key")
    db_openai_key = await get_setting(db, "llm.openai_api_key")
    db_volcengine_key = await get_setting(db, "llm.volcengine_api_key")

    # 优先使用数据库设置，否则使用环境变量
    # 注意：默认模型现在从 llm_model_config 表加载，已在启动时设置到环境变量
    import os
    default_model = db_model or os.environ.get("DEFAULT_LLM_MODEL") or "未配置"
    anthropic_key = db_anthropic_key or app_settings.ANTHROPIC_API_KEY
    openai_key = db_openai_key or app_settings.OPENAI_API_KEY
    volcengine_key = db_volcengine_key or getattr(app_settings, 'VOLCENGINE_API_KEY', '')

    return LLMConfigResponse(
        default_model=default_model,
        available_models=AVAILABLE_MODELS,
        anthropic_configured=bool(anthropic_key),
        openai_configured=bool(openai_key),
        volcengine_configured=bool(volcengine_key),
        anthropic_key_preview=mask_api_key(anthropic_key) if anthropic_key else None,
        openai_key_preview=mask_api_key(openai_key) if openai_key else None,
        volcengine_key_preview=mask_api_key(volcengine_key) if volcengine_key else None,
    )


@router.put("/llm")
async def update_llm_config(
    config: LLMConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新 LLM 配置

    可以更新默认模型和 API Key
    """
    updated = []

    if config.default_model:
        # 验证模型是否在可用列表中，或者是自定义模型 ID
        valid_models = [m["id"] for m in AVAILABLE_MODELS]
        model_to_use = config.default_model

        # 如果提供了自定义模型 ID，使用它（主要用于火山引擎 Endpoint）
        if config.custom_model_id:
            # 火山引擎模型需要 volcengine/ 前缀
            if config.custom_model_id.startswith("volcengine/") or config.custom_model_id.startswith("ep-"):
                if not config.custom_model_id.startswith("volcengine/"):
                    model_to_use = f"volcengine/{config.custom_model_id}"
                else:
                    model_to_use = config.custom_model_id
            else:
                model_to_use = config.custom_model_id
        elif config.default_model not in valid_models:
            # 允许使用任何以已知 provider 前缀开头的模型
            known_prefixes = ["claude-", "gpt-", "volcengine/", "openai/", "anthropic/"]
            if not any(config.default_model.startswith(p) for p in known_prefixes):
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的模型: {config.default_model}",
                )

        await set_setting(
            db,
            "llm.default_model",
            model_to_use,
            "llm",
            "默认 LLM 模型",
        )
        updated.append("default_model")
        logger.info(f"[Settings] 更新默认模型: {model_to_use}")

    if config.anthropic_api_key:
        await set_setting(
            db,
            "llm.anthropic_api_key",
            config.anthropic_api_key,
            "llm",
            "Anthropic API Key",
            is_sensitive=True,
        )
        updated.append("anthropic_api_key")
        logger.info("[Settings] 更新 Anthropic API Key")

    if config.openai_api_key:
        await set_setting(
            db,
            "llm.openai_api_key",
            config.openai_api_key,
            "llm",
            "OpenAI API Key",
            is_sensitive=True,
        )
        updated.append("openai_api_key")
        logger.info("[Settings] 更新 OpenAI API Key")

    if config.volcengine_api_key:
        await set_setting(
            db,
            "llm.volcengine_api_key",
            config.volcengine_api_key,
            "llm",
            "Volcengine API Key (豆包)",
            is_sensitive=True,
        )
        updated.append("volcengine_api_key")
        logger.info("[Settings] 更新 Volcengine API Key")

    return {
        "success": True,
        "updated": updated,
        "message": f"已更新 {len(updated)} 项设置",
    }


class LLMTestRequest(BaseModel):
    """LLM 测试请求"""
    model_id: Optional[str] = None  # 如果不传，使用默认模型


@router.post("/llm/test")
async def test_llm_connection(
    request: Optional[LLMTestRequest] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    测试 LLM 连接

    发送一个简单请求来验证 API Key 是否有效。
    可以指定 model_id 来测试特定模型，否则使用默认模型。
    """
    from app.llm.gateway import LLMGateway

    # 获取当前配置
    db_model = await get_setting(db, "llm.default_model")
    db_anthropic_key = await get_setting(db, "llm.anthropic_api_key")
    db_openai_key = await get_setting(db, "llm.openai_api_key")
    db_volcengine_key = await get_setting(db, "llm.volcengine_api_key")

    # 确定要测试的模型
    import os
    test_model = (request.model_id if request and request.model_id else None) or db_model or os.environ.get("DEFAULT_LLM_MODEL")

    anthropic_key = db_anthropic_key or app_settings.ANTHROPIC_API_KEY
    openai_key = db_openai_key or app_settings.OPENAI_API_KEY
    volcengine_key = db_volcengine_key or ""

    # 确定使用哪个 provider
    model_info = next(
        (m for m in AVAILABLE_MODELS if m["id"] == test_model),
        None
    )

    # 如果不在预设列表中，根据模型 ID 推断 provider
    if model_info:
        provider = model_info["provider"]
    elif test_model.startswith("volcengine/") or test_model.startswith("ep-"):
        provider = "volcengine"
    elif test_model.startswith("gpt-") or test_model.startswith("openai/"):
        provider = "openai"
    elif test_model.startswith("claude-") or test_model.startswith("anthropic/"):
        provider = "anthropic"
    else:
        return {
            "success": False,
            "error": f"无法识别模型的 provider: {test_model}",
        }

    # 根据 provider 选择 API key
    if provider == "anthropic":
        api_key = anthropic_key
    elif provider == "openai":
        api_key = openai_key
    elif provider == "volcengine":
        api_key = volcengine_key
    else:
        api_key = ""

    if not api_key:
        provider_names = {
            "anthropic": "Anthropic",
            "openai": "OpenAI",
            "volcengine": "豆包 (Volcengine)",
        }
        return {
            "success": False,
            "error": f"{provider_names.get(provider, provider)} API Key 未配置",
        }

    try:
        # 临时设置 API Key（如果是从数据库获取的）
        import os
        if provider == "anthropic" and db_anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = db_anthropic_key
        elif provider == "openai" and db_openai_key:
            os.environ["OPENAI_API_KEY"] = db_openai_key
        elif provider == "volcengine" and db_volcengine_key:
            os.environ["VOLCENGINE_API_KEY"] = db_volcengine_key

        gateway = LLMGateway()
        # 使用正确的参数格式：message 是字符串
        result = await gateway.chat(
            message="Hi, just testing. Reply with 'OK'.",
            model=test_model,
            max_tokens=10,
        )

        return {
            "success": True,
            "model": test_model,
            "provider": provider,
            "response": result.content[:50] if result.content else "",
        }

    except Exception as e:
        logger.error(f"[Settings] LLM 测试失败: {e}")
        return {
            "success": False,
            "model": test_model,
            "provider": provider,
            "error": str(e),
        }


# ==================== 邮件配置接口 ====================

@router.get("/email", response_model=EmailConfigResponse)
async def get_email_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取邮件配置"""
    # 从数据库获取或使用环境变量
    smtp_host = await get_setting(db, "email.smtp_host") or app_settings.SMTP_HOST
    smtp_port = await get_setting(db, "email.smtp_port")
    smtp_user = await get_setting(db, "email.smtp_user") or app_settings.SMTP_USER
    imap_host = await get_setting(db, "email.imap_host") or app_settings.IMAP_HOST
    imap_port = await get_setting(db, "email.imap_port")
    imap_user = await get_setting(db, "email.imap_user") or app_settings.IMAP_USER

    return EmailConfigResponse(
        smtp_configured=bool(smtp_host and smtp_user),
        imap_configured=bool(imap_host and imap_user),
        smtp_host=smtp_host or None,
        smtp_port=int(smtp_port) if smtp_port else app_settings.SMTP_PORT,
        smtp_user=smtp_user or None,
        imap_host=imap_host or None,
        imap_port=int(imap_port) if imap_port else app_settings.IMAP_PORT,
        imap_user=imap_user or None,
    )


@router.put("/email")
async def update_email_config(
    config: EmailConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新邮件配置"""
    updated = []

    if config.smtp_host is not None:
        await set_setting(db, "email.smtp_host", config.smtp_host, "email", "SMTP 服务器")
        updated.append("smtp_host")

    if config.smtp_port is not None:
        await set_setting(db, "email.smtp_port", str(config.smtp_port), "email", "SMTP 端口")
        updated.append("smtp_port")

    if config.smtp_user is not None:
        await set_setting(db, "email.smtp_user", config.smtp_user, "email", "SMTP 用户名")
        updated.append("smtp_user")

    if config.smtp_password is not None:
        await set_setting(db, "email.smtp_password", config.smtp_password, "email", "SMTP 密码", is_sensitive=True)
        updated.append("smtp_password")

    if config.imap_host is not None:
        await set_setting(db, "email.imap_host", config.imap_host, "email", "IMAP 服务器")
        updated.append("imap_host")

    if config.imap_port is not None:
        await set_setting(db, "email.imap_port", str(config.imap_port), "email", "IMAP 端口")
        updated.append("imap_port")

    if config.imap_user is not None:
        await set_setting(db, "email.imap_user", config.imap_user, "email", "IMAP 用户名")
        updated.append("imap_user")

    if config.imap_password is not None:
        await set_setting(db, "email.imap_password", config.imap_password, "email", "IMAP 密码", is_sensitive=True)
        updated.append("imap_password")

    logger.info(f"[Settings] 更新邮件配置: {updated}")

    return {
        "success": True,
        "updated": updated,
        "message": f"已更新 {len(updated)} 项设置",
    }


# ==================== 通用设置接口 ====================

@router.get("/all")
async def get_all_settings(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有设置

    可选按分类筛选
    """
    query = select(SystemSetting)
    if category:
        query = query.where(SystemSetting.category == category)

    result = await db.execute(query)
    settings = result.scalars().all()

    return [
        {
            "key": s.key,
            "value": mask_api_key(s.value) if s.is_sensitive else s.value,
            "category": s.category,
            "description": s.description,
            "is_sensitive": s.is_sensitive,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in settings
    ]


# ==================== 飞书配置接口 ====================

@router.get("/feishu", response_model=FeishuConfigResponse)
async def get_feishu_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取飞书配置

    返回飞书机器人的配置状态
    """
    # 从数据库获取配置
    enabled = await get_setting(db, "feishu.enabled")
    app_id = await get_setting(db, "feishu.app_id")
    app_secret = await get_setting(db, "feishu.app_secret")
    encrypt_key = await get_setting(db, "feishu.encrypt_key")
    verification_token = await get_setting(db, "feishu.verification_token")

    return FeishuConfigResponse(
        enabled=enabled == "true" if enabled else False,
        configured=bool(app_id and app_secret),
        app_id=app_id,
        app_id_preview=mask_api_key(app_id) if app_id else None,
        app_secret_configured=bool(app_secret),
        encrypt_key_configured=bool(encrypt_key),
        verification_token_configured=bool(verification_token),
    )


@router.put("/feishu")
async def update_feishu_config(
    config: FeishuConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新飞书配置

    可以更新 App ID、App Secret 和启用状态
    """
    updated = []

    if config.enabled is not None:
        await set_setting(
            db,
            "feishu.enabled",
            "true" if config.enabled else "false",
            "feishu",
            "飞书机器人启用状态",
        )
        updated.append("enabled")
        logger.info(f"[Settings] 飞书机器人 {'启用' if config.enabled else '禁用'}")

    if config.app_id is not None:
        await set_setting(
            db,
            "feishu.app_id",
            config.app_id,
            "feishu",
            "飞书应用 App ID",
        )
        updated.append("app_id")
        logger.info("[Settings] 更新飞书 App ID")

    if config.app_secret is not None:
        await set_setting(
            db,
            "feishu.app_secret",
            config.app_secret,
            "feishu",
            "飞书应用 App Secret",
            is_sensitive=True,
        )
        updated.append("app_secret")
        logger.info("[Settings] 更新飞书 App Secret")

    if config.encrypt_key is not None:
        await set_setting(
            db,
            "feishu.encrypt_key",
            config.encrypt_key,
            "feishu",
            "飞书加密 Key",
            is_sensitive=True,
        )
        updated.append("encrypt_key")
        logger.info("[Settings] 更新飞书 Encrypt Key")

    if config.verification_token is not None:
        await set_setting(
            db,
            "feishu.verification_token",
            config.verification_token,
            "feishu",
            "飞书验证 Token",
            is_sensitive=True,
        )
        updated.append("verification_token")
        logger.info("[Settings] 更新飞书 Verification Token")

    return {
        "success": True,
        "updated": updated,
        "message": f"已更新 {len(updated)} 项飞书配置",
    }


@router.get("/feishu/status")
async def get_feishu_worker_status(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取飞书 Worker 运行状态

    返回 Worker 是否正在运行
    """
    from app.workers.feishu_worker import get_feishu_worker_status as get_status

    # 获取配置状态
    enabled = await get_setting(db, "feishu.enabled")
    app_id = await get_setting(db, "feishu.app_id")
    app_secret = await get_setting(db, "feishu.app_secret")

    # 获取 Worker 运行状态
    worker_status = get_status()

    return {
        "enabled": enabled == "true" if enabled else False,
        "configured": bool(app_id and app_secret),
        "worker_running": worker_status["running"],
        "worker_pid": worker_status.get("pid"),
        "message": f"Worker 运行中 (PID: {worker_status.get('pid')})" if worker_status["running"] else "Worker 未运行",
    }


@router.post("/feishu/test")
async def test_feishu_connection(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    测试飞书连接

    使用配置的 App ID 和 App Secret 测试是否能获取 access_token
    """
    from app.adapters.feishu import FeishuClient

    # 获取配置
    app_id = await get_setting(db, "feishu.app_id")
    app_secret = await get_setting(db, "feishu.app_secret")

    if not app_id or not app_secret:
        return {
            "success": False,
            "error": "飞书 App ID 或 App Secret 未配置",
        }

    try:
        # 创建客户端并测试连接
        client = FeishuClient(app_id=app_id, app_secret=app_secret)
        is_connected = await client.test_connection()

        if is_connected:
            return {
                "success": True,
                "message": "飞书连接测试成功",
                "app_id": mask_api_key(app_id),
            }
        else:
            return {
                "success": False,
                "error": "无法获取飞书 access_token，请检查 App ID 和 App Secret",
            }

    except Exception as e:
        logger.error(f"[Settings] 飞书连接测试失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ==================== OSS 配置接口 ====================

@router.get("/oss", response_model=OSSConfigResponse)
async def get_oss_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 OSS 配置

    返回阿里云 OSS 的配置状态
    """
    # 从数据库获取配置，如果没有则使用环境变量
    db_endpoint = await get_setting(db, "oss.endpoint")
    db_bucket = await get_setting(db, "oss.bucket")
    db_access_key_id = await get_setting(db, "oss.access_key_id")
    db_access_key_secret = await get_setting(db, "oss.access_key_secret")

    endpoint = db_endpoint or getattr(app_settings, "OSS_ENDPOINT", None)
    bucket = db_bucket or getattr(app_settings, "OSS_BUCKET", None)
    access_key_id = db_access_key_id or getattr(app_settings, "OSS_ACCESS_KEY_ID", None)
    access_key_secret = db_access_key_secret or getattr(app_settings, "OSS_ACCESS_KEY_SECRET", None)

    return OSSConfigResponse(
        configured=bool(endpoint and bucket and access_key_id and access_key_secret),
        endpoint=endpoint,
        bucket=bucket,
        access_key_id_preview=mask_api_key(access_key_id) if access_key_id else None,
        access_key_secret_configured=bool(access_key_secret),
    )


@router.put("/oss")
async def update_oss_config(
    config: OSSConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新 OSS 配置

    更新后需要重启服务或调用重新连接接口
    """
    updated = []

    if config.endpoint is not None:
        await set_setting(
            db,
            "oss.endpoint",
            config.endpoint,
            "oss",
            "OSS Endpoint（如 oss-cn-hangzhou.aliyuncs.com）",
        )
        updated.append("endpoint")
        logger.info(f"[Settings] 更新 OSS Endpoint: {config.endpoint}")

    if config.bucket is not None:
        await set_setting(
            db,
            "oss.bucket",
            config.bucket,
            "oss",
            "OSS Bucket 名称",
        )
        updated.append("bucket")
        logger.info(f"[Settings] 更新 OSS Bucket: {config.bucket}")

    if config.access_key_id is not None:
        await set_setting(
            db,
            "oss.access_key_id",
            config.access_key_id,
            "oss",
            "OSS Access Key ID",
            is_sensitive=True,
        )
        updated.append("access_key_id")
        logger.info("[Settings] 更新 OSS Access Key ID")

    if config.access_key_secret is not None:
        await set_setting(
            db,
            "oss.access_key_secret",
            config.access_key_secret,
            "oss",
            "OSS Access Key Secret",
            is_sensitive=True,
        )
        updated.append("access_key_secret")
        logger.info("[Settings] 更新 OSS Access Key Secret")

    # 重新初始化 OSS 客户端
    if updated:
        from app.storage.oss import oss_client
        oss_client._initialized = False  # 强制下次使用时重新连接

    return {
        "success": True,
        "updated": updated,
        "message": f"已更新 {len(updated)} 项 OSS 配置",
    }


@router.post("/oss/test")
async def test_oss_connection(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    测试 OSS 连接

    尝试列出 Bucket 中的文件来验证配置是否正确
    """
    from app.storage.oss import OSSClient
    import oss2

    # 获取配置
    db_endpoint = await get_setting(db, "oss.endpoint")
    db_bucket = await get_setting(db, "oss.bucket")
    db_access_key_id = await get_setting(db, "oss.access_key_id")
    db_access_key_secret = await get_setting(db, "oss.access_key_secret")

    endpoint = db_endpoint or getattr(app_settings, "OSS_ENDPOINT", None)
    bucket = db_bucket or getattr(app_settings, "OSS_BUCKET", None)
    access_key_id = db_access_key_id or getattr(app_settings, "OSS_ACCESS_KEY_ID", None)
    access_key_secret = db_access_key_secret or getattr(app_settings, "OSS_ACCESS_KEY_SECRET", None)

    if not all([endpoint, bucket, access_key_id, access_key_secret]):
        missing = []
        if not endpoint:
            missing.append("Endpoint")
        if not bucket:
            missing.append("Bucket")
        if not access_key_id:
            missing.append("Access Key ID")
        if not access_key_secret:
            missing.append("Access Key Secret")
        return {
            "success": False,
            "error": f"OSS 配置不完整，缺少: {', '.join(missing)}",
        }

    try:
        # 创建临时连接测试
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket_obj = oss2.Bucket(auth, endpoint, bucket)

        # 尝试列出文件（最多1个）来验证连接
        result = list(oss2.ObjectIterator(bucket_obj, max_keys=1))

        return {
            "success": True,
            "message": "OSS 连接测试成功",
            "bucket": bucket,
            "endpoint": endpoint,
        }

    except oss2.exceptions.AccessDenied as e:
        error_details = {
            "status": getattr(e, 'status', None),
            "request_id": getattr(e, 'request_id', None),
            "code": getattr(e, 'code', None),
            "message": getattr(e, 'message', None),
            "details": str(e),
        }
        logger.error(f"[Settings] OSS 访问被拒绝: {error_details}")

        # 根据错误代码提供更具体的提示
        error_message = "访问被拒绝，请检查 Access Key 权限"
        if hasattr(e, 'code'):
            if e.code == 'InvalidAccessKeyId':
                error_message = "Access Key ID 无效，请检查是否正确"
            elif e.code == 'SignatureDoesNotMatch':
                error_message = "Access Key Secret 错误，请检查密钥"
            elif e.code == 'AccessDenied':
                error_message = f"权限不足。该 Access Key 没有访问 Bucket '{bucket}' 的权限，请在 RAM 控制台添加 oss:GetObject 和 oss:ListObjects 权限"

        return {
            "success": False,
            "error": error_message,
            "details": error_details,
        }
    except oss2.exceptions.NoSuchBucket as e:
        logger.error(f"[Settings] OSS Bucket 不存在: {e}")
        return {
            "success": False,
            "error": f"Bucket '{bucket}' 不存在，请先在 OSS 控制台创建",
        }
    except Exception as e:
        logger.error(f"[Settings] OSS 连接测试失败: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[Settings] 错误堆栈: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
        }
