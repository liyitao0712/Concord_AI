# app/workers/feishu_worker.py
# 飞书 WebSocket Worker
#
# 功能说明：
# 1. 使用 lark-oapi SDK 建立 WebSocket 长连接
# 2. 接收飞书消息 → 调用 Agent → 回复飞书
# 3. 支持多实例运行（每个飞书应用一个进程）
#
# 启动方式：
#   python -m app.workers.feishu_worker --app-id cli_xxx --app-secret xxx
#
# 优点（相比 HTTP 回调）：
# - 无需公网 IP
# - 实时性好
# - 连接稳定

import os
import sys
import argparse
import asyncio
import concurrent.futures
from typing import Optional

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
from lark_oapi.ws import Client as WSClient

from app.core.logging import get_logger, setup_logging
from app.core.config import settings
from app.core.redis import redis_client
from app.core.database import async_session_maker
from app.adapters.feishu import feishu_adapter, FeishuClient
from app.agents.chat_agent import ChatAgent
from app.schemas.event import UnifiedEvent
from app.workers.base import BaseWorker, WorkerStatus

logger = get_logger(__name__)


class FeishuMessageHandler:
    """
    飞书消息处理器

    接收飞书消息并调用 Agent 处理
    """

    def __init__(self, agent_id: str = "chat_agent"):
        self.agent_id = agent_id
        self.chat_agent = ChatAgent()
        self.client: Optional[FeishuClient] = None
        # 消息去重：记录已处理的 message_id，防止重复处理
        self._processed_messages: dict[str, float] = {}
        self._dedup_ttl = 60  # 去重记录保留 60 秒

    def set_client(self, client: FeishuClient) -> None:
        """设置飞书客户端"""
        self.client = client
        feishu_adapter.client = client

    async def load_agent_config(self) -> None:
        """从数据库加载 Agent 配置"""
        try:
            async with async_session_maker() as db:
                await self.chat_agent.load_config_from_db(db)
            logger.info(f"[FeishuMessageHandler] 已从数据库加载 {self.agent_id} 配置")
        except Exception as e:
            logger.warning(f"[FeishuMessageHandler] 加载 Agent 配置失败: {e}，使用默认配置")

    def is_duplicate(self, message_id: str) -> bool:
        """
        检查消息是否重复

        Args:
            message_id: 消息 ID

        Returns:
            bool: 是否重复
        """
        import time
        now = time.time()

        # 清理过期的记录
        expired_keys = [
            k for k, v in self._processed_messages.items()
            if now - v > self._dedup_ttl
        ]
        for k in expired_keys:
            del self._processed_messages[k]

        # 检查是否已处理
        if message_id in self._processed_messages:
            return True

        # 记录已处理
        self._processed_messages[message_id] = now
        return False

    async def handle_message(self, event: UnifiedEvent) -> str:
        """
        处理消息事件

        Args:
            event: 统一事件对象

        Returns:
            str: 回复内容
        """
        # 消息去重检查（source_id 存储了飞书的 message_id）
        message_id = event.source_id
        if message_id and self.is_duplicate(message_id):
            logger.warning(f"[FeishuWorker] 跳过重复消息: {message_id}")
            return ""

        logger.info(f"[FeishuWorker] 收到消息: {event.content[:50]}...")

        session_id = event.session_id or event.source_id

        try:
            # 使用 Chat Agent 处理消息
            result = await self.chat_agent.chat(
                session_id=session_id,
                message=event.content,
            )

            if result.success:
                return result.content
            else:
                logger.error(f"[FeishuWorker] Agent 处理失败: {result.error}")
                return "抱歉，处理消息时遇到了问题，请稍后重试。"

        except Exception as e:
            logger.error(f"[FeishuWorker] 消息处理异常: {e}")
            return "系统繁忙，请稍后再试。"


