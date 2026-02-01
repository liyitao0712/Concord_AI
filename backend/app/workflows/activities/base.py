# app/workflows/activities/base.py
# 基础 Activity 定义
#
# 功能说明：
# 1. 定义通用的 Activity 函数
# 2. 提供 Activity 的工具函数和基类
#
# Activity 特点：
# - 使用 @activity.defn 装饰器定义
# - 可以包含 I/O 操作（数据库、网络、文件等）
# - 支持超时、重试配置
# - 可以通过 activity.info() 获取执行上下文
#
# 超时配置说明：
# - schedule_to_close: 从任务被调度到完成的总时间
# - start_to_close: 从 Worker 开始执行到完成的时间
# - schedule_to_start: 从调度到 Worker 开始执行的时间
# - heartbeat: 心跳超时，用于长时间运行的 Activity

from datetime import datetime
from typing import Any

from temporalio import activity

from app.core.logging import get_logger
from app.workflows.types import (
    NotificationRequest,
    NotificationType,
    WorkflowEvent,
)

# 获取 logger
logger = get_logger(__name__)


# ==================== Activity 定义 ====================

@activity.defn(name="send_notification")
async def send_notification(request: NotificationRequest) -> bool:
    """
    发送通知 Activity

    这是一个通用的通知发送 Activity，支持多种通知类型。
    实际的发送逻辑根据通知类型分发到不同的处理器。

    Args:
        request: 通知请求对象

    Returns:
        bool: 发送是否成功

    Raises:
        ValueError: 不支持的通知类型
        Exception: 发送失败

    配置建议：
        在 Workflow 中调用时，建议设置：
        - start_to_close_timeout: 30 秒（发送不应该太久）
        - retry_policy: 最多重试 3 次
    """
    # 获取 Activity 执行信息
    info = activity.info()
    logger.info(f"[Activity] 发送通知")
    logger.info(f"  Activity ID: {info.activity_id}")
    logger.info(f"  Workflow ID: {info.workflow_id}")
    logger.info(f"  接收者: {request.recipient}")

    # 规范化通知类型（Temporal 序列化可能将枚举转为字符串）
    notification_type = request.type
    if isinstance(notification_type, str):
        notification_type = notification_type.lower()
    elif isinstance(notification_type, NotificationType):
        notification_type = notification_type.value
    elif isinstance(notification_type, (list, tuple)):
        # 处理序列化异常情况（字符串被拆成字符列表）
        notification_type = "".join(notification_type).lower()

    logger.info(f"  通知类型: {notification_type}")

    try:
        # 根据通知类型分发处理
        if notification_type == "email":
            # TODO: 实现邮件发送
            # await send_email_impl(request)
            logger.info(f"  邮件发送: {request.title} -> {request.recipient}")
            return True

        elif notification_type == "sms":
            # TODO: 实现短信发送
            # await send_sms_impl(request)
            logger.info(f"  短信发送: {request.title} -> {request.recipient}")
            return True

        elif notification_type == "webhook":
            # TODO: 实现 Webhook 回调
            # await call_webhook_impl(request)
            logger.info(f"  Webhook 调用: {request.recipient}")
            return True

        elif notification_type == "in_app":
            # TODO: 实现应用内通知
            # await create_in_app_notification(request)
            logger.info(f"  应用内通知: {request.title} -> {request.recipient}")
            return True

        else:
            raise ValueError(f"不支持的通知类型: {notification_type}")

    except Exception as e:
        logger.error(f"通知发送失败: {e}")
        raise


@activity.defn(name="log_workflow_event")
async def log_workflow_event(event: WorkflowEvent) -> None:
    """
    记录工作流事件 Activity

    将工作流执行过程中的事件记录到日志/数据库。
    这对于审计、调试、监控都很重要。

    Args:
        event: 工作流事件对象

    配置建议：
        在 Workflow 中调用时，建议设置：
        - start_to_close_timeout: 10 秒
        - retry_policy: 最多重试 5 次（日志记录应该可靠）
    """
    # 设置时间戳（如果未提供）
    if event.timestamp is None:
        event.timestamp = datetime.now()

    logger.info(f"[Workflow Event] {event.workflow_type}")
    logger.info(f"  Workflow ID: {event.workflow_id}")
    logger.info(f"  Event Type: {event.event_type}")
    logger.info(f"  Timestamp: {event.timestamp.isoformat()}")
    if event.event_data:
        logger.info(f"  Event Data: {event.event_data}")

    # TODO: 将事件保存到数据库
    # await save_workflow_event_to_db(event)


# ==================== 工具函数 ====================

def get_activity_context() -> dict:
    """
    获取当前 Activity 的执行上下文

    只能在 Activity 函数内部调用。

    Returns:
        dict: 包含 Activity 执行信息的字典
    """
    info = activity.info()
    return {
        "activity_id": info.activity_id,
        "activity_type": info.activity_type,
        "workflow_id": info.workflow_id,
        "workflow_type": info.workflow_type,
        "workflow_run_id": info.workflow_run_id,
        "attempt": info.attempt,
        "task_queue": info.task_queue,
    }


async def heartbeat(details: Any = None) -> None:
    """
    发送 Activity 心跳

    对于长时间运行的 Activity，定期发送心跳告诉 Temporal
    Activity 还在正常运行。如果心跳超时，Temporal 会认为
    Activity 已经失败，可能会重新调度。

    Args:
        details: 可选的心跳详情，用于进度报告

    Example:
        @activity.defn
        async def process_large_file(file_path: str):
            for i, chunk in enumerate(read_file_chunks(file_path)):
                await process_chunk(chunk)
                # 每处理一个 chunk 发送心跳
                await heartbeat(details={"progress": i})
    """
    activity.heartbeat(details)
