# app/main.py
# FastAPI 应用入口
#
# 功能说明：
# 1. 创建 FastAPI 应用实例
# 2. 配置中间件（CORS、日志）
# 3. 注册路由
# 4. 管理应用生命周期（启动/关闭）
#
# 启动命令：
#   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
#
# API 文档：
#   - Swagger UI: http://localhost:8000/docs
#   - ReDoc: http://localhost:8000/redoc

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_client
from app.core.logging import setup_logging, get_logger, RequestLoggingMiddleware
from app.workers import worker_manager

# 导入路由模块
from app.api import health
from app.api import auth
from app.api import llm
from app.api import admin
from app.api import agents
from app.api import settings as settings_router
from app.api import admin_monitor
from app.api import chat
from app.api import email_accounts
from app.api import workers as workers_router
from app.api import emails as emails_router
from app.api import prompts as prompts_router
from app.api import llm_models
from app.api import work_types as work_types_router
from app.api import customers as customers_router
from app.api import suppliers as suppliers_router
from app.api import customer_suggestions as customer_suggestions_router
from app.api import categories as categories_router
from app.api import products as products_router
from app.api import countries as countries_router
from app.api import trade_terms_ref as trade_terms_ref_router
from app.api import payment_methods_ref as payment_methods_ref_router
from app.api import upload as upload_router
from app.api import storage as storage_router


# 初始化日志系统（在应用启动前）
setup_logging()

# 获取当前模块的 logger
logger = get_logger(__name__)


