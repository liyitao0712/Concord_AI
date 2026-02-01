# app/core/config.py
# 配置管理模块
#
# 功能说明：
# 1. 使用 Pydantic Settings 从环境变量加载配置
# 2. 支持 .env 文件读取
# 3. 提供类型安全的配置访问
#
# 使用方法：
#   from app.core.config import settings
#   print(settings.APP_NAME)

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """
    应用配置类

    所有配置项都可以通过环境变量覆盖，环境变量名与属性名相同（大写）
    例如：设置 DEBUG=true 环境变量会覆盖 DEBUG 的默认值
    """

    # ==================== 应用基础配置 ====================
    APP_NAME: str = "Concord AI"      # 应用名称，显示在日志和API文档中
    DEBUG: bool = False                # 调试模式：True 时输出详细日志和 SQL 查询

    # ==================== 日志配置 ====================
    # 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
    # - DEBUG: 开发调试信息（SQL查询、详细请求信息）
    # - INFO: 正常运行信息（请求日志、业务流程）
    # - WARNING: 警告信息（可能的问题，但不影响运行）
    # - ERROR: 错误信息（需要关注的问题）
    # - CRITICAL: 严重错误（系统无法正常运行）
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # 日志格式：console（彩色控制台输出）或 json（结构化JSON，适合生产环境）
    LOG_FORMAT: Literal["console", "json"] = "console"

    # ==================== 数据库配置 ====================
    # 数据库连接字符串格式：postgresql+asyncpg://用户名:密码@主机:端口/数据库名
    # asyncpg 是异步 PostgreSQL 驱动，性能更好
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/concord"

    # ==================== Redis 配置 ====================
    # Redis 连接字符串格式：redis://主机:端口/数据库编号
    # 用于缓存、Session、消息队列等
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== LLM 配置 ====================
    # Anthropic API Key，用于调用 Claude 模型
    # 获取方式：https://console.anthropic.com/
    ANTHROPIC_API_KEY: str = ""

    # OpenAI API Key（可选），用于调用 GPT 模型
    OPENAI_API_KEY: str = ""

    # Google Gemini API Key（可选）
    # 获取方式：https://ai.google.dev
    GEMINI_API_KEY: str = ""

    # 阿里千问 API Key（可选）
    # 获取方式：https://dashscope.console.aliyun.com
    DASHSCOPE_API_KEY: str = ""

    # 火山引擎 API Key（可选）
    # 获取方式：https://console.volcengine.com
    VOLCENGINE_API_KEY: str = ""

    # 默认使用的 LLM 模型
    # 支持：claude-3-opus-20240229, claude-3-sonnet-20240229, gpt-4, gpt-3.5-turbo 等
    DEFAULT_LLM_MODEL: str = "claude-sonnet-4-20250514"

    # ==================== 邮件配置 (IMAP) ====================
    # IMAP 服务器地址，常见的有：
    # - QQ邮箱: imap.qq.com
    # - 163邮箱: imap.163.com
    # - Gmail: imap.gmail.com
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993           # IMAP SSL 端口，一般是 993
    IMAP_USER: str = ""            # 邮箱账号
    IMAP_PASSWORD: str = ""        # 授权码（不是登录密码！）
    IMAP_USE_SSL: bool = True      # 是否使用 SSL 加密

    # ==================== 邮件配置 (SMTP) ====================
    # SMTP 服务器地址，常见的有：
    # - QQ邮箱: smtp.qq.com
    # - 163邮箱: smtp.163.com
    # - Gmail: smtp.gmail.com
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465           # SMTP SSL 端口，一般是 465（SSL）或 587（STARTTLS）
    SMTP_USER: str = ""            # 发件人邮箱账号
    SMTP_PASSWORD: str = ""        # 授权码（不是登录密码！）
    SMTP_USE_TLS: bool = True      # 是否使用 SSL/TLS 加密
    SMTP_START_TLS: bool = False   # 是否使用 STARTTLS（端口 587 时使用）

    # ==================== 阿里云 OSS 配置 ====================
    # OSS Access Key ID，在阿里云控制台获取
    # 获取方式：https://ram.console.aliyun.com/manage/ak
    OSS_ACCESS_KEY_ID: str = ""

    # OSS Access Key Secret
    OSS_ACCESS_KEY_SECRET: str = ""

    # OSS Endpoint（地域节点）
    # 常见的有：
    # - 杭州: oss-cn-hangzhou.aliyuncs.com
    # - 上海: oss-cn-shanghai.aliyuncs.com
    # - 北京: oss-cn-beijing.aliyuncs.com
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"

    # OSS Bucket 名称（存储桶）
    OSS_BUCKET: str = ""

    # ==================== 本地文件存储配置 ====================
    # 本地文件存储根目录（当 OSS 未配置或失败时使用）
    LOCAL_STORAGE_PATH: str = "data/storage"

    # 本地文件是否启用（优先级低于 OSS，OSS 可用时不使用本地存储）
    LOCAL_STORAGE_ENABLED: bool = True

    # ==================== Temporal 配置 ====================
    # Temporal Server 地址
    # 开发环境使用 docker-compose 启动的 Temporal：localhost:7233
    # 生产环境使用 Temporal Cloud 或自建集群
    TEMPORAL_HOST: str = "localhost:7233"

    # Temporal 命名空间
    # 用于隔离不同环境/租户的工作流
    TEMPORAL_NAMESPACE: str = "default"

    # 任务队列名称
    # Worker 监听这个队列来执行 Workflow 和 Activity
    TEMPORAL_TASK_QUEUE: str = "concord-main-queue"

    # ==================== 飞书机器人配置 ====================
    # 飞书应用 App ID 和 Secret
    # 获取方式：https://open.feishu.cn/app 创建应用
    # 也可在管理后台动态配置，无需在环境变量中设置
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""

    # ==================== JWT 认证配置 ====================
    # JWT 密钥，用于签名和验证 Token
    # 重要：生产环境必须更换为随机生成的强密钥！
    # 生成方法：python -c "import secrets; print(secrets.token_urlsafe(32))"
    JWT_SECRET: str = "your-secret-key-change-in-production"

    # JWT 签名算法，HS256 是常用的对称加密算法
    JWT_ALGORITHM: str = "HS256"

    # Access Token 过期时间（分钟）
    # 建议 15-60 分钟，过短影响体验，过长有安全风险
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # Refresh Token 过期时间（天）
    # 用于刷新 Access Token，一般 7-30 天
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        """Pydantic 配置类"""
        env_file = ".env"              # 从 .env 文件读取环境变量
        env_file_encoding = "utf-8"    # 文件编码
        case_sensitive = True          # 环境变量名区分大小写


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）

    使用 @lru_cache 装饰器确保整个应用只创建一个 Settings 实例
    避免重复读取环境变量和 .env 文件

    Returns:
        Settings: 配置实例
    """
    return Settings()


# 导出配置实例，方便其他模块使用
# 使用方式：from app.core.config import settings
settings = get_settings()
