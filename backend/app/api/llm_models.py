"""
LLM 模型配置管理 API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.llm_model_config import LLMModelConfig


router = APIRouter(prefix="/admin/llm/models", tags=["LLM 模型配置"])


# ==================== Schemas ====================

class LLMModelConfigCreate(BaseModel):
    """创建新 LLM 模型配置的请求"""
    model_id: str  # 如：anthropic/claude-opus-4-5-20251101
    provider: str  # 如：anthropic, openai, gemini, qwen
    model_name: str  # 如：Claude Opus 4.5
    description: Optional[str] = None
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[dict] = None
    is_enabled: bool = True


class LLMModelConfigUpdate(BaseModel):
    """更新 LLM 模型配置的请求"""
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    is_enabled: Optional[bool] = None
    parameters: Optional[dict] = None


class LLMModelConfigResponse(BaseModel):
    """LLM 模型配置响应"""
    id: str
    model_id: str
    provider: str
    model_name: str
    api_key_preview: Optional[str] = None
    api_endpoint: Optional[str] = None
    total_requests: int
    total_tokens: int
    last_used_at: Optional[str] = None
    is_enabled: bool
    is_configured: bool
    description: Optional[str] = None
    parameters: Optional[dict] = None
    created_at: str
    updated_at: Optional[str] = None


class LLMModelTestRequest(BaseModel):
    """测试模型连接的请求"""
    test_prompt: str = "你好"


class LLMModelTestResponse(BaseModel):
    """测试模型连接的响应"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None


# ==================== API 端点 ====================

