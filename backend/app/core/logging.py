# app/core/logging.py
# 日志配置模块
#
# 功能说明：
# 1. 统一管理应用日志输出
# 2. 支持两种格式：彩色控制台（开发）和 JSON（生产）
# 3. 自动记录请求信息（中间件）
# 4. 与 Temporal、SQLAlchemy、uvicorn 等库兼容
#
# 使用方法：
#   from app.core.logging import get_logger
#   logger = get_logger(__name__)
#   logger.info("这是一条日志")
#
# 日志级别说明：
#   DEBUG    - 调试信息，开发时使用
#   INFO     - 正常运行信息
#   WARNING  - 警告，不影响运行但需要关注
#   ERROR    - 错误，需要处理
#   CRITICAL - 严重错误，系统可能无法运行

import logging
import sys
import json
import time
from datetime import datetime
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


# ==================== 彩色输出支持 ====================
# ANSI 颜色代码，用于在终端中显示彩色文字
# 格式：\033[颜色代码m文字\033[0m

class Colors:
    """
    终端颜色代码

    使用方法：
        print(f"{Colors.RED}红色文字{Colors.RESET}")
    """
    RESET = "\033[0m"      # 重置颜色
    RED = "\033[31m"       # 红色 - 用于 ERROR
    GREEN = "\033[32m"     # 绿色 - 用于 INFO
    YELLOW = "\033[33m"    # 黄色 - 用于 WARNING
    BLUE = "\033[34m"      # 蓝色 - 用于 DEBUG
    MAGENTA = "\033[35m"   # 紫色 - 用于 CRITICAL
    CYAN = "\033[36m"      # 青色 - 用于时间戳
    GRAY = "\033[90m"      # 灰色 - 用于文件名等次要信息


# 日志级别对应的颜色
LEVEL_COLORS = {
    "DEBUG": Colors.BLUE,
    "INFO": Colors.GREEN,
    "WARNING": Colors.YELLOW,
    "ERROR": Colors.RED,
    "CRITICAL": Colors.MAGENTA,
}


# ==================== 自定义 Formatter ====================

class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器（开发环境使用）

    输出格式：
    2026-01-30 12:00:00 | INFO     | app.api.auth:login:42 - 用户登录成功

    各部分说明：
    - 时间戳（青色）
    - 日志级别（彩色，根据级别不同显示不同颜色）
    - 位置信息（灰色）：模块名:函数名:行号
    - 日志内容
    """

    def format(self, record: logging.LogRecord) -> str:
        # 获取时间戳
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # 获取日志级别和对应颜色
        level_name = record.levelname
        level_color = LEVEL_COLORS.get(level_name, Colors.RESET)

        # 构建位置信息：模块名:函数名:行号
        # record.name 是 logger 名称（通常是模块路径）
        # record.funcName 是函数名
        # record.lineno 是行号
        location = f"{record.name}:{record.funcName}:{record.lineno}"

        # 组装最终的日志格式
        formatted = (
            f"{Colors.CYAN}{timestamp}{Colors.RESET} | "
            f"{level_color}{level_name:8}{Colors.RESET} | "
            f"{Colors.GRAY}{location}{Colors.RESET} - "
            f"{record.getMessage()}"
        )

        # 如果有异常信息，添加到日志中
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class JSONFormatter(logging.Formatter):
    """
    JSON 日志格式化器（生产环境使用）

    输出格式（每行一个 JSON 对象）：
    {"timestamp": "2026-01-30T12:00:00", "level": "INFO", "logger": "app.api.auth", ...}

    优点：
    - 结构化数据，便于日志分析工具（如 ELK、Loki）解析
    - 包含完整的上下文信息
    """

    def format(self, record: logging.LogRecord) -> str:
        # 构建日志数据字典
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # 如果有异常信息，添加到日志中
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 如果有额外的上下文信息（通过 extra 参数传入）
        # 例如：logger.info("message", extra={"user_id": 123})
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


# ==================== Logger 工厂函数 ====================

def setup_logging() -> None:
    """
    初始化日志系统

    这个函数应该在应用启动时调用一次
    会根据配置设置日志级别和格式

    调用位置：app/main.py 的 lifespan 函数中
    """
    # 获取根 logger
    root_logger = logging.getLogger()

    # 设置日志级别
    root_logger.setLevel(settings.LOG_LEVEL)

    # 清除已有的 handler（避免重复添加）
    root_logger.handlers.clear()

    # 创建控制台输出 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)

    # 根据配置选择格式化器
    if settings.LOG_FORMAT == "json":
        # 生产环境：JSON 格式
        formatter = JSONFormatter()
    else:
        # 开发环境：彩色控制台格式
        formatter = ColoredFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 设置第三方库的日志级别（避免过多输出）
    # uvicorn 的访问日志保留 INFO 级别
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # uvicorn 错误日志保留
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    # SQLAlchemy 引擎日志（SQL 查询）在 DEBUG 模式下显示
    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # httpx（HTTP 客户端）日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # httpcore 日志
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例

    每个模块应该使用自己的 logger，传入模块名（通常是 __name__）

    Args:
        name: logger 名称，通常传入 __name__

    Returns:
        logging.Logger: logger 实例

    使用示例：
        # 在模块顶部
        from app.core.logging import get_logger
        logger = get_logger(__name__)

        # 在代码中使用
        logger.debug("调试信息")
        logger.info("普通信息")
        logger.warning("警告信息")
        logger.error("错误信息")
        logger.critical("严重错误")

        # 记录异常
        try:
            do_something()
        except Exception as e:
            logger.exception("发生错误")  # 自动包含堆栈信息
    """
    return logging.getLogger(name)


