# app/workflows/worker.py
# Temporal Worker 模块
#
# 功能说明：
# 1. 创建和配置 Temporal Worker
# 2. 注册所有 Workflow 和 Activity
# 3. 管理 Worker 生命周期
#
# 运行方式：
#   python -m app.workflows.worker
#
# Worker 职责：
# - 从 Temporal Server 的任务队列中拉取任务
# - 执行 Workflow 的步骤（确定性代码）
# - 执行 Activity 的实际操作（I/O、外部调用）
# - 向 Temporal Server 汇报执行结果
#
# 注意事项：
# - Worker 可以水平扩展，多个 Worker 可以监听同一个队列
# - Worker 崩溃后，Temporal 会自动将未完成的任务分配给其他 Worker
# - 生产环境建议运行多个 Worker 实例以提高可用性

import asyncio
from typing import List, Type

from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner

from app.core.config import settings
from app.core.logging import get_logger

# 导入所有 Workflow 定义
from app.workflows.definitions.approval import ApprovalWorkflow
from app.workflows.definitions.email_process import EmailProcessWorkflow

# 导入所有 Activity
from app.workflows.activities.base import (
    send_notification,
    log_workflow_event,
)
from app.workflows.activities.email import (
    run_quote_agent,
    run_intent_classifier,
    send_reply_email,
    update_event_status,
    generate_quote_pdf,
)

# 获取 logger
logger = get_logger(__name__)


# ==================== 注册列表 ====================
# 在这里添加所有需要注册的 Workflow 和 Activity

# Workflow 类列表
# 每个 Workflow 类都需要用 @workflow.defn 装饰
WORKFLOWS: List[Type] = [
    ApprovalWorkflow,
    EmailProcessWorkflow,
]

# Activity 函数列表
# 每个 Activity 函数都需要用 @activity.defn 装饰
ACTIVITIES = [
    # 基础 Activity
    send_notification,
    log_workflow_event,
    # 邮件处理 Activity
    run_quote_agent,
    run_intent_classifier,
    send_reply_email,
    update_event_status,
    generate_quote_pdf,
]


async def create_worker(client: Client) -> Worker:
    """
    创建 Temporal Worker

    这个函数创建一个 Worker 实例，注册所有 Workflow 和 Activity。
    Worker 创建后需要调用 run() 方法才会开始处理任务。

    Args:
        client: Temporal Client 实例，用于连接 Temporal Server

    Returns:
        Worker: 配置好的 Worker 实例

    Example:
        client = await Client.connect("localhost:7233")
        worker = await create_worker(client)
        await worker.run()  # 开始处理任务
    """
    logger.info(f"创建 Worker，任务队列: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info(f"注册 Workflow: {[w.__name__ for w in WORKFLOWS]}")
    logger.info(f"注册 Activity: {[a.__name__ for a in ACTIVITIES]}")

    # 禁用 sandbox，避免 Python 版本兼容性问题
    # 注意：这会禁用确定性检查，但对大多数场景足够安全
    # 生产环境如需要确定性保证，可以使用 SandboxedWorkflowRunner 并配置白名单
    worker = Worker(
        client=client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
        workflow_runner=UnsandboxedWorkflowRunner(),
    )

    return worker


async def run_worker():
    """
    运行 Temporal Worker

    这个函数是 Worker 的入口点，执行以下操作：
    1. 连接到 Temporal Server
    2. 创建 Worker
    3. 开始监听任务队列并处理任务

    Worker 会一直运行直到：
    - 手动停止（Ctrl+C）
    - 发生不可恢复的错误

    生产环境建议：
    - 使用 supervisord 或 systemd 管理 Worker 进程
    - 配置自动重启策略
    - 运行多个 Worker 实例
    """
    logger.info("="*60)
    logger.info("Temporal Worker 启动中...")
    logger.info(f"  Temporal Server: {settings.TEMPORAL_HOST}")
    logger.info(f"  Namespace: {settings.TEMPORAL_NAMESPACE}")
    logger.info(f"  Task Queue: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info("="*60)

    try:
        # 连接到 Temporal Server
        client = await Client.connect(
            settings.TEMPORAL_HOST,
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        logger.info("成功连接到 Temporal Server")

        # 创建 Worker
        worker = await create_worker(client)

        # 运行 Worker（阻塞直到停止）
        logger.info("Worker 开始监听任务...")
        await worker.run()

    except KeyboardInterrupt:
        logger.info("收到停止信号，Worker 正在关闭...")
    except Exception as e:
        logger.error(f"Worker 运行失败: {e}")
        raise


# ==================== 入口点 ====================
# 允许直接运行此模块：python -m app.workflows.worker

if __name__ == "__main__":
    # 配置日志
    from app.core.logging import setup_logging
    setup_logging()

    # 运行 Worker
    asyncio.run(run_worker())
