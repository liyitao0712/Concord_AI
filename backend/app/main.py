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
from app.api import categories as categories_router
from app.api import products as products_router
from app.api import countries as countries_router
from app.api import trade_terms_ref as trade_terms_ref_router
from app.api import payment_methods_ref as payment_methods_ref_router
from app.api import upload as upload_router
from app.api import storage as storage_router
from app.api import warehouses as warehouses_router
from app.api import inventories as inventories_router
from app.api import purchase_contracts as purchase_contracts_router
from app.api import sales_contracts as sales_contracts_router
from app.api import inbound_orders as inbound_orders_router
from app.api import outbound_orders as outbound_orders_router
from app.api import contract_numbers as contract_numbers_router
from app.api import tts as tts_router
from app.api import client_rfqs as client_rfqs_router
from app.api import quotations as quotations_router
from app.api import supplier_rfqs as supplier_rfqs_router
from app.api import supplier_quotations as supplier_quotations_router
from app.api import projects as projects_router
from app.api import tasks as tasks_router
from app.api import progress as progress_router
from app.api import project_suggestions as project_suggestions_router
from app.api import permissions_api as permissions_api_router
from app.api import organizations as organizations_router
from app.api import departments as departments_router
from app.api import roles as roles_router


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
# - GET /api/stats - 系统统计
# - GET /api/users - 用户列表
# - POST /api/users - 创建用户
# - PUT /api/users/{id} - 更新用户
# - DELETE /api/users/{id} - 删除用户
# - POST /api/users/{id}/toggle - 启用/禁用用户
# - POST /api/users/{id}/reset-password - 重置密码
app.include_router(admin.router)

# Agent 路由（AI Agent 调用）
# - GET /api/agents - 列出所有 Agent
# - GET /api/agents/{name} - 获取 Agent 信息
# - POST /api/agents/{name}/run - 执行 Agent
# - POST /api/agents/analyze/email - 分析邮件
# - POST /api/agents/classify/intent - 意图分类
app.include_router(agents.router)

# 系统设置路由（仅管理员）
# - GET /api/settings/llm - 获取 LLM 配置
# - PUT /api/settings/llm - 更新 LLM 配置
# - POST /api/settings/llm/test - 测试 LLM 连接
# - GET /api/settings/email - 获取邮件配置
# - PUT /api/settings/email - 更新邮件配置
# - GET /api/settings/feishu - 获取飞书配置
# - PUT /api/settings/feishu - 更新飞书配置
app.include_router(settings_router.router)

# 监控路由（仅管理员，只读）
# - GET /api/monitor/summary - 监控摘要
# - GET /api/monitor/workflows - 工作流列表
# - GET /api/monitor/agents - Agent 统计
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
# - GET /api/email-accounts - 邮箱账户列表
# - POST /api/email-accounts - 创建邮箱账户
# - GET /api/email-accounts/{id} - 邮箱账户详情
# - PUT /api/email-accounts/{id} - 更新邮箱账户
# - DELETE /api/email-accounts/{id} - 删除邮箱账户
# - PUT /api/email-accounts/{id}/default - 设为默认
# - POST /api/email-accounts/{id}/test - 测试连接
app.include_router(email_accounts.router)

# Worker 管理路由（仅管理员）
# - GET /api/workers - Worker 列表
# - POST /api/workers - 创建 Worker
# - GET /api/workers/{id} - Worker 详情
# - PUT /api/workers/{id} - 更新 Worker
# - DELETE /api/workers/{id} - 删除 Worker
# - POST /api/workers/{id}/start - 启动 Worker
# - POST /api/workers/{id}/stop - 停止 Worker
# - POST /api/workers/{id}/restart - 重启 Worker
# - POST /api/workers/{id}/test - 测试连接
app.include_router(workers_router.router)

# 邮件记录路由（仅管理员）
# - GET /api/emails - 邮件列表
# - GET /api/emails/{id} - 邮件详情
# - GET /api/emails/{id}/raw - 下载原始邮件
# - GET /api/emails/{id}/attachments/{att_id} - 下载附件
# - POST /api/emails/{id}/analyze - 分析邮件意图
# - POST /api/emails/{id}/execute - 执行邮件处理
app.include_router(emails_router.router)

# 工作类型管理路由（仅管理员）
# - GET/POST /api/work-types - 工作类型 CRUD
# - GET /api/work-types/tree - 树形结构
# - GET /api/work-type-suggestions - 建议列表
# - POST /api/work-type-suggestions/{id}/approve - 批准建议
# - POST /api/work-type-suggestions/{id}/reject - 拒绝建议
app.include_router(work_types_router.router)
app.include_router(work_types_router.suggestions_router)

