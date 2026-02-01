# app/workflows/activities/email.py
# 邮件相关 Activity 定义
#
# 功能说明：
# 1. 运行报价 Agent
# 2. 发送回复邮件
# 3. 更新事件状态
# 4. 生成报价单 PDF
#
# 注意：
# Activity 是无状态的函数，可以包含 I/O 操作
# 不要在 Activity 中使用全局状态或缓存

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from temporalio import activity

from app.core.logging import get_logger

logger = get_logger(__name__)


# ==================== 数据类型 ====================

@dataclass
class RunAgentRequest:
    """运行 Agent 的请求参数"""
    agent_name: str
    input_text: str
    input_data: Optional[dict] = None


@dataclass
class RunAgentResult:
    """运行 Agent 的结果"""
    success: bool
    output: str
    data: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class SendEmailRequest:
    """发送邮件的请求参数"""
    to: str
    subject: str
    body: str
    html_body: Optional[str] = None
    reply_to: Optional[str] = None
    account_id: Optional[int] = None  # 指定邮箱账户 ID
    purpose: Optional[str] = None  # 业务用途 (sales/support/notification/general)


@dataclass
class UpdateEventRequest:
    """更新事件状态的请求参数"""
    event_id: str
    status: str
    response: Optional[str] = None
    error: Optional[str] = None
    workflow_id: Optional[str] = None


# ==================== Activity 定义 ====================

@activity.defn(name="run_quote_agent")
async def run_quote_agent(request: RunAgentRequest) -> RunAgentResult:
    """
    运行报价 Agent

    调用报价 Agent 分析询价内容，生成报价。

    Args:
        request: 包含输入文本和上下文数据

    Returns:
        RunAgentResult: Agent 执行结果
    """
    info = activity.info()
    logger.info(f"[Activity] 运行报价 Agent")
    logger.info(f"  Workflow ID: {info.workflow_id}")

    try:
        # 延迟导入，避免循环依赖
        from app.agents.registry import agent_registry
        from app.llm.settings_loader import apply_llm_settings
        from app.core.database import async_session_maker

        # 从数据库加载 LLM 设置并运行 Agent
        async with async_session_maker() as session:
            await apply_llm_settings(session)

            # 运行 Agent（传递 db 参数以加载 Agent 配置）
            result = await agent_registry.run(
                "quote_agent",
                input_text=request.input_text,
                input_data=request.input_data,
                db=session,
            )

        logger.info(f"[Activity] 报价 Agent 完成: success={result.success}")

        return RunAgentResult(
            success=result.success,
            output=result.output,
            data=result.data,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"[Activity] 报价 Agent 失败: {e}")
        return RunAgentResult(
            success=False,
            output="",
            error=str(e),
        )


@activity.defn(name="run_intent_classifier")
async def run_intent_classifier(request: RunAgentRequest) -> RunAgentResult:
    """
    运行意图分类 Agent

    Args:
        request: 包含输入文本

    Returns:
        RunAgentResult: 分类结果
    """
    info = activity.info()
    logger.info(f"[Activity] 运行意图分类 Agent")
    logger.info(f"  Workflow ID: {info.workflow_id}")

    try:
        from app.agents.registry import agent_registry
        from app.llm.settings_loader import apply_llm_settings
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            await apply_llm_settings(session)

            result = await agent_registry.run(
                "intent_classifier",
                input_text=request.input_text,
                input_data=request.input_data,
                db=session,
            )

        return RunAgentResult(
            success=result.success,
            output=result.output,
            data=result.data,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"[Activity] 意图分类失败: {e}")
        return RunAgentResult(
            success=False,
            output="",
            data={"intent": "other"},
            error=str(e),
        )


@activity.defn(name="send_reply_email")
async def send_reply_email(request: SendEmailRequest) -> bool:
    """
    发送回复邮件

    根据 account_id 或 purpose 自动选择邮箱账户：
    - 优先使用 account_id 指定的账户
    - 其次根据 purpose 查找对应用途的邮箱
    - 最后使用默认邮箱

    Args:
        request: 发送邮件的参数

    Returns:
        bool: 是否发送成功
    """
    info = activity.info()
    logger.info(f"[Activity] 发送回复邮件")
    logger.info(f"  Workflow ID: {info.workflow_id}")
    logger.info(f"  收件人: {request.to}")
    logger.info(f"  主题: {request.subject}")
    if request.account_id:
        logger.info(f"  账户 ID: {request.account_id}")
    if request.purpose:
        logger.info(f"  业务用途: {request.purpose}")

    try:
        from app.storage.email import smtp_send

        message_id = await smtp_send(
            to=request.to,
            subject=request.subject,
            body=request.body,
            html_body=request.html_body,
            reply_to=request.reply_to,
            account_id=request.account_id,
            purpose=request.purpose,
        )

        logger.info(f"[Activity] 邮件发送成功: {message_id}")
        return True

    except Exception as e:
        logger.error(f"[Activity] 邮件发送失败: {e}")
        raise


@activity.defn(name="update_event_status")
async def update_event_status(request: UpdateEventRequest) -> bool:
    """
    更新事件状态

    Args:
        request: 更新请求

    Returns:
        bool: 是否更新成功
    """
    info = activity.info()
    logger.info(f"[Activity] 更新事件状态")
    logger.info(f"  Event ID: {request.event_id}")
    logger.info(f"  Status: {request.status}")

    try:
        from sqlalchemy import select
        from app.core.database import async_session_maker
        from app.models.event import Event, EventStatus

        async with async_session_maker() as session:
            stmt = select(Event).where(Event.id == request.event_id)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()

            if not event:
                logger.warning(f"[Activity] 事件不存在: {request.event_id}")
                return False

            event.status = request.status
            if request.response:
                event.response_content = request.response
            if request.error:
                event.error_message = request.error
            if request.workflow_id:
                event.workflow_id = request.workflow_id
            if request.status in (EventStatus.COMPLETED, EventStatus.FAILED):
                event.completed_at = datetime.utcnow()

            await session.commit()
            logger.info(f"[Activity] 事件状态更新成功")
            return True

    except Exception as e:
        logger.error(f"[Activity] 更新事件状态失败: {e}")
        raise


@activity.defn(name="generate_quote_pdf")
async def generate_quote_pdf(
    customer_name: str,
    items: list,
    total_price: float,
    currency: str = "CNY",
    valid_days: int = 7,
) -> dict:
    """
    生成报价单 PDF

    Args:
        customer_name: 客户名称
        items: 报价明细
        total_price: 总价
        currency: 货币
        valid_days: 有效天数

    Returns:
        dict: {"success": bool, "url": str, "quote_no": str}
    """
    info = activity.info()
    logger.info(f"[Activity] 生成报价单 PDF")
    logger.info(f"  Workflow ID: {info.workflow_id}")
    logger.info(f"  客户: {customer_name}")
    logger.info(f"  明细数: {len(items)}")

    try:
        from app.tools.registry import tool_registry

        result = await tool_registry.execute(
            "generate_quote_pdf",
            customer_name=customer_name,
            items=items,
            total_price=total_price,
            currency=currency,
            valid_days=valid_days,
        )

        logger.info(f"[Activity] PDF 生成成功: {result.get('quote_no')}")
        return result

    except Exception as e:
        logger.error(f"[Activity] PDF 生成失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }
