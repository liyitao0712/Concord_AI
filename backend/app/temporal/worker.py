# app/temporal/worker.py
# Temporal Worker 启动器
#
# 用法：
#   python -m app.temporal.worker
#
# Worker 负责执行工作流和活动，需要持续运行

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings

# 导入工作流和活动
from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow
from app.temporal.activities.work_type import (
    notify_admin_activity,
    approve_suggestion_activity,
    reject_suggestion_activity,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_worker():
    """
    启动 Temporal Worker
    """
    logger.info("="*50)
    logger.info("启动 Temporal Worker")
    logger.info(f"  Temporal Host: {settings.TEMPORAL_HOST}")
    logger.info(f"  Namespace: {settings.TEMPORAL_NAMESPACE}")
    logger.info(f"  Task Queue: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info("="*50)

    # 连接 Temporal Server
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )
    logger.info("已连接到 Temporal Server")

    # 创建 Worker
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[
            WorkTypeSuggestionWorkflow,
        ],
        activities=[
            notify_admin_activity,
            approve_suggestion_activity,
            reject_suggestion_activity,
        ],
        # 使用线程池执行活动（活动中有同步数据库操作）
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )

    logger.info("Temporal Worker 已启动，等待任务...")

    # 处理优雅关闭
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，准备关闭...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行 Worker
    async with worker:
        await shutdown_event.wait()

    logger.info("Temporal Worker 已关闭")


def main():
    """
    主入口
    """
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("收到 KeyboardInterrupt，正在退出...")
    except Exception as e:
        logger.error(f"Worker 异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
