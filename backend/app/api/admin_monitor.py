# app/api/admin_monitor.py
# 管理员监控 API（只读）
#
# 提供 Workflow 和 Agent 执行记录的只读查询接口

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, Integer
from sqlalchemy.sql.expression import cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.core.logging import get_logger
from app.models.user import User
from app.models.execution import WorkflowExecution, AgentExecution

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/monitor", tags=["监控"])


# ==================== 响应模型 ====================

class MonitorSummary(BaseModel):
    """监控摘要"""
    total_workflows: int
    pending_workflows: int
    completed_workflows: int
    failed_workflows: int
    total_agent_calls: int
    today_agent_calls: int
    agent_success_rate: float


class WorkflowItem(BaseModel):
    """工作流列表项"""
    id: str
    workflow_id: str
    workflow_type: str
    status: str
    title: str
    started_at: datetime
    completed_at: Optional[datetime]


class AgentStats(BaseModel):
    """Agent 统计"""
    agent_name: str
    total_calls: int
    success_count: int
    fail_count: int
    avg_time_ms: float


# ==================== API 端点 ====================

@router.get("/summary", response_model=MonitorSummary)
async def get_monitor_summary(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取监控摘要

    返回 Workflow 和 Agent 的整体统计数据
    """
    # Workflow 统计
    total_workflows = await db.scalar(
        select(func.count(WorkflowExecution.id))
    ) or 0

    pending_workflows = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.status == "pending")
    ) or 0

    completed_workflows = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.status == "completed")
    ) or 0

    failed_workflows = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.status == "failed")
    ) or 0

    # Agent 统计
    total_agent_calls = await db.scalar(
        select(func.count(AgentExecution.id))
    ) or 0

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_agent_calls = await db.scalar(
        select(func.count(AgentExecution.id))
        .where(AgentExecution.created_at >= today_start)
    ) or 0

    success_count = await db.scalar(
        select(func.count(AgentExecution.id))
        .where(AgentExecution.success == True)
    ) or 0

    agent_success_rate = (success_count / total_agent_calls * 100) if total_agent_calls > 0 else 100.0

    return MonitorSummary(
        total_workflows=total_workflows,
        pending_workflows=pending_workflows,
        completed_workflows=completed_workflows,
        failed_workflows=failed_workflows,
        total_agent_calls=total_agent_calls,
        today_agent_calls=today_agent_calls,
        agent_success_rate=round(agent_success_rate, 1),
    )


@router.get("/workflows", response_model=list[WorkflowItem])
async def get_workflow_list(
    limit: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取工作流列表

    返回最近的工作流执行记录
    """
    query = select(WorkflowExecution).order_by(WorkflowExecution.started_at.desc())

    if status:
        query = query.where(WorkflowExecution.status == status)

    query = query.limit(limit)

    result = await db.execute(query)
    workflows = result.scalars().all()

    return [
        WorkflowItem(
            id=str(w.id),
            workflow_id=w.workflow_id,
            workflow_type=w.workflow_type,
            status=w.status,
            title=w.title,
            started_at=w.started_at,
            completed_at=w.completed_at,
        )
        for w in workflows
    ]


@router.get("/agents", response_model=list[AgentStats])
async def get_agent_stats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 Agent 调用统计

    返回每个 Agent 的调用次数和成功率
    """
    # 按 agent_name 分组统计
    query = select(
        AgentExecution.agent_name,
        func.count(AgentExecution.id).label("total_calls"),
        func.sum(func.cast(AgentExecution.success, Integer)).label("success_count"),
        func.avg(AgentExecution.execution_time_ms).label("avg_time_ms"),
    ).group_by(AgentExecution.agent_name)

    result = await db.execute(query)
    rows = result.all()

    # 如果没有执行记录，返回已注册的 Agent 列表
    if not rows:
        from app.agents.registry import agent_registry
        agents = agent_registry.list_agents()
        return [
            AgentStats(
                agent_name=a["name"],
                total_calls=0,
                success_count=0,
                fail_count=0,
                avg_time_ms=0,
            )
            for a in agents
        ]

    return [
        AgentStats(
            agent_name=row.agent_name,
            total_calls=row.total_calls,
            success_count=row.success_count or 0,
            fail_count=row.total_calls - (row.success_count or 0),
            avg_time_ms=round(row.avg_time_ms or 0, 1),
        )
        for row in rows
    ]


@router.get("/workflows/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取工作流详情
    """
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        return {"error": "工作流不存在"}

    return {
        "id": str(workflow.id),
        "workflow_id": workflow.workflow_id,
        "workflow_type": workflow.workflow_type,
        "status": workflow.status,
        "title": workflow.title,
        "input_data": workflow.input_data,
        "output_data": workflow.output_data,
        "error_message": workflow.error_message,
        "started_at": workflow.started_at.isoformat(),
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
    }
