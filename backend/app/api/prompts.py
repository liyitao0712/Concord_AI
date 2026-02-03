# app/api/prompts.py
# Prompt 模板管理 API
#
# 功能说明：
# 1. Prompt 列表和详情
# 2. Prompt 更新（仅管理员）
# 3. Prompt 预览测试
#
# 路由：
#   GET    /admin/prompts              列表
#   GET    /admin/prompts/{name}       详情
#   PUT    /admin/prompts/{name}       更新
#   POST   /admin/prompts/{name}/test  测试预览
#   GET    /admin/prompts/{name}/default  获取默认值
#   POST   /admin/prompts/{name}/reset   重置为默认值

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.prompt import Prompt

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/prompts", tags=["Prompt 管理"])


# ==================== Schema ====================

class PromptResponse(BaseModel):
    """Prompt 响应"""
    id: str
    name: str
    category: str
    display_name: Optional[str]
    content: str
    variables: Optional[dict]
    description: Optional[str]
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    """Prompt 列表响应"""
    items: List[PromptResponse]
    total: int


class PromptUpdate(BaseModel):
    """更新 Prompt"""
    content: str = Field(..., min_length=1)
    display_name: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[dict] = None
    is_active: Optional[bool] = None


class PromptTestRequest(BaseModel):
    """测试 Prompt 请求"""
    variables: dict = Field(default_factory=dict)


class PromptTestResponse(BaseModel):
    """测试 Prompt 响应"""
    rendered: str
    variables_used: List[str]
    missing_variables: List[str]


# ==================== API ====================