async def load_llm_settings_from_db():
    """
    从数据库加载 LLM 设置到环境变量

    管理后台配置的 LLM API Key 存储在 system_settings 表中，
    需要在应用启动时加载到环境变量，供 LiteLLM 使用。
    """
    import os
    from sqlalchemy import text
    from app.core.database import async_session_maker

    try:
        async with async_session_maker() as session:
            # 从 llm_model_config 表加载已配置且启用的模型
            from app.models import LLMModelConfig
            from sqlalchemy import select

            query = select(LLMModelConfig).where(
                LLMModelConfig.is_enabled == True,
                LLMModelConfig.is_configured == True
            ).order_by(LLMModelConfig.created_at)

            result = await session.execute(query)
            models = result.scalars().all()

            if models:
                # 使用第一个已配置的模型作为默认模型
                default_model = models[0]
                os.environ["DEFAULT_LLM_MODEL"] = default_model.model_id
                logger.info(f"已设置默认模型: {default_model.model_id} ({default_model.model_name})")

                # 加载所有模型的 API Key 到环境变量
                api_keys_loaded = set()
                for model in models:
                    if model.api_key:
                        # 根据提供商设置对应的环境变量
                        if model.provider == "anthropic" and "ANTHROPIC_API_KEY" not in api_keys_loaded:
                            os.environ["ANTHROPIC_API_KEY"] = model.api_key
                            logger.info(f"已加载 Anthropic API Key (来自模型: {model.model_name})")
                            api_keys_loaded.add("ANTHROPIC_API_KEY")
                        elif model.provider == "openai" and "OPENAI_API_KEY" not in api_keys_loaded:
                            os.environ["OPENAI_API_KEY"] = model.api_key
                            logger.info(f"已加载 OpenAI API Key (来自模型: {model.model_name})")
                            api_keys_loaded.add("OPENAI_API_KEY")
                        elif model.provider == "gemini" and "GEMINI_API_KEY" not in api_keys_loaded:
                            os.environ["GEMINI_API_KEY"] = model.api_key
                            logger.info(f"已加载 Gemini API Key (来自模型: {model.model_name})")
                            api_keys_loaded.add("GEMINI_API_KEY")
                        elif model.provider == "qwen" and "DASHSCOPE_API_KEY" not in api_keys_loaded:
                            os.environ["DASHSCOPE_API_KEY"] = model.api_key
                            logger.info(f"已加载 DashScope API Key (来自模型: {model.model_name})")
                            api_keys_loaded.add("DASHSCOPE_API_KEY")
                        elif model.provider == "volcengine" and "VOLCENGINE_API_KEY" not in api_keys_loaded:
                            os.environ["VOLCENGINE_API_KEY"] = model.api_key
                            logger.info(f"已加载 VolcEngine API Key (来自模型: {model.model_name})")
                            api_keys_loaded.add("VOLCENGINE_API_KEY")

                logger.info(f"共加载 {len(models)} 个 LLM 模型配置")
            else:
                logger.warning(
                    "数据库中没有已配置的 LLM 模型！"
                    "请在管理员后台的 LLM 配置页面添加模型并设置 API Key。"
                )

    except Exception as e:
        logger.warning(f"从数据库加载 LLM 模型配置失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    这个函数管理应用的启动和关闭事件
    - 启动时：连接 Redis、初始化数据库等
    - 关闭时：断开连接、清理资源等

    使用 asynccontextmanager 装饰器，yield 之前是启动逻辑，之后是关闭逻辑
    """
    # ==================== 启动阶段 ====================
    logger.info(f"正在启动 {settings.APP_NAME}...")

    # 从数据库加载 LLM 配置
    await load_llm_settings_from_db()

    # 连接 Redis
    try:
        await redis_client.connect()
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.error(f"Redis 连接失败: {e}")
        # Redis 连接失败不阻止应用启动，但某些功能可能不可用

    # 可选：初始化数据库（如果不使用 Alembic 迁移）
    # await init_db()
    # logger.info("数据库初始化完成")

    # 自动启动所有已启用的 Worker
    try:
        results = await worker_manager.start_all_enabled()
        started_count = sum(1 for success, _ in results.values() if success)
        if started_count > 0:
            logger.info(f"已启动 {started_count} 个 Worker")
    except Exception as e:
        logger.warning(f"Worker 启动失败: {e}")

    logger.info(f"{settings.APP_NAME} 启动完成")
    logger.info(f"API 文档: http://localhost:8000/docs")

    # yield 将控制权交给应用
    yield

    # ==================== 关闭阶段 ====================
    logger.info("正在关闭...")

    # 停止所有 Worker
    try:
        await worker_manager.stop_all()
    except Exception as e:
        logger.warning(f"停止 Worker 时出错: {e}")

    # 断开 Redis 连接
    try:
        await redis_client.disconnect()
        logger.info("Redis 连接已断开")
    except Exception as e:
        logger.warning(f"Redis 断开连接时出错: {e}")

    # 关闭数据库连接
    try:
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.warning(f"数据库关闭时出错: {e}")

    logger.info("清理完成，应用已关闭")


# ==================== 创建 FastAPI 应用 ====================

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Concord AI - 智能业务自动化平台

    ## 功能模块

    - **认证**: 用户注册、登录、Token 管理
    - **LLM**: AI 对话、意图分类、实体提取
    - **健康检查**: 服务状态监控

    ## 认证说明

    大部分接口需要认证，请先通过 `/api/auth/login` 获取 Token，
    然后在请求头中添加：`Authorization: Bearer <token>`
    """,
    version="0.1.0",
    lifespan=lifespan,
    # 配置文档页面
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc
    openapi_url="/openapi.json",
)


# ==================== 中间件配置 ====================

# CORS 中间件（跨域资源共享）
# 允许前端应用从不同域名访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 生产环境应该配置具体的域名
    allow_credentials=True,     # 允许携带 Cookie
    allow_methods=["*"],        # 允许所有 HTTP 方法
    allow_headers=["*"],        # 允许所有请求头
)

# 请求日志中间件
# 记录每个请求的方法、路径、耗时、状态码
app.add_middleware(RequestLoggingMiddleware)


# ==================== 全局异常处理 ====================

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理 HTTP 异常，确保包含 CORS 头"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}")
    import traceback
    traceback.print_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"服务器内部错误: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ==================== 注册路由 ====================

# 健康检查路由
# - GET /health - 基础健康检查
# - GET /health/detailed - 详细健康检查
app.include_router(health.router)

# 认证路由
# - POST /api/auth/register - 用户注册
# - POST /api/auth/login - 用户登录
# - POST /api/auth/refresh - 刷新 Token
# - GET /api/auth/me - 获取当前用户
app.include_router(auth.router)

