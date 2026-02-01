# app/api/workflows.py
# Workflow API 端点
#
# 功能说明：
# 提供 HTTP API 来管理和操作 Temporal Workflow：
# 1. 启动新的 Workflow
# 2. 查询 Workflow 状态
# 3. 发送 Signal（如审批通过/拒绝）
# 4. 取消 Workflow
#
# API 列表：
# - POST /api/workflows/approval       - 创建审批工作流
# - GET  /api/workflows/{id}/status    - 查询工作流状态
# - POST /api/workflows/{id}/approve   - 审批通过
# - POST /api/workflows/{id}/reject    - 审批拒绝
# - POST /api/workflows/{id}/cancel    - 取消工作流

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.execution import WorkflowExecution
from app.workflows.client import (
    start_workflow,
    get_workflow_handle,
    signal_workflow,
    cancel_workflow,
)
from app.workflows.definitions.approval import ApprovalWorkflow
from app.workflows.types import (
    ApprovalRequest,
    ApprovalResult,
    ApprovalStatus,
)

# 获取 logger
logger = get_logger(__name__)

# 创建路由
router = APIRouter(
    prefix="/api/workflows",
    tags=["Workflows"],
)


# ==================== 请求/响应模型 ====================

class CreateApprovalRequest(BaseModel):
    """创建审批请求的 API 模型"""
    request_id: str = Field(..., description="业务请求ID（如订单ID）")
    request_type: str = Field(..., description="请求类型（如 order_approval）")
    approver_id: str = Field(..., description="审批人用户ID")
    approver_email: str = Field(..., description="审批人邮箱")
    title: str = Field(..., description="审批标题")
    description: str = Field(..., description="审批描述")
    amount: Optional[float] = Field(None, description="涉及金额")
    timeout_hours: int = Field(24, description="超时时间（小时）", ge=1, le=168)
    metadata: Optional[dict] = Field(None, description="附加元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "order-12345",
                "request_type": "order_approval",
                "approver_id": "user-001",
                "approver_email": "approver@example.com",
                "title": "订单金额超限审批",
                "description": "订单金额 ¥50,000 超过 ¥10,000 限额，需要审批",
                "amount": 50000.00,
                "timeout_hours": 24,
            }
        }


class ApprovalResponse(BaseModel):
    """审批操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    workflow_id: Optional[str] = Field(None, description="工作流ID")


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应模型"""
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="当前状态")
    request_id: Optional[str] = Field(None, description="业务请求ID")
    approver_id: Optional[str] = Field(None, description="审批人ID")
    comment: Optional[str] = Field(None, description="审批意见")


class ApproveRejectRequest(BaseModel):
    """审批通过/拒绝请求模型"""
    comment: str = Field("", description="审批意见或拒绝原因")


# ==================== API 端点 ====================