@router.get("", response_model=PromptListResponse)
async def list_prompts(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取 Prompt 列表"""
    query = select(Prompt).order_by(Prompt.category, Prompt.name)

    if category:
        query = query.where(Prompt.category == category)
    if is_active is not None:
        query = query.where(Prompt.is_active == is_active)

    result = await session.execute(query)
    prompts = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(Prompt.id))
    if category:
        count_query = count_query.where(Prompt.category == category)
    if is_active is not None:
        count_query = count_query.where(Prompt.is_active == is_active)
    total = await session.scalar(count_query) or 0

    return PromptListResponse(
        items=[PromptResponse(
            id=str(p.id),
            name=p.name,
            category=p.category,
            display_name=p.display_name,
            content=p.content,
            variables=p.variables,
            description=p.description,
            is_active=p.is_active,
            version=p.version,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ) for p in prompts],
        total=total,
    )


@router.get("/{prompt_name}", response_model=PromptResponse)
async def get_prompt(
    prompt_name: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取 Prompt 详情"""
    result = await session.execute(
        select(Prompt).where(Prompt.name == prompt_name)
    )
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt 不存在")

    return PromptResponse(
        id=str(prompt.id),
        name=prompt.name,
        category=prompt.category,
        display_name=prompt.display_name,
        content=prompt.content,
        variables=prompt.variables,
        description=prompt.description,
        is_active=prompt.is_active,
        version=prompt.version,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.put("/{prompt_name}", response_model=PromptResponse)
async def update_prompt(
    prompt_name: str,
    data: PromptUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新 Prompt"""
    result = await session.execute(
        select(Prompt).where(Prompt.name == prompt_name)
    )
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt 不存在")

    # 更新字段
    prompt.content = data.content
    if data.display_name is not None:
        prompt.display_name = data.display_name
    if data.description is not None:
        prompt.description = data.description
    if data.variables is not None:
        prompt.variables = data.variables
    if data.is_active is not None:
        prompt.is_active = data.is_active

    prompt.version += 1
    prompt.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(prompt)

    # 清除 Prompt 缓存（通用）
    try:
        from app.llm.prompts import prompt_manager
        await prompt_manager.refresh_cache(prompt_name)
        logger.info(f"[PromptsAPI] 已清除 Prompt 缓存: {prompt_name}")
    except Exception as e:
        logger.warning(f"[PromptsAPI] 清除缓存失败: {e}")

    logger.info(f"[PromptsAPI] 更新 Prompt: {prompt_name} by {admin.email}")

    return PromptResponse(
        id=str(prompt.id),
        name=prompt.name,
        category=prompt.category,
        display_name=prompt.display_name,
        content=prompt.content,
        variables=prompt.variables,
        description=prompt.description,
        is_active=prompt.is_active,
        version=prompt.version,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.post("/{prompt_name}/test", response_model=PromptTestResponse)
async def test_prompt(
    prompt_name: str,
    data: PromptTestRequest,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    测试 Prompt 渲染

    传入变量，返回渲染后的结果
    """
    import re

    result = await session.execute(
        select(Prompt).where(Prompt.name == prompt_name)
    )
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt 不存在")

    # 提取模板中的变量（支持 {var} 和 {{var}} 格式）
    # 匹配 {var} 但不匹配 {{var}} 中的内容
    content = prompt.content

    # 找出所有变量
    # 先处理 {{var}} 格式（Jinja2 风格）
    jinja_vars = re.findall(r'\{\{(\w+)\}\}', content)
    # 再处理 {var} 格式（Python format 风格）
    python_vars = re.findall(r'\{(\w+)\}', content)
    # 去除 JSON 中的花括号误匹配
    python_vars = [v for v in python_vars if v not in ['', 'null', 'true', 'false']]

    all_vars = list(set(jinja_vars + python_vars))

    # 检查缺失的变量
    missing_vars = [v for v in all_vars if v not in data.variables]

    # 渲染（用占位符替代缺失变量）
    rendered = content
    for var in all_vars:
        value = data.variables.get(var, f"[{var}]")
        # 替换两种格式
        rendered = rendered.replace(f"{{{{{var}}}}}", str(value))
        rendered = rendered.replace(f"{{{var}}}", str(value))

    return PromptTestResponse(
        rendered=rendered,
        variables_used=list(data.variables.keys()),
        missing_variables=missing_vars,
    )


@router.get("/{prompt_name}/default")
async def get_prompt_default(
    prompt_name: str,
    _: User = Depends(get_current_admin_user),
):
    """
    获取 Prompt 的默认值（来自 defaults.py）

    可用于前端对比当前值和默认值
    """
    from app.llm.prompts.defaults import get_default_prompt

    default = get_default_prompt(prompt_name)
    if not default:
        raise HTTPException(status_code=404, detail=f"未找到默认 Prompt: {prompt_name}")

    return {
        "name": prompt_name,
        "content": default["content"],
        "variables": default.get("variables", {}),
        "display_name": default.get("display_name"),
        "description": default.get("description"),
    }


@router.post("/{prompt_name}/reset", response_model=PromptResponse)
async def reset_prompt_to_default(
    prompt_name: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    重置 Prompt 为默认值

    如果数据库中已存在，更新内容为默认值并保存历史版本。
    如果不存在，从默认值创建新记录。
    """
    from app.llm.prompts.defaults import get_default_prompt
    from app.models.prompt import PromptHistory

    default = get_default_prompt(prompt_name)
    if not default:
        raise HTTPException(status_code=404, detail=f"未找到默认 Prompt: {prompt_name}")

    result = await session.execute(
        select(Prompt).where(Prompt.name == prompt_name)
    )
    prompt = result.scalar_one_or_none()

    if prompt:
        # 保存历史版本
        history = PromptHistory(
            prompt_id=prompt.id,
            prompt_name=prompt.name,
            content=prompt.content,
            variables=prompt.variables,
            version=prompt.version,
            changed_by=admin.id,
            change_reason="Reset to default",
        )
        session.add(history)

        # 重置为默认值
        prompt.content = default["content"]
        prompt.variables = default.get("variables", {})
        prompt.display_name = default.get("display_name", prompt_name)
        prompt.description = default.get("description")
        prompt.version += 1
        prompt.updated_at = datetime.utcnow()
        prompt.updated_by = admin.id
    else:
        # 从默认值创建
        prompt = Prompt(
            name=prompt_name,
            display_name=default.get("display_name", prompt_name),
            category=default.get("category", "general"),
            content=default["content"],
            variables=default.get("variables", {}),
            description=default.get("description"),
            model_hint=default.get("model_hint"),
        )
        session.add(prompt)

    await session.commit()
    await session.refresh(prompt)

    # 清除缓存
    try:
        from app.llm.prompts import prompt_manager
        await prompt_manager.refresh_cache(prompt_name)
    except Exception as e:
        logger.warning(f"[PromptsAPI] 清除缓存失败: {e}")

    logger.info(f"[PromptsAPI] 重置 Prompt 为默认值: {prompt_name} by {admin.email}")

    return PromptResponse(
        id=str(prompt.id),
        name=prompt.name,
        category=prompt.category,
        display_name=prompt.display_name,
        content=prompt.content,
        variables=prompt.variables,
        description=prompt.description,
        is_active=prompt.is_active,
        version=prompt.version,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.post("/init-defaults")
async def init_default_prompts(
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    初始化默认 Prompt 到数据库

    将 defaults.py 中定义的所有 Prompt 同步到数据库。
    如果数据库中已存在，则跳过。

    Returns:
        dict: 初始化结果统计
    """
    from app.llm.prompts import prompt_manager

    try:
        # 执行初始化
        await prompt_manager.init_defaults(session)

        # 统计结果
        result = await session.execute(select(Prompt))
        total_count = len(result.scalars().all())

        logger.info(f"[PromptsAPI] 默认 Prompt 已初始化 by {admin.email}")

        return {
            "success": True,
            "detail": "默认 Prompt 已初始化",
            "total_prompts": total_count,
        }

    except Exception as e:
        logger.error(f"[PromptsAPI] 初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")
