# app/temporal/client.py
# Temporal Client 封装
#
# 提供与 Temporal Server 交互的便捷方法：
# - 获取 Client 连接
# - 启动工作流
# - 发送 Signal
# - 查询工作流状态

import logging
from typing import Optional

from temporalio.client import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局 Client 实例（惰性初始化）
_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    获取 Temporal Client 实例（单例模式）

    Returns:
        Client: Temporal Client 实例
    """
    global _client
    if _client is None:
        logger.info(f"连接 Temporal Server: {settings.TEMPORAL_HOST}")
        _client = await Client.connect(
            settings.TEMPORAL_HOST,
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        logger.info("Temporal Client 连接成功")
    return _client


async def close_temporal_client():
    """
    关闭 Temporal Client 连接
    """
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("Temporal Client 已关闭")


async def start_suggestion_workflow(suggestion_id: str) -> str:
    """
    启动工作类型建议审批工作流

    Args:
        suggestion_id: WorkTypeSuggestion 的 ID

    Returns:
        str: Workflow ID
    """
    # 延迟导入避免循环依赖
    from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow

    client = await get_temporal_client()
    workflow_id = f"work-type-suggestion-{suggestion_id}"

    logger.info(f"启动审批工作流: {workflow_id}")

    handle = await client.start_workflow(
        WorkTypeSuggestionWorkflow.run,
        suggestion_id,
        id=workflow_id,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )

    logger.info(f"工作流已启动: {workflow_id}")
    return workflow_id


async def approve_suggestion(workflow_id: str, reviewer_id: str, note: str = ""):
    """
    发送批准信号到工作流

    Args:
        workflow_id: 工作流 ID
        reviewer_id: 审批人 ID
        note: 审批备注
    """
    from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow

    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    logger.info(f"发送批准信号: workflow_id={workflow_id}, reviewer={reviewer_id}")
    await handle.signal(WorkTypeSuggestionWorkflow.approve, reviewer_id, note)


async def reject_suggestion(workflow_id: str, reviewer_id: str, note: str = ""):
    """
    发送拒绝信号到工作流

    Args:
        workflow_id: 工作流 ID
        reviewer_id: 审批人 ID
        note: 拒绝原因
    """
    from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow

    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    logger.info(f"发送拒绝信号: workflow_id={workflow_id}, reviewer={reviewer_id}")
    await handle.signal(WorkTypeSuggestionWorkflow.reject, reviewer_id, note)


async def get_workflow_status(workflow_id: str) -> Optional[dict]:
    """
    查询工作流状态

    Args:
        workflow_id: 工作流 ID

    Returns:
        dict: 工作流状态信息，如果工作流不存在返回 None
    """
    from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow

    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)

        # 查询工作流状态
        status = await handle.query(WorkTypeSuggestionWorkflow.get_status)
        return status
    except Exception as e:
        logger.warning(f"查询工作流状态失败: {workflow_id}, error={e}")
        return None