# ==================== 请求日志中间件 ====================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求日志中间件

    自动记录每个请求的：
    - 请求方法（GET/POST/PUT/DELETE 等）
    - 请求路径
    - 响应状态码
    - 处理耗时

    输出示例：
    INFO | POST /api/auth/login -> 200 OK (45ms)
    """

    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        # 使用专门的请求日志 logger
        self.logger = logger or get_logger("app.request")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录日志

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        # 调用下一个处理器
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # 如果发生异常，记录错误日志
            duration = (time.time() - start_time) * 1000
            self.logger.error(
                f"{method} {path} -> 500 ERROR ({duration:.0f}ms) - {str(e)}"
            )
            raise

        # 计算处理耗时（毫秒）
        duration = (time.time() - start_time) * 1000

        # 构建日志消息
        # 状态码 200-299 用 INFO，400-499 用 WARNING，500+ 用 ERROR
        log_message = f"{method} {path}"
        if query:
            log_message += f"?{query}"
        log_message += f" -> {status_code} ({duration:.0f}ms)"

        # 根据状态码选择日志级别
        if status_code >= 500:
            self.logger.error(log_message)
        elif status_code >= 400:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        return response


# ==================== 函数执行日志装饰器 ====================

def log_execution(logger: Optional[logging.Logger] = None):
    """
    函数执行日志装饰器

    自动记录函数的调用和返回（或异常）

    Args:
        logger: 可选的 logger 实例，不传则使用默认

    使用示例：
        @log_execution()
        async def process_email(email_id: str):
            # 处理邮件
            pass

    日志输出：
        DEBUG | 调用 process_email(email_id='123')
        DEBUG | process_email 返回: {...}
    """
    def decorator(func: Callable):
        # 获取函数所属模块的 logger
        func_logger = logger or get_logger(func.__module__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 构建参数字符串
            args_str = ", ".join([repr(a) for a in args])
            kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            all_args = ", ".join(filter(None, [args_str, kwargs_str]))

            func_logger.debug(f"调用 {func.__name__}({all_args})")

            try:
                result = await func(*args, **kwargs)
                func_logger.debug(f"{func.__name__} 返回: {result}")
                return result
            except Exception as e:
                func_logger.error(f"{func.__name__} 异常: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            args_str = ", ".join([repr(a) for a in args])
            kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            all_args = ", ".join(filter(None, [args_str, kwargs_str]))

            func_logger.debug(f"调用 {func.__name__}({all_args})")

            try:
                result = func(*args, **kwargs)
                func_logger.debug(f"{func.__name__} 返回: {result}")
                return result
            except Exception as e:
                func_logger.error(f"{func.__name__} 异常: {e}")
                raise

        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