# LLM 路由
# - POST /api/llm/chat - 普通对话
# - POST /api/llm/stream - 流式对话
# - POST /api/llm/classify - 意图分类
app.include_router(llm.router)

# 管理员路由（需要管理员权限）
# - GET /admin/stats - 系统统计
# - GET /admin/users - 用户列表
# - POST /admin/users - 创建用户
# - PUT /admin/users/{id} - 更新用户
# - DELETE /admin/users/{id} - 删除用户
# - POST /admin/users/{id}/toggle - 启用/禁用用户
# - POST /admin/users/{id}/reset-password - 重置密码
app.include_router(admin.router)

# Agent 路由（AI Agent 调用）
# - GET /api/agents - 列出所有 Agent
# - GET /api/agents/{name} - 获取 Agent 信息
# - POST /api/agents/{name}/run - 执行 Agent
# - POST /api/agents/analyze/email - 分析邮件
# - POST /api/agents/classify/intent - 意图分类
app.include_router(agents.router)

# 系统设置路由（仅管理员）
# - GET /admin/settings/llm - 获取 LLM 配置
# - PUT /admin/settings/llm - 更新 LLM 配置
# - POST /admin/settings/llm/test - 测试 LLM 连接
# - GET /admin/settings/email - 获取邮件配置
# - PUT /admin/settings/email - 更新邮件配置
# - GET /admin/settings/feishu - 获取飞书配置
# - PUT /admin/settings/feishu - 更新飞书配置
app.include_router(settings_router.router)

# 监控路由（仅管理员，只读）
# - GET /admin/monitor/summary - 监控摘要
# - GET /admin/monitor/workflows - 工作流列表
# - GET /admin/monitor/agents - Agent 统计
app.include_router(admin_monitor.router)

# Chat 路由（SSE 流式对话）
# - POST /api/chat/sessions - 创建会话
# - GET /api/chat/sessions - 会话列表
# - GET /api/chat/sessions/{id} - 会话详情
# - DELETE /api/chat/sessions/{id} - 删除会话
# - GET /api/chat/sessions/{id}/messages - 消息历史
# - POST /api/chat/stream - SSE 流式对话
# - POST /api/chat/send - 非流式对话
app.include_router(chat.router)

# 邮箱账户管理路由（仅管理员）
# - GET /admin/email-accounts - 邮箱账户列表
# - POST /admin/email-accounts - 创建邮箱账户
# - GET /admin/email-accounts/{id} - 邮箱账户详情
# - PUT /admin/email-accounts/{id} - 更新邮箱账户
# - DELETE /admin/email-accounts/{id} - 删除邮箱账户
# - PUT /admin/email-accounts/{id}/default - 设为默认
# - POST /admin/email-accounts/{id}/test - 测试连接
app.include_router(email_accounts.router)

# Worker 管理路由（仅管理员）
# - GET /admin/workers - Worker 列表
# - POST /admin/workers - 创建 Worker
# - GET /admin/workers/{id} - Worker 详情
# - PUT /admin/workers/{id} - 更新 Worker
# - DELETE /admin/workers/{id} - 删除 Worker
# - POST /admin/workers/{id}/start - 启动 Worker
# - POST /admin/workers/{id}/stop - 停止 Worker
# - POST /admin/workers/{id}/restart - 重启 Worker
# - POST /admin/workers/{id}/test - 测试连接
app.include_router(workers_router.router)

# 邮件记录路由（仅管理员）
# - GET /admin/emails - 邮件列表
# - GET /admin/emails/{id} - 邮件详情
# - GET /admin/emails/{id}/raw - 下载原始邮件
# - GET /admin/emails/{id}/attachments/{att_id} - 下载附件
# - POST /admin/emails/{id}/analyze - 分析邮件意图
# - POST /admin/emails/{id}/execute - 执行邮件处理
app.include_router(emails_router.router)