# Prompt 模板管理路由（仅管理员）
# - GET /api/prompts - Prompt 列表
# - GET /api/prompts/{name} - Prompt 详情
# - PUT /api/prompts/{name} - 更新 Prompt
# - POST /api/prompts/{name}/test - 测试渲染
app.include_router(prompts_router.router)

# LLM 模型配置路由（仅管理员）
# - GET /api/llm/models - 模型列表
# - GET /api/llm/models/{model_id} - 模型详情
# - PUT /api/llm/models/{model_id} - 更新模型配置
# - POST /api/llm/models/{model_id}/test - 测试模型连接
# - GET /api/llm/models/stats/usage - 使用统计
app.include_router(llm_models.router)

# 客户管理路由（仅管理员）
# - GET/POST /api/customers - 客户 CRUD
# - GET/PUT/DELETE /api/customers/{id} - 客户详情/更新/删除
# - GET/POST /api/contacts - 联系人 CRUD
# - GET/PUT/DELETE /api/contacts/{id} - 联系人详情/更新/删除
app.include_router(customers_router.router)
app.include_router(customers_router.contacts_router)

# 供应商管理路由（仅管理员）
# - GET/POST /api/suppliers - 供应商 CRUD
# - GET/PUT/DELETE /api/suppliers/{id} - 供应商详情/更新/删除
# - GET/POST /api/supplier-contacts - 供应商联系人 CRUD
# - GET/PUT/DELETE /api/supplier-contacts/{id} - 供应商联系人详情/更新/删除
app.include_router(suppliers_router.router)
app.include_router(suppliers_router.supplier_contacts_router)

# 品类管理路由（仅管理员）
# - GET/POST /api/categories - 品类 CRUD
# - GET /api/categories/tree - 品类树形结构
# - GET/PUT/DELETE /api/categories/{id} - 品类详情/更新/删除
app.include_router(categories_router.router)

# 产品管理路由（仅管理员）
# - GET/POST /api/products - 产品 CRUD
# - GET/PUT/DELETE /api/products/{id} - 产品详情/更新/删除
# - POST /api/products/{id}/suppliers - 添加供应商关联
# - PUT/DELETE /api/products/{id}/suppliers/{supplier_id} - 更新/移除供应商关联
app.include_router(products_router.router)

# 国家数据库路由（仅管理员，只读）
# - GET /api/countries - 国家列表
# - GET /api/countries/{id} - 国家详情
app.include_router(countries_router.router)

# 贸易术语路由（仅管理员，只读）
# - GET /api/trade-terms - 贸易术语列表
# - GET /api/trade-terms/{id} - 贸易术语详情
app.include_router(trade_terms_ref_router.router)

# 付款方式路由（仅管理员，只读）
# - GET /api/payment-methods - 付款方式列表
# - GET /api/payment-methods/{id} - 付款方式详情
app.include_router(payment_methods_ref_router.router)

# 文件上传路由（仅管理员）
# - POST /api/upload - 通用文件上传
app.include_router(upload_router.router)

# 文件下载路由（公开，通过 token 验证）
# - GET /api/storage/download/{key} - 临时链接下载
app.include_router(storage_router.router)

# 仓库管理路由（仅管理员）
# - GET/POST /api/warehouses - 仓库 CRUD
# - GET/PUT/DELETE /api/warehouses/{id} - 仓库详情/更新/删除
app.include_router(warehouses_router.router)

# 库存管理路由（仅管理员，只读）
# - GET /api/inventories - 库存列表
# - GET /api/inventories/summary - 库存汇总
app.include_router(inventories_router.router)

# 采购合同管理路由（仅管理员）
# - GET/POST /api/purchase-contracts - 采购合同 CRUD
# - GET/PUT/DELETE /api/purchase-contracts/{id} - 详情/更新/删除
# - PUT /api/purchase-contracts/{id}/status - 状态变更
# - PUT /api/purchase-contracts/{id}/lines - 更新明细行
app.include_router(purchase_contracts_router.router)

# 销售合同管理路由（仅管理员）
# - GET/POST /api/sales-contracts - 销售合同 CRUD
# - GET/PUT/DELETE /api/sales-contracts/{id} - 详情/更新/删除
# - PUT /api/sales-contracts/{id}/status - 状态变更
# - PUT /api/sales-contracts/{id}/lines - 更新明细行
# - POST /api/sales-contracts/{id}/link-purchase - 绑定采购合同
app.include_router(sales_contracts_router.router)

# 入仓单管理路由（仅管理员）
# - GET/POST /api/inbound-orders - 入仓单 CRUD
# - GET/PUT/DELETE /api/inbound-orders/{id} - 详情/更新/删除
# - PUT /api/inbound-orders/{id}/status - 状态变更
# - POST /api/inbound-orders/{id}/confirm-receive - 确认收货
app.include_router(inbound_orders_router.router)