@router.post(
    "/approval",
    response_model=ApprovalResponse,
    summary="创建审批工作流",
    description="创建一个新的审批工作流，并发送通知给审批人",
)
async def create_approval_workflow(
    request: CreateApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    创建审批工作流

    启动一个新的审批工作流：
    1. 创建 Workflow 实例
    2. 发送通知给审批人
    3. 等待审批响应或超时

    Args:
        request: 审批请求数据
        current_user: 当前登录用户（作为申请人）

    Returns:
        ApprovalResponse: 包含工作流ID的响应

    Raises:
        HTTPException: 创建失败时抛出 500 错误
    """
    logger.info(f"创建审批工作流: {request.request_id}")
    logger.info(f"  申请人: {current_user.name} ({current_user.id})")
    logger.info(f"  审批人: {request.approver_email}")

    try:
        # 构建 Workflow 输入
        approval_request = ApprovalRequest(
            request_id=request.request_id,
            request_type=request.request_type,
            requester_id=str(current_user.id),
            requester_name=current_user.name,
            approver_id=request.approver_id,
            approver_email=request.approver_email,
            title=request.title,
            description=request.description,
            amount=request.amount,
            timeout_hours=request.timeout_hours,
            metadata=request.metadata,
        )

        # 启动 Workflow
        # Workflow ID 使用 "approval-{request_id}" 格式，便于后续查询
        workflow_id = f"approval-{request.request_id}"
        handle = await start_workflow(
            ApprovalWorkflow.run,
            args=(approval_request,),
            id=workflow_id,
        )

        # 保存执行记录
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type="approval",
            status="pending",
            title=request.title,
            input_data={
                "request_id": request.request_id,
                "approver_email": request.approver_email,
                "amount": request.amount,
            },
        )
        db.add(execution)
        await db.commit()

        logger.info(f"审批工作流已创建: {workflow_id}")

        return ApprovalResponse(
            success=True,
            message="审批工作流已创建",
            workflow_id=workflow_id,
        )

    except Exception as e:
        logger.error(f"创建审批工作流失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"创建审批工作流失败: {str(e)}",
        )


@router.get(
    "/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="查询工作流状态",
    description="查询指定工作流的当前状态",
)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> WorkflowStatusResponse:
    """
    查询工作流状态

    通过 Query 机制查询运行中 Workflow 的当前状态。

    Args:
        workflow_id: 工作流ID
        current_user: 当前登录用户

    Returns:
        WorkflowStatusResponse: 工作流状态

    Raises:
        HTTPException: 工作流不存在或查询失败时抛出错误
    """
    logger.info(f"查询工作流状态: {workflow_id}")

    try:
        handle = await get_workflow_handle(workflow_id)

        # 使用 Query 获取详细状态
        details = await handle.query(ApprovalWorkflow.get_details)

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=details.get("status", "unknown"),
            request_id=details.get("request_id"),
            approver_id=details.get("approver_id"),
            comment=details.get("comment"),
        )

    except Exception as e:
        logger.error(f"查询工作流状态失败: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"工作流不存在或查询失败: {str(e)}",
        )


@router.post(
    "/{workflow_id}/approve",
    response_model=ApprovalResponse,
    summary="审批通过",
    description="发送审批通过信号给工作流",
)
async def approve_workflow(
    workflow_id: str,
    request: ApproveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    审批通过

    发送审批通过 Signal 给运行中的 Workflow。

    Args:
        workflow_id: 工作流ID
        request: 审批意见
        current_user: 当前登录用户（作为审批人）

    Returns:
        ApprovalResponse: 操作结果

    Raises:
        HTTPException: 发送信号失败时抛出错误
    """
    logger.info(f"审批通过: {workflow_id}")
    logger.info(f"  审批人: {current_user.name} ({current_user.id})")
    logger.info(f"  意见: {request.comment}")

    try:
        handle = await get_workflow_handle(workflow_id)

        # 发送审批通过信号
        # Temporal signal 需要将多个参数作为单个 args 元组传递
        await handle.signal(
            ApprovalWorkflow.approve,
            args=[str(current_user.id), request.comment],
        )

        # 更新执行记录状态
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = "completed"
            execution.completed_at = datetime.now()
            execution.output_data = {"result": "approved", "comment": request.comment}
            await db.commit()

        logger.info(f"审批通过信号已发送: {workflow_id}")

        return ApprovalResponse(
            success=True,
            message="审批通过",
            workflow_id=workflow_id,
        )

    except Exception as e:
        logger.error(f"发送审批通过信号失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"审批失败: {str(e)}",
        )


@router.post(
    "/{workflow_id}/reject",
    response_model=ApprovalResponse,
    summary="审批拒绝",
    description="发送审批拒绝信号给工作流",
)
async def reject_workflow(
    workflow_id: str,
    request: ApproveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    审批拒绝

    发送审批拒绝 Signal 给运行中的 Workflow。

    Args:
        workflow_id: 工作流ID
        request: 拒绝原因
        current_user: 当前登录用户（作为审批人）

    Returns:
        ApprovalResponse: 操作结果

    Raises:
        HTTPException: 发送信号失败时抛出错误
    """
    logger.info(f"审批拒绝: {workflow_id}")
    logger.info(f"  审批人: {current_user.name} ({current_user.id})")
    logger.info(f"  原因: {request.comment}")

    try:
        handle = await get_workflow_handle(workflow_id)

        # 发送审批拒绝信号
        # Temporal signal 需要将多个参数作为单个 args 元组传递
        await handle.signal(
            ApprovalWorkflow.reject,
            args=[str(current_user.id), request.comment],
        )

        # 更新执行记录状态
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = "completed"
            execution.completed_at = datetime.now()
            execution.output_data = {"result": "rejected", "comment": request.comment}
            await db.commit()

        logger.info(f"审批拒绝信号已发送: {workflow_id}")

        return ApprovalResponse(
            success=True,
            message="审批已拒绝",
            workflow_id=workflow_id,
        )

    except Exception as e:
        logger.error(f"发送审批拒绝信号失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"拒绝失败: {str(e)}",
        )


@router.post(
    "/{workflow_id}/cancel",
    response_model=ApprovalResponse,
    summary="取消工作流",
    description="取消运行中的工作流",
)
async def cancel_workflow_api(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> ApprovalResponse:
    """
    取消工作流

    取消运行中的 Workflow。只有申请人或管理员可以取消。

    Args:
        workflow_id: 工作流ID
        current_user: 当前登录用户

    Returns:
        ApprovalResponse: 操作结果

    Raises:
        HTTPException: 取消失败时抛出错误
    """
    logger.info(f"取消工作流: {workflow_id}")
    logger.info(f"  操作人: {current_user.name} ({current_user.id})")

    try:
        await cancel_workflow(workflow_id)

        logger.info(f"工作流已取消: {workflow_id}")

        return ApprovalResponse(
            success=True,
            message="工作流已取消",
            workflow_id=workflow_id,
        )

    except Exception as e:
        logger.error(f"取消工作流失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取消失败: {str(e)}",
        )