class FeishuWorker(BaseWorker):
    """
    飞书 WebSocket Worker

    使用 lark-oapi SDK 建立长连接，接收并处理消息

    使用方法：
        worker = FeishuWorker()
        await worker.start({
            "app_id": "cli_xxx",
            "app_secret": "xxx",
        })
    """

    worker_type = "feishu"
    name = "飞书 Worker"
    description = "飞书 WebSocket 长连接，接收并处理消息"

    def __init__(self):
        self._ws_client: Optional[WSClient] = None
        self._feishu_client: Optional[FeishuClient] = None
        self._handler: Optional[FeishuMessageHandler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # 记录启动时间，用于过滤旧消息
        import time
        self._start_time_ms: int = int(time.time() * 1000)

    @classmethod
    def get_required_config_fields(cls) -> list[str]:
        return ["app_id", "app_secret"]

    @classmethod
    def get_optional_config_fields(cls) -> list[str]:
        return ["encrypt_key", "verification_token"]

    def start_sync(self, config: dict) -> bool:
        """
        同步启动 Worker

        注意：lark-oapi 的 WSClient.start() 是阻塞方法，内部管理自己的事件循环，
        因此不能在已有的 asyncio 事件循环中调用。
        """
        app_id = config.get("app_id")
        app_secret = config.get("app_secret")
        agent_id = config.get("agent_id", "chat_agent")

        if not app_id or not app_secret:
            logger.error("[FeishuWorker] 缺少 app_id 或 app_secret")
            self._set_error("缺少必需配置")
            return False

        try:
            self._status = WorkerStatus.STARTING
            logger.info("[FeishuWorker] 正在启动...")

            # 同步初始化 Redis（使用临时事件循环）
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(redis_client.connect())
                logger.info("[FeishuWorker] Redis 连接成功")

                # 初始化飞书客户端
                self._feishu_client = FeishuClient()
                self._feishu_client.configure(app_id, app_secret)

                # 测试连接
                if not loop.run_until_complete(self._feishu_client.test_connection()):
                    logger.error("[FeishuWorker] 飞书连接测试失败")
                    self._set_error("飞书连接测试失败")
                    return False

                logger.info("[FeishuWorker] 飞书连接测试成功")
            finally:
                loop.close()

            # 初始化消息处理器
            self._handler = FeishuMessageHandler(agent_id)
            self._handler.set_client(self._feishu_client)

            # 加载 Agent 配置（使用临时事件循环）
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._handler.load_agent_config())
            finally:
                loop.close()

            # 创建事件处理器
            encrypt_key = config.get("encrypt_key", "")
            verification_token = config.get("verification_token", "")

            event_handler = lark.EventDispatcherHandler.builder(
                encrypt_key,
                verification_token,
            ).register_p2_im_message_receive_v1(
                self._handle_message_event
            ).build()

            # 创建 WebSocket 客户端
            self._ws_client = WSClient(
                app_id,
                app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.INFO,
            )

            logger.info("[FeishuWorker] WebSocket 长连接已建立，等待消息...")
            self._set_running(os.getpid())

            # 启动长连接（阻塞，内部管理自己的事件循环）
            self._ws_client.start()

            return True

        except Exception as e:
            logger.error(f"[FeishuWorker] 启动失败: {e}")
            self._set_error(str(e))
            return False

    async def start(self, config: dict) -> bool:
        """异步启动 Worker（用于 API 调用，但实际执行在子进程中）"""
        # 注意：此方法只用于测试或 API 兼容
        # 实际运行时应使用 start_sync() 或作为子进程启动
        return self.start_sync(config)

    async def stop(self) -> bool:
        """停止 Worker"""
        logger.info("[FeishuWorker] 正在停止...")
        self._status = WorkerStatus.STOPPING

        try:
            if self._ws_client:
                self._ws_client.stop()

            await redis_client.disconnect()

            self._set_stopped()
            logger.info("[FeishuWorker] 已停止")
            return True

        except Exception as e:
            logger.error(f"[FeishuWorker] 停止失败: {e}")
            return False

    async def test_connection(self, config: dict) -> tuple[bool, str]:
        """测试飞书连接"""
        app_id = config.get("app_id")
        app_secret = config.get("app_secret")

        if not app_id or not app_secret:
            return False, "缺少 app_id 或 app_secret"

        try:
            client = FeishuClient()
            client.configure(app_id, app_secret)
            success = await client.test_connection()

            if success:
                return True, "连接成功"
            else:
                return False, "连接失败，请检查 App ID 和 App Secret"

        except Exception as e:
            return False, str(e)

    def _handle_message_event(self, data: P2ImMessageReceiveV1) -> None:
        """
        处理飞书消息事件（同步回调）

        lark-oapi 的事件回调是同步的，需要在内部处理异步逻辑
        """
        try:
            event = data.event
            message = event.message

            # 非文本消息：回复提示
            if message.message_type != "text":
                logger.info(f"[FeishuWorker] 收到非文本消息: {message.message_type}")
                # 回复用户暂不支持
                import json
                try:
                    from app.adapters.feishu import FeishuClient
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(
                        self._feishu_client.reply_message(
                            message_id=message.message_id,
                            msg_type="text",
                            content=json.dumps({"text": f"暂时只支持文本消息，收到的是: {message.message_type}"}),
                        )
                    )
                    loop.close()
                except Exception as e:
                    logger.error(f"[FeishuWorker] 回复非文本消息失败: {e}")
                return

            # 过滤旧消息：忽略 Worker 启动前的消息
            # 飞书 WebSocket 重连时会推送历史未确认消息
            import time
            if hasattr(message, 'create_time') and message.create_time:
                msg_time_ms = int(message.create_time)
                # Worker 启动时间（毫秒）
                if hasattr(self, '_start_time_ms'):
                    if msg_time_ms < self._start_time_ms:
                        logger.warning(f"[FeishuWorker] 跳过旧消息: {message.message_id} (消息时间: {msg_time_ms}, 启动时间: {self._start_time_ms})")
                        return

            # 解析消息内容
            import json
            content_dict = json.loads(message.content)
            text = content_dict.get("text", "")

            if not text:
                return

            # 构建统一事件
            unified_event = UnifiedEvent(
                event_type="chat",
                source="feishu",
                source_id=message.message_id,
                user_external_id=event.sender.sender_id.open_id,
                session_id=message.chat_id,
                content=text,
                raw_data={
                    "message_id": message.message_id,
                    "chat_id": message.chat_id,
                    "chat_type": message.chat_type,
                    "sender": {
                        "sender_id": event.sender.sender_id.open_id,
                        "sender_type": event.sender.sender_type,
                    },
                },
            )

            # 使用线程池执行异步代码，避免嵌套事件循环问题
            # lark-oapi 的 WebSocket 客户端内部有自己的事件循环
            def run_in_thread():
                """在独立线程中运行异步代码"""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    reply = loop.run_until_complete(
                        self._handler.handle_message(unified_event)
                    )
                    # 如果回复为空（重复消息），跳过回复
                    if not reply:
                        return
                    loop.run_until_complete(
                        self._feishu_client.reply_message(
                            message_id=message.message_id,
                            msg_type="text",
                            content=json.dumps({"text": reply}),
                        )
                    )
                except Exception as e:
                    logger.error(f"[FeishuWorker] 消息处理线程异常: {e}")
                finally:
                    loop.close()

            # 提交到线程池执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(run_in_thread)

        except Exception as e:
            logger.error(f"[FeishuWorker] 处理消息失败: {e}")