# 工作类型管理路由（仅管理员）
# - GET/POST /admin/work-types - 工作类型 CRUD
# - GET /admin/work-types/tree - 树形结构
# - GET /admin/work-type-suggestions - 建议列表
# - POST /admin/work-type-suggestions/{id}/approve - 批准建议
# - POST /admin/work-type-suggestions/{id}/reject - 拒绝建议
app.include_router(work_types_router.router)
app.include_router(work_types_router.suggestions_router)

# Prompt 模板管理路由（仅管理员）
# - GET /admin/prompts - Prompt 列表
# - GET /admin/prompts/{name} - Prompt 详情
# - PUT /admin/prompts/{name} - 更新 Prompt
# - POST /admin/prompts/{name}/test - 测试渲染
app.include_router(prompts_router.router)

# LLM 模型配置路由（仅管理员）
# - GET /admin/llm/models - 模型列表
# - GET /admin/llm/models/{model_id} - 模型详情
# - PUT /admin/llm/models/{model_id} - 更新模型配置
# - POST /admin/llm/models/{model_id}/test - 测试模型连接
# - GET /admin/llm/models/stats/usage - 使用统计
app.include_router(llm_models.router)

# 客户管理路由（仅管理员）
# - GET/POST /admin/customers - 客户 CRUD
# - GET/PUT/DELETE /admin/customers/{id} - 客户详情/更新/删除
# - GET/POST /admin/contacts - 联系人 CRUD
# - GET/PUT/DELETE /admin/contacts/{id} - 联系人详情/更新/删除
app.include_router(customers_router.router)
app.include_router(customers_router.contacts_router)

# 客户建议审批路由（仅管理员）
# - GET /admin/customer-suggestions - 建议列表
# - GET /admin/customer-suggestions/{id} - 建议详情
# - POST /admin/customer-suggestions/{id}/approve - 批准建议
# - POST /admin/customer-suggestions/{id}/reject - 拒绝建议
app.include_router(customer_suggestions_router.router)

# 供应商管理路由（仅管理员）
# - GET/POST /admin/suppliers - 供应商 CRUD
# - GET/PUT/DELETE /admin/suppliers/{id} - 供应商详情/更新/删除
# - GET/POST /admin/supplier-contacts - 供应商联系人 CRUD
# - GET/PUT/DELETE /admin/supplier-contacts/{id} - 供应商联系人详情/更新/删除
app.include_router(suppliers_router.router)
app.include_router(suppliers_router.supplier_contacts_router)

# 品类管理路由（仅管理员）
# - GET/POST /admin/categories - 品类 CRUD
# - GET /admin/categories/tree - 品类树形结构
# - GET/PUT/DELETE /admin/categories/{id} - 品类详情/更新/删除
app.include_router(categories_router.router)

# 产品管理路由（仅管理员）
# - GET/POST /admin/products - 产品 CRUD
# - GET/PUT/DELETE /admin/products/{id} - 产品详情/更新/删除
# - POST /admin/products/{id}/suppliers - 添加供应商关联
# - PUT/DELETE /admin/products/{id}/suppliers/{supplier_id} - 更新/移除供应商关联
app.include_router(products_router.router)

# 国家数据库路由（仅管理员，只读）
# - GET /admin/countries - 国家列表
# - GET /admin/countries/{id} - 国家详情
app.include_router(countries_router.router)

# 贸易术语路由（仅管理员，只读）
# - GET /admin/trade-terms - 贸易术语列表
# - GET /admin/trade-terms/{id} - 贸易术语详情
app.include_router(trade_terms_ref_router.router)

# 付款方式路由（仅管理员，只读）
# - GET /admin/payment-methods - 付款方式列表
# - GET /admin/payment-methods/{id} - 付款方式详情
app.include_router(payment_methods_ref_router.router)

# 文件上传路由（仅管理员）
# - POST /admin/upload - 通用文件上传
app.include_router(upload_router.router)

# 文件下载路由（公开，通过 token 验证）
# - GET /api/storage/download/{key} - 临时链接下载
app.include_router(storage_router.router)


# ==================== 根路由 ====================

@app.get("/", tags=["Root"])
async def root():
    """
    根路由

    返回应用基本信息和文档链接
    """
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