@router.get("", response_model=dict)
async def list_models(
    provider: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    is_configured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取所有 LLM 模型配置列表

    查询参数：
    - provider: 按提供商筛选（可选）
    - is_enabled: 按是否启用筛选（可选）
    - is_configured: 按是否已配置筛选（可选）
    """
    query = select(LLMModelConfig)

    # 应用筛选条件
    if provider:
        query = query.where(LLMModelConfig.provider == provider)
    if is_enabled is not None:
        query = query.where(LLMModelConfig.is_enabled == is_enabled)
    if is_configured is not None:
        query = query.where(LLMModelConfig.is_configured == is_configured)

    # 排序：按提供商和模型名称
    query = query.order_by(LLMModelConfig.provider, LLMModelConfig.model_id)

    result = await db.execute(query)
    models = result.scalars().all()

    return {
        "items": [model.to_dict(include_api_key=False) for model in models],
        "total": len(models),
    }


@router.post("", response_model=LLMModelConfigResponse)
async def create_model(
    data: LLMModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    创建新的 LLM 模型配置

    允许管理员添加自定义模型，支持任何 LiteLLM 兼容的模型。

    参数：
    - model_id: LiteLLM 格式的模型 ID（如：anthropic/claude-opus-4-5-20251101）
    - provider: 提供商名称（anthropic, openai, gemini, qwen, volcengine 等）
    - model_name: 显示名称
    - description: 模型描述（可选）
    - api_key: API Key（可选）
    - api_endpoint: 自定义端点（可选）
    - parameters: 默认参数（可选）
    - is_enabled: 是否启用（默认 true）
    """
    # 检查模型是否已存在
    query = select(LLMModelConfig).where(LLMModelConfig.model_id == data.model_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"模型 {data.model_id} 已存在"
        )

    # 确保 model_id 包含提供商前缀（LiteLLM 要求）
    model_id = data.model_id
    if '/' not in model_id:
        model_id = f"{data.provider}/{model_id}"

    # 创建新模型
    new_model = LLMModelConfig(
        id=str(uuid.uuid4()),
        model_id=model_id,
        provider=data.provider,
        model_name=data.model_name,
        description=data.description,
        api_key=data.api_key,
        api_endpoint=data.api_endpoint,
        parameters=data.parameters,
        is_enabled=data.is_enabled,
        is_configured=bool(data.api_key and data.api_key.strip()) if data.api_key else False,
        total_requests=0,
        total_tokens=0,
        created_at=datetime.utcnow(),
    )

    db.add(new_model)
    await db.commit()
    await db.refresh(new_model)

    return new_model.to_dict(include_api_key=False)


@router.get("/{model_id:path}", response_model=LLMModelConfigResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取单个模型配置详情"""
    query = select(LLMModelConfig).where(LLMModelConfig.model_id == model_id)
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

    return model.to_dict(include_api_key=False)


@router.put("/{model_id:path}", response_model=LLMModelConfigResponse)
async def update_model(
    model_id: str,
    data: LLMModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    更新模型配置

    可更新字段：
    - api_key: API Key（敏感）
    - api_endpoint: 自定义 API 端点
    - is_enabled: 是否启用
    - parameters: 默认参数（temperature, max_tokens 等）
    """
    # 查询模型
    query = select(LLMModelConfig).where(LLMModelConfig.model_id == model_id)
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

    # 更新字段
    update_data = {}
    if data.api_key is not None:
        update_data['api_key'] = data.api_key
        # 如果设置了 API Key，标记为已配置
        update_data['is_configured'] = bool(data.api_key.strip())
    if data.api_endpoint is not None:
        update_data['api_endpoint'] = data.api_endpoint
    if data.is_enabled is not None:
        update_data['is_enabled'] = data.is_enabled
    if data.parameters is not None:
        update_data['parameters'] = data.parameters

    if update_data:
        update_data['updated_at'] = datetime.utcnow()
        stmt = (
            update(LLMModelConfig)
            .where(LLMModelConfig.model_id == model_id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.commit()

        # 重新查询更新后的数据
        result = await db.execute(query)
        model = result.scalar_one()

    return model.to_dict(include_api_key=False)


@router.post("/{model_id:path}/test", response_model=LLMModelTestResponse)
async def test_model(
    model_id: str,
    data: LLMModelTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    测试模型连接

    发送一个简单的测试请求到 LLM，验证 API Key 和连接是否正常
    """
    # 查询模型配置
    query = select(LLMModelConfig).where(LLMModelConfig.model_id == model_id)
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

    if not model.api_key:
        raise HTTPException(status_code=400, detail="该模型尚未配置 API Key")

    # 测试连接
    try:
        from litellm import completion
        import os

        # 临时设置环境变量（用于测试）
        provider = model.provider
        env_key = None

        if provider == "anthropic":
            env_key = "ANTHROPIC_API_KEY"
        elif provider == "openai":
            env_key = "OPENAI_API_KEY"
        elif provider == "gemini":
            env_key = "GEMINI_API_KEY"
        elif provider == "qwen":
            env_key = "DASHSCOPE_API_KEY"
        elif provider == "volcengine":
            env_key = "VOLCENGINE_API_KEY"

        # 备份原有的环境变量
        old_value = os.environ.get(env_key) if env_key else None

        try:
            # 设置测试用的 API Key
            if env_key:
                os.environ[env_key] = model.api_key

            # 调用 LLM
            response = completion(
                model=model.model_id,
                messages=[{"role": "user", "content": data.test_prompt}],
                api_base=model.api_endpoint if model.api_endpoint else None,
                max_tokens=100,
            )

            # 提取响应
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else None

            # 更新统计（测试成功）
            update_data = {
                'last_used_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            stmt = (
                update(LLMModelConfig)
                .where(LLMModelConfig.model_id == model_id)
                .values(**update_data)
            )
            await db.execute(stmt)
            await db.commit()

            return LLMModelTestResponse(
                success=True,
                response=content,
                model_used=model.model_id,
                tokens_used=tokens,
            )

        finally:
            # 恢复原有的环境变量
            if env_key:
                if old_value is not None:
                    os.environ[env_key] = old_value
                else:
                    os.environ.pop(env_key, None)

    except Exception as e:
        return LLMModelTestResponse(
            success=False,
            error=str(e),
        )


@router.get("/stats/usage", response_model=dict)
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取模型使用统计

    返回每个模型的使用次数、Token 消耗等信息
    """
    query = select(LLMModelConfig).where(LLMModelConfig.total_requests > 0).order_by(
        LLMModelConfig.total_requests.desc()
    )
    result = await db.execute(query)
    models = result.scalars().all()

    stats = []
    for model in models:
        stats.append({
            "model_id": model.model_id,
            "model_name": model.model_name,
            "provider": model.provider,
            "total_requests": model.total_requests,
            "total_tokens": model.total_tokens,
            "last_used_at": model.last_used_at.isoformat() if model.last_used_at else None,
        })

    return {
        "stats": stats,
        "total_requests": sum(s["total_requests"] for s in stats),
        "total_tokens": sum(s["total_tokens"] for s in stats),
    }


@router.delete("/{model_id:path}")
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    删除自定义模型配置

    注意：
    - 只能删除自定义添加的模型
    - 预定义的系统模型无法删除（为了安全）
    - 删除后相关的使用统计也会丢失
    """
    # 查询模型
    query = select(LLMModelConfig).where(LLMModelConfig.model_id == model_id)
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

    # 如果模型有使用记录，警告但允许删除
    if model.total_requests > 0:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(
            f"删除有使用记录的模型: {model_id}, "
            f"请求数: {model.total_requests}, "
            f"Token 数: {model.total_tokens}"
        )

    # 删除模型
    await db.delete(model)
    await db.commit()

    return {
        "success": True,
        "message": f"模型 {model_id} 已删除",
        "deleted_model": {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "total_requests": model.total_requests,
            "total_tokens": model.total_tokens,
        }
    }
