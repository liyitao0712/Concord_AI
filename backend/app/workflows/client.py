# app/workflows/client.py
# Temporal Client 模块
#
# 功能说明：
# 1. 提供 Temporal Client 连接管理
# 2. 封装常用的 Workflow 操作（启动、查询、取消）
# 3. 提供便捷的辅助函数
#
# 使用方法：
#   from app.workflows.client import get_temporal_client, start_workflow
#
#   # 方式1：使用全局 Client
#   client = await get_temporal_client()
#   handle = await client.start_workflow(...)
#
#   # 方式2：使用辅助函数
#   handle = await start_workflow(ApprovalWorkflow.run, args=(...))
#
# Client 职责：
# - 与 Temporal Server 建立连接
# - 启动新的 Workflow 执行
# - 查询运行中 Workflow 的状态
# - 发送 Signal 给运行中的 Workflow
# - 取消或终止 Workflow

from typing import Any, Optional, TypeVar
from datetime import timedelta
import uuid

from temporalio.client import Client, WorkflowHandle

from app.core.config import settings
from app.core.logging import get_logger

# 获取 logger
logger = get_logger(__name__)

# 全局 Client 实例
# 使用单例模式避免创建多个连接
_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    获取 Temporal Client 实例（单例模式）

    这个函数返回一个共享的 Client 实例，避免每次调用都创建新连接。
    首次调用时会创建连接，后续调用返回已有连接。

    Returns:
        Client: Temporal Client 实例

    Raises:
        Exception: 连接 Temporal Server 失败时抛出

    Example:
        client = await get_temporal_client()
        handle = await client.start_workflow(
            MyWorkflow.run,
            args=["arg1"],
            id="my-workflow-id",
            task_queue="my-queue"
        )
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

    在应用关闭时调用，释放连接资源。
    """
    global _client

    if _client is not None:
        # Temporal Python SDK 的 Client 没有显式的 close 方法
        # 将引用置空让 GC 处理
        _client = None
        logger.info("Temporal Client 已关闭")


async def start_workflow(
    workflow: Any,
    args: tuple = (),
    id: Optional[str] = None,
    task_queue: Optional[str] = None,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
) -> WorkflowHandle:
    """
    启动一个新的 Workflow 执行

    这是启动 Workflow 的便捷方法，自动处理：
    - 获取 Client 连接
    - 生成唯一的 Workflow ID（如果未提供）
    - 使用默认的任务队列

    Args:
        workflow: Workflow 的 run 方法（如 ApprovalWorkflow.run）
        args: 传递给 Workflow 的参数元组
        id: Workflow ID（可选，默认生成 UUID）
        task_queue: 任务队列名称（可选，默认使用配置）
        execution_timeout: 整个 Workflow 执行的超时时间
        run_timeout: 单次运行的超时时间
        task_timeout: 单个任务的超时时间

    Returns:
        WorkflowHandle: Workflow 句柄，可用于查询状态、发送信号等

    Example:
        # 启动审批工作流
        handle = await start_workflow(
            ApprovalWorkflow.run,
            args=(approval_request,),
            id=f"approval-{request_id}",
        )

        # 等待结果
        result = await handle.result()

        # 或者获取 Workflow ID 以便后续查询
        workflow_id = handle.id
    """
    client = await get_temporal_client()

    # 生成 Workflow ID（如果未提供）
    workflow_id = id or f"wf-{uuid.uuid4()}"

    # 使用默认任务队列（如果未提供）
    queue = task_queue or settings.TEMPORAL_TASK_QUEUE

    logger.info(f"启动 Workflow: {workflow.__qualname__}")
    logger.info(f"  Workflow ID: {workflow_id}")
    logger.info(f"  Task Queue: {queue}")

    handle = await client.start_workflow(
        workflow,
        args=args if args else None,
        id=workflow_id,
        task_queue=queue,
        execution_timeout=execution_timeout,
        run_timeout=run_timeout,
        task_timeout=task_timeout,
    )

    logger.info(f"Workflow 已启动: {workflow_id}")
    return handle


async def get_workflow_handle(workflow_id: str) -> WorkflowHandle:
    """
    获取已存在的 Workflow 句柄

    用于查询或操作已经运行的 Workflow。

    Args:
        workflow_id: Workflow 的唯一标识符

    Returns:
        WorkflowHandle: Workflow 句柄

    Example:
        handle = await get_workflow_handle("approval-12345")
        status = await handle.query(ApprovalWorkflow.get_status)
    """
    client = await get_temporal_client()
    return client.get_workflow_handle(workflow_id)


async def signal_workflow(
    workflow_id: str,
    signal_name: str,
    args: tuple = (),
) -> None:
    """
    向运行中的 Workflow 发送信号

    Signal 是外部与运行中 Workflow 通信的方式，常用于：
    - 用户审批通过/拒绝
    - 外部事件通知
    - 动态更新 Workflow 状态

    Args:
        workflow_id: Workflow 的唯一标识符
        signal_name: 信号名称（对应 Workflow 中的 @workflow.signal 方法）
        args: 传递给信号处理方法的参数

    Example:
        # 发送审批通过信号
        await signal_workflow(
            workflow_id="approval-12345",
            signal_name="approve",
            args=(approver_id, "同意"),
        )
    """
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    logger.info(f"发送信号到 Workflow: {workflow_id}")
    logger.info(f"  信号名称: {signal_name}")

    await handle.signal(signal_name, *args)
    logger.info("信号发送成功")


async def cancel_workflow(workflow_id: str) -> None:
    """
    取消运行中的 Workflow

    取消是优雅的停止方式，Workflow 会收到 CancelledError，
    可以在 try/except 中处理清理逻辑。

    Args:
        workflow_id: Workflow 的唯一标识符

    Example:
        await cancel_workflow("approval-12345")
    """
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    logger.warning(f"取消 Workflow: {workflow_id}")
    await handle.cancel()
    logger.info("Workflow 已取消")