# 出仓单管理路由（仅管理员）
# - GET/POST /api/outbound-orders - 出仓单 CRUD
# - GET/PUT/DELETE /api/outbound-orders/{id} - 详情/更新/删除
# - PUT /api/outbound-orders/{id}/status - 状态变更
# - POST /api/outbound-orders/{id}/confirm-ship - 确认出仓
app.include_router(outbound_orders_router.router)

# 合同编号规则路由（仅管理员）
# - GET /api/contract-number-rules - 规则列表
# - PUT /api/contract-number-rules/{type} - 更新规则
# - POST /api/contract-number-rules/preview - 预览编号
app.include_router(contract_numbers_router.router)

# TTS 语音合成路由（仅管理员）
# - POST /api/tts/synthesize - 文本转语音
app.include_router(tts_router.router)

# 客户询价单管理路由（仅管理员）
# - GET/POST /api/client-rfqs - 客户询价单 CRUD
# - GET/PUT/DELETE /api/client-rfqs/{id} - 详情/更新/删除
# - PUT /api/client-rfqs/{id}/status - 状态变更
# - PUT /api/client-rfqs/{id}/lines - 更新明细行
app.include_router(client_rfqs_router.router)

# 报价单管理路由（仅管理员）
# - GET/POST /api/quotations - 报价单 CRUD
# - GET/PUT/DELETE /api/quotations/{id} - 详情/更新/删除
# - PUT /api/quotations/{id}/status - 状态变更
# - PUT /api/quotations/{id}/lines - 更新明细行
app.include_router(quotations_router.router)

# 供应商询价单管理路由（仅管理员）
# - GET/POST /api/supplier-rfqs - 供应商询价单 CRUD
# - GET/PUT/DELETE /api/supplier-rfqs/{id} - 详情/更新/删除
# - PUT /api/supplier-rfqs/{id}/status - 状态变更
# - PUT /api/supplier-rfqs/{id}/lines - 更新明细行
app.include_router(supplier_rfqs_router.router)

# 供应商报价单管理路由（仅管理员）
# - GET/POST /api/supplier-quotations - 供应商报价单 CRUD
# - GET/PUT/DELETE /api/supplier-quotations/{id} - 详情/更新/删除
# - PUT /api/supplier-quotations/{id}/status - 状态变更
# - PUT /api/supplier-quotations/{id}/lines - 更新明细行
app.include_router(supplier_quotations_router.router)

# 项目管理路由（仅管理员）
# - GET/POST /api/projects - 项目 CRUD
# - GET/PUT/DELETE /api/projects/{id} - 项目详情/更新/删除
# - PUT /api/projects/{id}/status - 状态变更
# - POST/DELETE /api/projects/{id}/associations - 关联管理
# - POST /api/projects/from-email/{email_id} - 从邮件预填
app.include_router(projects_router.router)

# 任务管理路由（仅管理员）
# - GET/POST /api/tasks - 任务 CRUD（列表需 project_id）
# - GET/PUT/DELETE /api/tasks/{id} - 任务详情/更新/删除
app.include_router(tasks_router.router)

# 进度记录路由（仅管理员）
# - GET/POST /api/progress - 进度 CRUD（列表需 task_id）
# - DELETE /api/progress/{id} - 删除进度
app.include_router(progress_router.router)

# 项目建议审批路由（仅管理员）
# - GET /api/project-suggestions - 建议列表
# - GET /api/project-suggestions/{id} - 建议详情
# - POST /api/project-suggestions/{id}/approve - 批准建议
# - POST /api/project-suggestions/{id}/reject - 拒绝建议
app.include_router(project_suggestions_router.router)

# 权限管理路由（只读，仅管理员）
# - GET /api/permissions - 获取所有权限（按资源分组）
app.include_router(permissions_api_router.router)

# 组织管理路由（仅超级管理员）
# - GET/POST /api/organizations - 组织 CRUD
# - GET/PUT/DELETE /api/organizations/{id} - 组织详情/更新/删除
app.include_router(organizations_router.router)

# 部门管理路由（仅管理员）
# - GET /api/departments - 部门列表（扁平）
# - GET /api/departments/tree - 部门树
# - POST /api/departments - 创建部门
# - PUT /api/departments/{id} - 更新部门
# - DELETE /api/departments/{id} - 删除部门
# - PUT /api/departments/sort - 批量更新排序
app.include_router(departments_router.router)

# 角色管理路由（仅管理员）
# - GET/POST /api/roles - 角色 CRUD
# - GET/PUT/DELETE /api/roles/{id} - 角色详情/更新/删除
# - PUT /api/roles/{id}/permissions - 批量设置权限
# - PUT /api/roles/{id}/data-scopes - 批量设置数据范围
app.include_router(roles_router.router)


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
