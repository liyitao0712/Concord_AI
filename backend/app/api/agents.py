# app/api/agents.py
# Agent API 端点
#
# 提供 HTTP API 来调用 Agent：
# 1. 列出可用 Agent
# 2. 执行指定 Agent
# 3. 查询 Agent 能力

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_user, get_current_admin_user
from app.core.config import settings as app_settings
from app.core.database import get_db
from app.models.user import User
from app.models.execution import AgentExecution
from app.agents.registry import agent_registry
from app.llm import apply_llm_settings

logger = get_logger(__name__)

# 创建路由
router = APIRouter(
    prefix="/api/agents",
    tags=["Agents"],
)


# ==================== 请求/响应模型 ====================

class AgentRunRequest(BaseModel):
    """Agent 执行请求"""
    input: str = Field(..., description="输入文本")
    data: Optional[dict] = Field(None, description="额外的输入数据")

    class Config:
        json_schema_extra = {
            "example": {
                "input": "我想询问一下产品A的价格，需要采购100个",
                "data": {
                    "subject": "询价请求",
                    "sender": "customer@example.com",
                },
            }
        }


class AgentRunResponse(BaseModel):
    """Agent 执行响应"""
    success: bool = Field(..., description="是否成功")
    output: str = Field("", description="文本输出")
    data: dict = Field(default_factory=dict, description="结构化输出")
    iterations: int = Field(0, description="迭代次数")
    tool_calls: list = Field(default_factory=list, description="工具调用记录")
    error: Optional[str] = Field(None, description="错误信息")


class AgentInfo(BaseModel):
    """Agent 信息"""
    name: str = Field(..., description="Agent 名称")
    description: str = Field("", description="Agent 描述")
    tools: list[str] = Field(default_factory=list, description="可用工具")
    model: Optional[str] = Field(None, description="使用的模型")


class AgentConfigResponse(BaseModel):
    """Agent 配置响应"""
    agent_name: str = Field(..., description="Agent 名称")
    model: Optional[str] = Field(None, description="模型 ID")
    temperature: Optional[float] = Field(None, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大 Token 数")
    enabled: bool = Field(True, description="是否启用")


class AgentConfigUpdateRequest(BaseModel):
    """Agent 配置更新请求"""
    model: Optional[str] = Field(None, description="模型 ID")
    temperature: Optional[float] = Field(None, description="温度参数", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, description="最大 Token 数", gt=0)
    enabled: Optional[bool] = Field(None, description="是否启用")


class AgentListItem(BaseModel):
    """Agent 列表项"""
    name: str = Field(..., description="Agent 名称")
    description: str = Field("", description="Agent 描述")
    prompt_name: str = Field("", description="Prompt 名称")
    model: Optional[str] = Field(None, description="使用的模型")
    tools: list[str] = Field(default_factory=list, description="可用工具")


# ==================== API 端点 ====================

@router.get(
    "",
    response_model=list[AgentInfo],
    summary="列出所有 Agent",
    description="获取所有已注册的 Agent 列表",
)
async def list_agents(
    current_user: User = Depends(get_current_user),
) -> list[AgentInfo]:
    """列出所有可用的 Agent"""
    agents = agent_registry.list_agents()
    return [AgentInfo(**agent) for agent in agents]


@router.get(
    "/{agent_name}",
    response_model=AgentInfo,
    summary="获取 Agent 信息",
    description="获取指定 Agent 的详细信息",
)
async def get_agent(
    agent_name: str,
    current_user: User = Depends(get_current_user),
) -> AgentInfo:
    """获取 Agent 详情"""
    agent = agent_registry.get(agent_name)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent 不存在: {agent_name}",
        )

    return AgentInfo(
        name=agent.name,
        description=agent.description,
        tools=agent.tools,
        model=agent.model,
    )