# ==================== 独立进程模式 ====================

def _load_llm_settings_sync() -> None:
    """从数据库同步加载 LLM 设置到环境变量"""
    import asyncpg
    from app.core.config import settings as app_settings

    async def _fetch_settings():
        db_url = app_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        try:
            rows = await conn.fetch(
                "SELECT key, value FROM system_settings WHERE category = 'llm'"
            )
            return rows
        finally:
            await conn.close()

    try:
        loop = asyncio.new_event_loop()
        rows = loop.run_until_complete(_fetch_settings())
        loop.close()

        for row in rows:
            key, value = row['key'], row['value']
            if key == "llm.anthropic_api_key" and value:
                os.environ["ANTHROPIC_API_KEY"] = value
                logger.info("[FeishuWorker] 已设置 ANTHROPIC_API_KEY")
            elif key == "llm.openai_api_key" and value:
                os.environ["OPENAI_API_KEY"] = value
                logger.info("[FeishuWorker] 已设置 OPENAI_API_KEY")
            elif key == "llm.default_model" and value:
                os.environ["DEFAULT_LLM_MODEL"] = value
                logger.info(f"[FeishuWorker] 已设置 DEFAULT_LLM_MODEL: {value}")

    except Exception as e:
        logger.error(f"[FeishuWorker] 加载 LLM 设置失败: {e}")


