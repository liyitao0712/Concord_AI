# app/api/settings.py
# 系统设置 API
#
# 提供系统配置的管理接口（仅管理员）：
# - 公司信息配置
# - 邮件配置
# - 飞书配置
# - OSS 配置
#
# 注意：LLM 配置已统一到 llm_models.py（/admin/llm/models），
# API Key 唯一数据源为 llm_model_configs 表。

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


# ==================== 公司信息配置接口 ====================

# 公司信息 key 定义
COMPANY_SETTINGS_KEYS = {
    "company.name": {"description": "公司英文名称", "example": "Concord Tools Limited"},
    "company.name_zh": {"description": "公司中文名称", "example": "广州协和工具有限公司"},
    "company.industry": {"description": "所属行业", "example": "外贸五金工具"},
    "company.context": {"description": "业务背景描述（会注入到所有 AI 分析 Prompt 中）", "example": "Concord 是一家外贸公司，主营五金工具出口，客户主要在欧美市场"},
    "company.email_domains": {"description": "公司邮箱域名（逗号分隔，用于识别内部邮件）", "example": "concordtools.com"},
}


class CompanyConfigResponse(BaseModel):
    """公司信息配置响应"""
    name: Optional[str] = None
    name_zh: Optional[str] = None
    industry: Optional[str] = None
    context: Optional[str] = None
    email_domains: Optional[str] = None


class CompanyConfigUpdate(BaseModel):
    """公司信息配置更新（所有字段可选，只更新传入的字段）"""
    name: Optional[str] = None
    name_zh: Optional[str] = None
    industry: Optional[str] = None
    context: Optional[str] = None
    email_domains: Optional[str] = None


@router.get("/company", response_model=CompanyConfigResponse)
async def get_company_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取公司信息配置

    这些信息会作为系统变量自动注入到所有 AI Prompt 中，
    可在 Prompt 模板中通过 {{company_name}}、{{company_context}} 等引用。
    """
    return CompanyConfigResponse(
        name=await get_setting(db, "company.name"),
        name_zh=await get_setting(db, "company.name_zh"),
        industry=await get_setting(db, "company.industry"),
        context=await get_setting(db, "company.context"),
        email_domains=await get_setting(db, "company.email_domains"),
    )


@router.put("/company")
async def update_company_config(
    config: CompanyConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新公司信息配置

    更新后会自动刷新 Prompt 缓存，后续所有 AI 分析将使用新的公司信息。
    """
    updated = []

    # 遍历所有字段，只更新传入的
    field_to_key = {
        "name": "company.name",
        "name_zh": "company.name_zh",
        "industry": "company.industry",
        "context": "company.context",
        "email_domains": "company.email_domains",
    }

    for field_name, setting_key in field_to_key.items():
        value = getattr(config, field_name, None)
        if value is not None:
            desc = COMPANY_SETTINGS_KEYS[setting_key]["description"]
            await set_setting(db, setting_key, value, "company", desc)
            updated.append(field_name)
            logger.info(f"[Settings] 更新公司信息: {setting_key}")

    # 刷新 Prompt 缓存中的系统变量
    if updated:
        from app.llm.prompts import prompt_manager
        await prompt_manager.refresh_cache()

    return {
        "success": True,
        "updated": updated,
        "message": f"已更新 {len(updated)} 项公司信息",
        "hint": "可在 Prompt 模板中使用 {{company_name}}、{{company_name_zh}}、{{company_industry}}、{{company_context}}、{{company_email_domains}} 引用",
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