@router.post(
    "/{agent_name}/run",
    response_model=AgentRunResponse,
    summary="执行 Agent",
    description="执行指定的 Agent，返回处理结果",
)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """
    执行 Agent

    调用指定的 Agent 处理输入，返回结构化结果。

    Args:
        agent_name: Agent 名称
        request: 执行请求

    Returns:
        AgentRunResponse: 执行结果
    """
    logger.info(f"执行 Agent: {agent_name}")
    logger.info(f"  用户: {current_user.name}")
    logger.info(f"  输入: {request.input[:50]}...")

    # 检查 Agent 是否存在
    agent = agent_registry.get(agent_name)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent 不存在: {agent_name}",
        )

    start_time = time.time()

    try:
        # 从数据库加载并应用 LLM 设置
        await apply_llm_settings(db)

        # 加载 Agent 配置（如果有的话）
        await agent.load_config_from_db(db)

        # 执行 Agent
        result = await agent_registry.run(
            agent_name,
            request.input,
            input_data=request.data,
        )

        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Agent 执行完成: success={result.success}, time={execution_time_ms}ms")

        # 获取实际使用的模型
        model_used = agent._get_model()

        # 保存执行记录
        execution = AgentExecution(
            agent_name=agent_name,
            success=result.success,
            execution_time_ms=execution_time_ms,
            model_used=model_used,
            iterations=result.iterations,
            error_message=result.error,
        )
        db.add(execution)
        await db.commit()

        return AgentRunResponse(
            success=result.success,
            output=result.output,
            data=result.data,
            iterations=result.iterations,
            tool_calls=result.tool_calls,
            error=result.error,
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Agent 执行失败: {e}")

        # 保存失败记录
        try:
            # 尝试获取实际使用的模型，失败则使用默认值
            try:
                model_used = agent._get_model()
            except:
                model_used = app_settings.DEFAULT_LLM_MODEL

            execution = AgentExecution(
                agent_name=agent_name,
                success=False,
                execution_time_ms=execution_time_ms,
                model_used=model_used,
                iterations=0,
                error_message=str(e),
            )
            db.add(execution)
            await db.commit()
        except Exception:
            pass  # 忽略保存失败

        raise HTTPException(
            status_code=500,
            detail=f"Agent 执行失败: {str(e)}",
        )


@router.post(
    "/analyze/email",
    response_model=AgentRunResponse,
    summary="分析邮件",
    description="使用邮件分析 Agent 分析邮件内容",
)
async def analyze_email(
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """
    分析邮件

    便捷端点，直接调用邮件分析 Agent
    """
    return await run_agent(
        agent_name="email_analyzer",
        request=request,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/classify/intent",
    response_model=AgentRunResponse,
    summary="意图分类",
    description="使用意图分类 Agent 快速分类用户意图",
)
async def classify_intent(
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """
    意图分类

    便捷端点，快速分类用户意图
    """
    return await run_agent(
        agent_name="intent_classifier",
        request=request,
        current_user=current_user,
        db=db,
    )


# ==================== Agent 配置管理（管理员） ====================


@router.get(
    "/admin/list",
    response_model=list[AgentListItem],
    summary="获取所有 Agent 列表（管理员）",
    description="获取所有 Agent 及其配置信息",
)
async def list_all_agents(
    _: User = Depends(get_current_admin_user),
) -> list[AgentListItem]:
    """
    获取所有 Agent 列表

    返回所有已注册的 Agent 及其基本配置
    """
    agents = agent_registry.list_agents()
    result = []

    for agent_dict in agents:
        agent = agent_registry.get(agent_dict["name"])
        result.append(AgentListItem(
            name=agent.name,
            description=agent.description,
            prompt_name=getattr(agent, "prompt_name", ""),
            model=agent.model,
            tools=agent.tools,
        ))

    return result


@router.get(
    "/admin/{agent_name}/config",
    response_model=AgentConfigResponse,
    summary="获取 Agent 配置（管理员）",
    description="获取指定 Agent 的配置信息",
)
async def get_agent_config(
    agent_name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> AgentConfigResponse:
    """
    获取 Agent 配置

    从数据库读取 Agent 的配置，包括模型、温度等参数
    """
    from app.llm.settings_loader import load_agent_config

    # 检查 Agent 是否存在
    agent = agent_registry.get(agent_name)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent 不存在: {agent_name}",
        )

    # 加载配置
    config = await load_agent_config(db, agent_name)

    return AgentConfigResponse(
        agent_name=agent_name,
        model=config.get("model"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        enabled=config.get("enabled", True),
    )


@router.put(
    "/admin/{agent_name}/config",
    response_model=AgentConfigResponse,
    summary="更新 Agent 配置（管理员）",
    description="更新指定 Agent 的配置信息",
)
async def update_agent_config(
    agent_name: str,
    request: AgentConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> AgentConfigResponse:
    """
    更新 Agent 配置

    保存 Agent 的配置到数据库，包括模型、温度等参数
    """
    from app.models.settings import SystemSetting
    from sqlalchemy import select, update

    # 检查 Agent 是否存在
    agent = agent_registry.get(agent_name)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent 不存在: {agent_name}",
        )

    # 更新配置到数据库
    updates = {}
    if request.model is not None:
        updates["model"] = request.model
    if request.temperature is not None:
        updates["temperature"] = str(request.temperature)
    if request.max_tokens is not None:
        updates["max_tokens"] = str(request.max_tokens)
    if request.enabled is not None:
        updates["enabled"] = "true" if request.enabled else "false"

    for key, value in updates.items():
        setting_key = f"agent.{agent_name}.{key}"

        # 查询是否已存在
        query = select(SystemSetting).where(SystemSetting.key == setting_key)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新
            existing.value = value
        else:
            # 创建新记录
            new_setting = SystemSetting(
                key=setting_key,
                value=value,
                category="agent",
                description=f"{agent_name} 的 {key} 配置",
            )
            db.add(new_setting)

    await db.commit()

    logger.info(f"[Agent Config] 更新 {agent_name} 配置: {updates}")

    # 返回更新后的配置
    from app.llm.settings_loader import load_agent_config
    config = await load_agent_config(db, agent_name)

    return AgentConfigResponse(
        agent_name=agent_name,
        model=config.get("model"),
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        enabled=config.get("enabled", True),
    )