def main():
    """主函数（独立进程模式）"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="飞书 WebSocket Worker")
    parser.add_argument("--worker-id", help="Worker 配置 ID")
    parser.add_argument("--app-id", required=True, help="飞书 App ID")
    parser.add_argument("--app-secret", required=True, help="飞书 App Secret")
    parser.add_argument("--encrypt-key", default="", help="加密密钥")
    parser.add_argument("--verification-token", default="", help="验证令牌")
    parser.add_argument("--agent-id", default="chat_agent", help="绑定的 Agent ID")
    args = parser.parse_args()

    # 初始化日志
    setup_logging()

    logger.info("=" * 60)
    logger.info("飞书 WebSocket Worker 启动")
    logger.info(f"  Worker ID: {args.worker_id or '(未指定)'}")
    logger.info(f"  App ID: {args.app_id[:8]}...")
    logger.info(f"  Agent: {args.agent_id}")
    logger.info("=" * 60)

    # 加载 LLM 设置
    _load_llm_settings_sync()

    # 创建 Worker 并启动
    worker = FeishuWorker()

    config = {
        "app_id": args.app_id,
        "app_secret": args.app_secret,
        "encrypt_key": args.encrypt_key,
        "verification_token": args.verification_token,
        "agent_id": args.agent_id,
    }

    # 同步启动（WSClient.start() 内部管理事件循环）
    try:
        worker.start_sync(config)
    except KeyboardInterrupt:
        logger.info("[FeishuWorker] 收到中断信号")
        # 停止 Worker
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(worker.stop())
        finally:
            loop.close()


# ==================== 进程管理（供 FastAPI 启动时调用） ====================

import subprocess
import signal

_feishu_process: Optional[subprocess.Popen] = None


async def load_config_from_db() -> tuple[str, str]:
    """
    从数据库加载飞书配置

    优先从 worker_configs 表读取，如果没有再从 system_settings 读取（兼容旧配置）

    Returns:
        tuple[str, str]: (app_id, app_secret)
    """
    from sqlalchemy import select
    from app.models.settings import SystemSetting

    async with async_session_maker() as session:
        # 1. 优先从 worker_configs 表读取
        try:
            from app.models.worker import WorkerConfig
            result = await session.execute(
                select(WorkerConfig).where(
                    WorkerConfig.worker_type == "feishu",
                    WorkerConfig.is_enabled == True,
                )
            )
            worker_config = result.scalar_one_or_none()
            if worker_config and worker_config.config:
                app_id = worker_config.config.get("app_id", "")
                app_secret = worker_config.config.get("app_secret", "")
                if app_id and app_secret:
                    logger.info(f"[FeishuWorker] 从 worker_configs 加载配置: {worker_config.name}")
                    return app_id, app_secret
        except Exception as e:
            logger.warning(f"[FeishuWorker] 从 worker_configs 加载失败: {e}")

        # 2. 兼容：从 system_settings 读取（旧配置）
        result = await session.execute(
            select(SystemSetting).where(
                SystemSetting.key.in_([
                    "feishu.app_id",
                    "feishu.app_secret",
                ])
            )
        )
        settings_dict = {s.key: s.value for s in result.scalars().all()}

    app_id = settings_dict.get("feishu.app_id", "")
    app_secret = settings_dict.get("feishu.app_secret", "")

    return app_id, app_secret


def load_config_from_db_sync() -> tuple[str, str]:
    """
    从数据库同步加载飞书配置

    Returns:
        tuple[str, str]: (app_id, app_secret)
    """
    async def _load():
        return await load_config_from_db()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_load())
    finally:
        loop.close()


async def is_feishu_enabled() -> bool:
    """
    检查飞书是否已启用

    优先从 worker_configs 表检查，兼容 system_settings（旧配置）

    Returns:
        bool: 是否启用
    """
    from sqlalchemy import select
    from app.models.settings import SystemSetting

    try:
        async with async_session_maker() as session:
            # 1. 优先从 worker_configs 检查
            try:
                from app.models.worker import WorkerConfig
                result = await session.execute(
                    select(WorkerConfig).where(
                        WorkerConfig.worker_type == "feishu",
                        WorkerConfig.is_enabled == True,
                    )
                )
                worker_config = result.scalar_one_or_none()
                if worker_config:
                    return True
            except Exception as e:
                logger.debug(f"检查 worker_configs 失败: {e}")

            # 2. 兼容：检查 system_settings（旧配置）
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "feishu.enabled")
            )
            setting = result.scalar_one_or_none()
            return setting and setting.value == "true"
    except Exception as e:
        logger.warning(f"检查飞书配置失败: {e}")
        return False


async def start_feishu_worker_if_enabled() -> bool:
    """
    如果飞书已启用，自动启动 Worker（作为独立子进程）

    这个函数在 FastAPI 启动时调用

    Returns:
        bool: 是否成功启动
    """
    global _feishu_process

    # 检查是否已启用
    if not await is_feishu_enabled():
        logger.info("[Feishu] 飞书未启用，跳过 Worker 启动")
        return False

    # 检查配置是否完整
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        logger.info("[Feishu] 环境变量未配置，尝试从数据库加载...")
        try:
            app_id, app_secret = await load_config_from_db()
        except Exception as e:
            logger.error(f"[Feishu] 从数据库加载配置失败: {e}")
            return False

    if not app_id or not app_secret:
        logger.warning("[Feishu] 飞书已启用但配置不完整，跳过 Worker 启动")
        return False

    # 作为独立子进程启动
    try:
        import sys
        python_path = sys.executable
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(os.path.dirname(project_root), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "feishu.log")

        # 打开日志文件
        log_handle = open(log_file, "a")

        # 启动子进程
        _feishu_process = subprocess.Popen(
            [
                python_path, "-m", "app.workers.feishu_worker",
                "--app-id", app_id,
                "--app-secret", app_secret,
            ],
            cwd=project_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # 创建新会话，避免信号传播
        )

        logger.info(f"[Feishu] Worker 已作为独立进程启动 (PID: {_feishu_process.pid})")
        logger.info(f"[Feishu] Worker 日志: {log_file}")
        return True

    except Exception as e:
        logger.error(f"[Feishu] 启动 Worker 进程失败: {e}")
        return False


async def stop_feishu_worker() -> None:
    """
    停止飞书 Worker

    这个函数在 FastAPI 关闭时调用
    """
    global _feishu_process

    if _feishu_process:
        logger.info(f"[Feishu] 正在停止 Worker 进程 (PID: {_feishu_process.pid})...")
        try:
            _feishu_process.terminate()
            _feishu_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _feishu_process.kill()
        except Exception as e:
            logger.warning(f"[Feishu] 停止进程时出错: {e}")
        _feishu_process = None
        logger.info("[Feishu] Worker 进程已停止")


def get_feishu_worker_status() -> dict:
    """
    获取飞书 Worker 状态

    Returns:
        dict: 状态信息
    """
    global _feishu_process

    # 检查子进程是否还在运行
    if _feishu_process and _feishu_process.poll() is None:
        return {
            "running": True,
            "pid": _feishu_process.pid,
        }

    # 也检查是否有其他飞书 Worker 进程在运行
    import shutil
    if shutil.which("pgrep"):
        try:
            result = subprocess.run(
                ["pgrep", "-f", "app.workers.feishu_worker"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                return {
                    "running": True,
                    "pid": int(pids[0]),
                }
        except Exception:
            pass

    return {
        "running": False,
        "pid": None,
    }


if __name__ == "__main__":
    main()
