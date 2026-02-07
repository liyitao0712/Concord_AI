# app/api/emails.py
# 邮件查看 API
#
# 功能说明：
# 1. 查看已接收邮件列表
# 2. 查看邮件详情
# 3. 下载原始邮件 (.eml)
# 4. 下载附件

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import get_current_admin_user, decode_token
from app.models.user import User
from app.models.email_raw import EmailRawMessage, EmailAttachment
from app.models.email_account import EmailAccount
from app.models.email_analysis import EmailAnalysis
from app.storage.email_persistence import persistence_service
from app.storage.oss import oss_client
from app.agents.email_summarizer import email_summarizer
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _get_email_body_text(email: EmailRawMessage) -> str:
    """
    获取邮件正文文本

    优先使用数据库中的 body_text，如果为空则从 OSS 下载原始邮件并解析。

    Args:
        email: 邮件记录

    Returns:
        str: 邮件正文文本
    """
    # 1. 优先使用数据库中的 body_text
    if email.body_text and email.body_text.strip():
        return email.body_text

    # 2. 如果 body_text 为空，尝试从 OSS 下载原始邮件
    if not email.oss_key:
        logger.warning(f"[EmailAPI] 邮件 {email.id} 没有 oss_key，无法获取正文")
        return ""

    try:
        # 下载原始邮件
        raw_bytes = await oss_client.download(email.oss_key)
        if not raw_bytes:
            return ""

        # 解析邮件
        import email as email_lib
        from email.policy import default as email_policy

        msg = email_lib.message_from_bytes(raw_bytes, policy=email_policy)

        # 提取正文
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body_text = part.get_content()
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        body_html = part.get_content()
                    except Exception:
                        pass
        else:
            try:
                body_text = msg.get_content()
            except Exception:
                pass

        # 优先返回纯文本，否则从 HTML 提取
        if body_text and body_text.strip():
            return body_text

        if body_html:
            # 简单去除 HTML 标签
            import re
            text = re.sub(r'<style[^>]*>.*?</style>', '', body_html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        return ""

    except Exception as e:
        logger.error(f"[EmailAPI] 从 OSS 获取邮件正文失败: {email.id}, {e}")
        return ""

router = APIRouter(prefix="/admin/emails", tags=["邮件记录"])


# ==================== 下载认证辅助函数 ====================

async def get_admin_from_token_or_query(
    token: Optional[str] = Query(None, description="认证 Token（用于下载）"),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    从查询参数获取 token 并验证管理员身份

    用于下载端点，支持通过 URL 参数传递 token
    """
    if not token:
        raise HTTPException(status_code=401, detail="需要认证")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 无效")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效")

    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户无效")

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user


# ==================== Schema ====================

class AttachmentItem(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    is_inline: bool
    is_signature: bool

    class Config:
        from_attributes = True


class EmailListItem(BaseModel):
    id: str
    sender: str
    sender_name: Optional[str]
    subject: str
    received_at: datetime
    is_processed: bool
    attachment_count: int
    email_account_name: Optional[str]

    class Config:
        from_attributes = True


class EmailDetail(BaseModel):
    id: str
    sender: str
    sender_name: Optional[str]
    subject: str
    recipients: List[str]
    body_text: str  # 邮件正文
    received_at: datetime
    is_processed: bool
    processed_at: Optional[datetime]
    event_id: Optional[str]
    size_bytes: int
    oss_key: str
    email_account_id: Optional[int]
    email_account_name: Optional[str]
    attachments: List[AttachmentItem]

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EmailListItem]


# ==================== API Endpoints ====================

@router.get("", response_model=EmailListResponse)
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account_id: Optional[int] = None,
    is_processed: Optional[bool] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取邮件列表

    - **page**: 页码
    - **page_size**: 每页数量
    - **account_id**: 按邮箱账户筛选
    - **is_processed**: 按处理状态筛选
    - **search**: 按发件人/主题搜索
    """
    # 构建查询
    query = select(EmailRawMessage).options(
        selectinload(EmailRawMessage.attachments)
    )

    # 筛选条件
    if account_id is not None:
        query = query.where(EmailRawMessage.email_account_id == account_id)
    if is_processed is not None:
        query = query.where(EmailRawMessage.is_processed == is_processed)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (EmailRawMessage.sender.ilike(search_pattern)) |
            (EmailRawMessage.sender_name.ilike(search_pattern)) |
            (EmailRawMessage.subject.ilike(search_pattern))
        )

    # 统计总数
    count_query = select(func.count(EmailRawMessage.id))
    if account_id is not None:
        count_query = count_query.where(EmailRawMessage.email_account_id == account_id)
    if is_processed is not None:
        count_query = count_query.where(EmailRawMessage.is_processed == is_processed)
    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            (EmailRawMessage.sender.ilike(search_pattern)) |
            (EmailRawMessage.sender_name.ilike(search_pattern)) |
            (EmailRawMessage.subject.ilike(search_pattern))
        )

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(EmailRawMessage.received_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    emails = result.scalars().all()

    # 获取邮箱账户名称
    account_ids = [e.email_account_id for e in emails if e.email_account_id]
    account_names = {}
    if account_ids:
        acc_query = select(EmailAccount.id, EmailAccount.name).where(
            EmailAccount.id.in_(account_ids)
        )
        acc_result = await session.execute(acc_query)
        account_names = {row[0]: row[1] for row in acc_result.all()}

    # 构建响应
    items = []
    for email in emails:
        # 计算附件数（排除签名图片）
        attachment_count = sum(
            1 for att in email.attachments if not att.is_signature
        )
        items.append(EmailListItem(
            id=email.id,
            sender=email.sender,
            sender_name=email.sender_name,
            subject=email.subject,
            received_at=email.received_at,
            is_processed=email.is_processed,
            attachment_count=attachment_count,
            email_account_name=account_names.get(email.email_account_id),
        ))

    return EmailListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{email_id}", response_model=EmailDetail)
async def get_email_detail(
    email_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取邮件详情
    """
    query = select(EmailRawMessage).where(
        EmailRawMessage.id == email_id
    ).options(selectinload(EmailRawMessage.attachments))

    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 获取邮箱账户名称
    account_name = None
    if email.email_account_id:
        acc_query = select(EmailAccount.name).where(
            EmailAccount.id == email.email_account_id
        )
        acc_result = await session.execute(acc_query)
        account_name = acc_result.scalar_one_or_none()

    # 构建附件列表（排除签名图片）
    attachments = [
        AttachmentItem(
            id=att.id,
            filename=att.filename,
            content_type=att.content_type,
            size_bytes=att.size_bytes,
            is_inline=att.is_inline,
            is_signature=att.is_signature,
        )
        for att in email.attachments
        if not att.is_signature
    ]

    # 获取邮件正文
    body_text = await _get_email_body_text(email)

    return EmailDetail(
        id=email.id,
        sender=email.sender,
        sender_name=email.sender_name,
        subject=email.subject,
        recipients=email.get_recipients(),
        body_text=body_text,
        received_at=email.received_at,
        is_processed=email.is_processed,
        processed_at=email.processed_at,
        event_id=email.event_id,
        size_bytes=email.size_bytes,
        oss_key=email.oss_key,
        email_account_id=email.email_account_id,
        email_account_name=account_name,
        attachments=attachments,
    )


@router.get("/{email_id}/raw")
async def download_raw_email(
    email_id: str,
    token: Optional[str] = Query(None, description="认证 Token"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    下载原始邮件 (.eml)

    返回 302 重定向到签名 URL

    注意：此端点支持通过 URL 参数传递 token，以便浏览器直接下载
    """
    # 验证管理员权限
    await get_admin_from_token_or_query(token, session)

    # 验证邮件存在
    query = select(EmailRawMessage.id).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 获取签名 URL
    url = await persistence_service.get_raw_email_url(email_id)
    if not url:
        raise HTTPException(status_code=404, detail="原始邮件文件不存在")

    return RedirectResponse(url=url)


@router.get("/{email_id}/attachments/{attachment_id}")
async def download_attachment(
    email_id: str,
    attachment_id: str,
    token: Optional[str] = Query(None, description="认证 Token"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    下载附件

    返回 302 重定向到签名 URL

    注意：此端点支持通过 URL 参数传递 token，以便浏览器直接下载
    """
    # 验证管理员权限
    await get_admin_from_token_or_query(token, session)

    # 验证附件存在且属于该邮件
    query = select(EmailAttachment).where(
        EmailAttachment.id == attachment_id,
        EmailAttachment.email_id == email_id,
    )
    result = await session.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 获取签名 URL
    url = await persistence_service.get_attachment_url(attachment_id)
    if not url:
        raise HTTPException(status_code=404, detail="附件文件不存在")

    return RedirectResponse(url=url)


# ==================== 路由分析 ====================

class RouteAnalyzeResponse(BaseModel):
    """路由分析结果"""
    intent: str
    intent_label: str
    confidence: float
    reasoning: str
    action: str
    handler_config: dict
    workflow_name: Optional[str]
    needs_escalation: bool
    escalation_reason: Optional[str]
    new_suggestion: Optional[dict]


class RouteExecuteRequest(BaseModel):
    """执行请求"""
    intent: Optional[str] = None  # 如果指定，覆盖分析结果
    force: bool = False  # 强制执行（即使已处理过）


class RouteExecuteResponse(BaseModel):
    """执行结果"""
    success: bool
    message: str
    intent: str
    action: str
    workflow_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/{email_id}/analyze", response_model=RouteAnalyzeResponse)
async def analyze_email(
    email_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    分析邮件意图

    使用 RouterAgent 分析邮件，返回分类结果。
    不会执行任何操作，只是展示分析结果。
    """
    from app.agents.router_agent import router_agent
    from app.schemas.event import UnifiedEvent
    from uuid import uuid4

    # 获取邮件
    query = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 构建 UnifiedEvent
    event = UnifiedEvent(
        event_id=str(uuid4()),
        event_type="email",
        source="email",
        source_id=email.message_id,
        content=email.body_text or email.subject or "(无内容)",  # 优先用正文，其次用主题
        user_external_id=email.sender,
        user_name=email.sender_name,
        metadata={
            "subject": email.subject,
            "recipients": email.get_recipients(),
            "email_raw_id": email.id,
            "email_account_id": email.email_account_id,
        },
    )

    # 调用 RouterAgent
    route_result = await router_agent.route(event, session)

    return RouteAnalyzeResponse(
        intent=route_result.intent,
        intent_label=route_result.intent_label,
        confidence=route_result.confidence,
        reasoning=route_result.reasoning,
        action=route_result.action,
        handler_config=route_result.handler_config,
        workflow_name=route_result.workflow_name,
        needs_escalation=route_result.needs_escalation,
        escalation_reason=route_result.escalation_reason,
        new_suggestion=(
            {
                "name": route_result.new_suggestion.name,
                "label": route_result.new_suggestion.label,
                "description": route_result.new_suggestion.description,
                "suggested_handler": route_result.new_suggestion.suggested_handler,
            }
            if route_result.new_suggestion
            else None
        ),
    )


@router.post("/{email_id}/execute", response_model=RouteExecuteResponse)
async def execute_email_route(
    email_id: str,
    data: RouteExecuteRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    执行邮件路由

    调用 RouterAgent 分析并执行相应处理。

    - force=true 时，即使邮件已处理过也会重新执行
    """
    from app.agents.router_agent import router_agent
    from app.schemas.event import UnifiedEvent
    from datetime import datetime
    from uuid import uuid4

    # 获取邮件
    query = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 检查是否已处理
    if email.is_processed and not data.force:
        raise HTTPException(
            status_code=400,
            detail="邮件已处理，使用 force=true 强制重新执行",
        )

    # 构建 UnifiedEvent
    event = UnifiedEvent(
        event_id=str(uuid4()),
        event_type="email",
        source="email",
        source_id=email.message_id,
        content=email.body_text or email.subject or "(无内容)",
        user_external_id=email.sender,
        user_name=email.sender_name,
        metadata={
            "subject": email.subject,
            "recipients": email.get_recipients(),
            "email_raw_id": email.id,
            "email_account_id": email.email_account_id,
        },
    )

    # 调用 RouterAgent 分析
    route_result = await router_agent.route(event, session)

    # TODO: 实际执行逻辑
    # 目前只是标记为已处理，后续实现实际的 Agent/Workflow 调用

    # 更新邮件状态
    email.is_processed = True
    email.processed_at = datetime.utcnow()
    email.event_id = event.event_id

    await session.commit()

    return RouteExecuteResponse(
        success=True,
        message=f"已处理，意图: {route_result.intent}",
        intent=route_result.intent,
        action=route_result.action,
        workflow_id=None,  # TODO: 返回实际的 workflow_id
    )


# ==================== AI 邮件分析 ====================

class EmailAnalysisResponse(BaseModel):
    """邮件分析结果"""
    id: str
    email_id: str
    summary: str
    key_points: Optional[List[str]] = None
    original_language: Optional[str] = None

    # 发件方
    sender_type: Optional[str] = None
    sender_company: Optional[str] = None
    sender_country: Optional[str] = None
    is_new_contact: Optional[bool] = None

    # 意图
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    urgency: Optional[str] = None
    sentiment: Optional[str] = None

    # 业务
    products: Optional[List[dict]] = None
    amounts: Optional[List[dict]] = None
    trade_terms: Optional[dict] = None
    deadline: Optional[str] = None

    # 跟进
    questions: Optional[List[str]] = None
    action_required: Optional[List[str]] = None
    suggested_reply: Optional[str] = None
    priority: Optional[str] = None

    # 元数据
    llm_model: Optional[str] = None
    token_used: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/{email_id}/ai-analyze", response_model=EmailAnalysisResponse)
async def ai_analyze_email(
    email_id: str,
    force: bool = Query(False, description="强制重新分析"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    AI 分析邮件

    使用 EmailSummarizerAgent 分析邮件内容，提取：
    - 摘要和关键要点
    - 发件方身份（客户/供应商）
    - 意图分类
    - 产品、金额、贸易条款等业务信息
    - 处理建议

    分析结果会保存到数据库，下次查询可直接返回。
    使用 force=true 强制重新分析。
    """
    # 获取邮件
    query = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 检查是否已有分析结果
    if not force:
        analysis_query = select(EmailAnalysis).where(
            EmailAnalysis.email_id == email_id
        ).order_by(EmailAnalysis.created_at.desc()).limit(1)
        analysis_result = await session.execute(analysis_query)
        existing = analysis_result.scalars().first()

        if existing:
            return EmailAnalysisResponse(
                id=existing.id,
                email_id=existing.email_id,
                summary=existing.summary,
                key_points=existing.key_points,
                original_language=existing.original_language,
                sender_type=existing.sender_type,
                sender_company=existing.sender_company,
                sender_country=existing.sender_country,
                is_new_contact=existing.is_new_contact,
                intent=existing.intent,
                intent_confidence=existing.intent_confidence,
                urgency=existing.urgency,
                sentiment=existing.sentiment,
                products=existing.products,
                amounts=existing.amounts,
                trade_terms=existing.trade_terms,
                deadline=existing.deadline.isoformat() if existing.deadline else None,
                questions=existing.questions,
                action_required=existing.action_required,
                suggested_reply=existing.suggested_reply,
                priority=existing.priority,
                llm_model=existing.llm_model,
                token_used=existing.token_used,
                created_at=existing.created_at.isoformat() if existing.created_at else None,
            )

    # 获取邮件正文（优先数据库，否则从 OSS 下载）
    body_text = await _get_email_body_text(email)
    if not body_text or not body_text.strip():
        # 提供详细的诊断信息
        has_body_text = bool(email.body_text and email.body_text.strip())
        has_oss_key = bool(email.oss_key and email.oss_key.strip())

        detail_parts = ["邮件正文为空，无法进行 AI 分析"]
        if not has_body_text and not has_oss_key:
            detail_parts.append("原因：数据库中没有保存正文，且没有 OSS 文件")
            detail_parts.append("建议：检查邮件接收系统是否正常工作")
        elif not has_body_text and has_oss_key:
            detail_parts.append("原因：数据库中没有正文，但 OSS 下载失败")
        else:
            detail_parts.append("原因：邮件可能是纯 HTML 或附件类型")

        raise HTTPException(
            status_code=400,
            detail="。".join(detail_parts)
        )

    # 调用 AI 分析
    try:
        analysis_result = await email_summarizer.analyze(
            email_id=email.id,
            sender=email.sender,
            sender_name=email.sender_name,
            subject=email.subject,
            body_text=body_text,
            received_at=email.received_at,
        )
    except ValueError as e:
        # API Key 未配置或其他配置错误
        error_msg = str(e)
        # 如果是 LLM 配置缺失，返回更友好的错误信息
        if "未找到可用的 LLM 模型配置" in error_msg or "API Key 未配置" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="LLM 模型未配置。请前往「管理后台 → LLM 配置」页面添加至少一个模型配置并设置 API Key。"
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        # 记录详细错误日志
        logger.error(f"[EmailAPI] AI 分析失败: {email_id}, {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[EmailAPI] 错误堆栈: {traceback.format_exc()}")

        # 返回用户友好的错误信息
        raise HTTPException(
            status_code=500,
            detail=f"AI 分析失败，请稍后重试或联系管理员。错误详情: {str(e)}"
        )

    # 解析 deadline
    deadline_dt = None
    if analysis_result.get("deadline"):
        try:
            from datetime import datetime
            deadline_dt = datetime.fromisoformat(analysis_result["deadline"])
        except (ValueError, TypeError):
            pass

    # 保存到数据库
    from uuid import uuid4
    analysis = EmailAnalysis(
        id=str(uuid4()),
        email_id=email_id,
        summary=analysis_result.get("summary", ""),
        key_points=analysis_result.get("key_points"),
        original_language=analysis_result.get("original_language"),
        sender_type=analysis_result.get("sender_type"),
        sender_company=analysis_result.get("sender_company"),
        sender_country=analysis_result.get("sender_country"),
        is_new_contact=analysis_result.get("is_new_contact"),
        intent=analysis_result.get("intent"),
        intent_confidence=analysis_result.get("intent_confidence"),
        urgency=analysis_result.get("urgency"),
        sentiment=analysis_result.get("sentiment"),
        products=analysis_result.get("products"),
        amounts=analysis_result.get("amounts"),
        trade_terms=analysis_result.get("trade_terms"),
        deadline=deadline_dt,
        questions=analysis_result.get("questions"),
        action_required=analysis_result.get("action_required"),
        suggested_reply=analysis_result.get("suggested_reply"),
        priority=analysis_result.get("priority"),
        cleaned_content=analysis_result.get("cleaned_content"),
        llm_model=analysis_result.get("llm_model"),
        token_used=analysis_result.get("token_used"),
    )

    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)

    return EmailAnalysisResponse(
        id=analysis.id,
        email_id=analysis.email_id,
        summary=analysis.summary,
        key_points=analysis.key_points,
        original_language=analysis.original_language,
        sender_type=analysis.sender_type,
        sender_company=analysis.sender_company,
        sender_country=analysis.sender_country,
        is_new_contact=analysis.is_new_contact,
        intent=analysis.intent,
        intent_confidence=analysis.intent_confidence,
        urgency=analysis.urgency,
        sentiment=analysis.sentiment,
        products=analysis.products,
        amounts=analysis.amounts,
        trade_terms=analysis.trade_terms,
        deadline=analysis.deadline.isoformat() if analysis.deadline else None,
        questions=analysis.questions,
        action_required=analysis.action_required,
        suggested_reply=analysis.suggested_reply,
        priority=analysis.priority,
        llm_model=analysis.llm_model,
        token_used=analysis.token_used,
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


@router.get("/{email_id}/analysis", response_model=Optional[EmailAnalysisResponse])
async def get_email_analysis(
    email_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取邮件分析结果

    返回已保存的分析结果，如果没有则返回 null。
    """
    query = select(EmailAnalysis).where(
        EmailAnalysis.email_id == email_id
    ).order_by(EmailAnalysis.created_at.desc()).limit(1)

    result = await session.execute(query)
    analysis = result.scalars().first()

    if not analysis:
        return None

    return EmailAnalysisResponse(
        id=analysis.id,
        email_id=analysis.email_id,
        summary=analysis.summary,
        key_points=analysis.key_points,
        original_language=analysis.original_language,
        sender_type=analysis.sender_type,
        sender_company=analysis.sender_company,
        sender_country=analysis.sender_country,
        is_new_contact=analysis.is_new_contact,
        intent=analysis.intent,
        intent_confidence=analysis.intent_confidence,
        urgency=analysis.urgency,
        sentiment=analysis.sentiment,
        products=analysis.products,
        amounts=analysis.amounts,
        trade_terms=analysis.trade_terms,
        deadline=analysis.deadline.isoformat() if analysis.deadline else None,
        questions=analysis.questions,
        action_required=analysis.action_required,
        suggested_reply=analysis.suggested_reply,
        priority=analysis.priority,
        llm_model=analysis.llm_model,
        token_used=analysis.token_used,
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


# ==================== 工作类型分析 ====================

class WorkTypeAnalyzeResponse(BaseModel):
    """工作类型分析结果"""
    email_id: str
    matched_work_type: Optional[dict] = None  # {code, confidence, reason}
    new_suggestion: Optional[dict] = None  # {should_suggest, suggested_code, ...}
    suggestion_id: Optional[str] = None  # 如果创建了建议，返回建议 ID
    llm_model: Optional[str] = None


@router.post("/{email_id}/work-type-analyze", response_model=WorkTypeAnalyzeResponse)
async def analyze_email_work_type(
    email_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    分析邮件工作类型

    使用 WorkTypeAnalyzer Agent 分析邮件内容，判断工作类型：
    - 匹配现有工作类型
    - 识别并建议新的工作类型（置信度 >= 0.6 时）
    - 如果建议新类型，自动创建 WorkTypeSuggestion 并启动 Temporal 审批流程

    注意：此功能需要手动触发，不会在邮件接收时自动执行。
    """
    from app.agents.work_type_analyzer import work_type_analyzer

    # 获取邮件
    query = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 获取邮件正文
    body_text = await _get_email_body_text(email)
    if not body_text or not body_text.strip():
        raise HTTPException(
            status_code=400,
            detail="邮件正文为空，无法进行工作类型分析"
        )

    # 调用 WorkTypeAnalyzer
    try:
        analysis_result = await work_type_analyzer.analyze(
            email_id=email.id,
            sender=email.sender,
            subject=email.subject,
            content=body_text,
            received_at=email.received_at,
            session=session,
        )

        # 如果建议新类型，创建 suggestion
        suggestion_id = None
        if analysis_result.get("new_suggestion", {}).get("should_suggest"):
            suggestion_id = await work_type_analyzer.create_suggestion_if_needed(
                result=analysis_result,
                email_id=email.id,
                trigger_content=f"主题: {email.subject}\n\n{body_text[:200]}",
                session=session,
            )

        return WorkTypeAnalyzeResponse(
            email_id=email.id,
            matched_work_type=analysis_result.get("matched_work_type"),
            new_suggestion=analysis_result.get("new_suggestion"),
            suggestion_id=suggestion_id,
            llm_model=analysis_result.get("llm_model"),
        )

    except ValueError as e:
        error_msg = str(e)
        if "未找到可用的 LLM 模型配置" in error_msg or "API Key 未配置" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="LLM 模型未配置。请前往「管理后台 → LLM 配置」页面添加模型配置。"
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"[EmailAPI] 工作类型分析失败: {email_id}, {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"工作类型分析失败: {str(e)}"
        )


# ==================== 客户提取 ====================

class CustomerExtractResponse(BaseModel):
    """客户提取结果"""
    email_id: str
    skip_extraction: bool = False
    skip_reason: Optional[str] = None
    is_new_customer: Optional[bool] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    company: Optional[dict] = None
    contact: Optional[dict] = None
    suggested_tags: Optional[List[str]] = None
    matched_existing_customer: Optional[str] = None
    sender_type: Optional[str] = None
    suggestion_id: Optional[str] = None
    llm_model: Optional[str] = None


@router.post("/{email_id}/customer-extract", response_model=CustomerExtractResponse)
async def extract_customer_from_email(
    email_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    从邮件中提取客户信息

    使用 CustomerExtractorAgent 分析邮件，提取客户和联系人信息。
    如果检测到新客户/新联系人，自动创建 CustomerSuggestion 并启动 Temporal 审批流程。

    注意：此功能会复用已有的 EmailAnalysis 结果，如果没有会先提示用户执行 AI 分析。
    """
    from app.agents.customer_extractor import customer_extractor

    # 获取邮件
    query = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
    result = await session.execute(query)
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # 获取邮件正文
    body_text = await _get_email_body_text(email)
    if not body_text or not body_text.strip():
        raise HTTPException(
            status_code=400,
            detail="邮件正文为空，无法进行客户提取"
        )

    # 获取已有的 EmailAnalysis（复用 EmailSummarizer 分析结果）
    email_analysis_data = None
    analysis_query = select(EmailAnalysis).where(
        EmailAnalysis.email_id == email_id
    ).order_by(EmailAnalysis.created_at.desc()).limit(1)
    analysis_result = await session.execute(analysis_query)
    existing_analysis = analysis_result.scalars().first()

    if existing_analysis:
        email_analysis_data = {
            "sender_company": existing_analysis.sender_company,
            "sender_country": existing_analysis.sender_country,
            "sender_type": existing_analysis.sender_type,
            "is_new_contact": existing_analysis.is_new_contact,
            "intent": existing_analysis.intent,
            "products": existing_analysis.products,
        }

    # 调用 CustomerExtractorAgent
    try:
        extract_result = await customer_extractor.analyze(
            email_id=email.id,
            sender=email.sender,
            sender_name=email.sender_name,
            subject=email.subject,
            content=body_text,
            email_analysis=email_analysis_data,
            session=session,
        )

        return CustomerExtractResponse(
            email_id=email.id,
            skip_extraction=extract_result.get("skip_extraction", False),
            skip_reason=extract_result.get("skip_reason"),
            is_new_customer=extract_result.get("is_new_customer"),
            confidence=extract_result.get("confidence"),
            reasoning=extract_result.get("reasoning"),
            company=extract_result.get("company"),
            contact=extract_result.get("contact"),
            suggested_tags=extract_result.get("suggested_tags"),
            matched_existing_customer=extract_result.get("matched_existing_customer"),
            sender_type=extract_result.get("sender_type"),
            suggestion_id=extract_result.get("suggestion_id"),
            llm_model=extract_result.get("llm_model"),
        )

    except ValueError as e:
        error_msg = str(e)
        if "未找到可用的 LLM 模型配置" in error_msg or "API Key 未配置" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="LLM 模型未配置。请前往「管理后台 → LLM 配置」页面添加模型配置。"
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"[EmailAPI] 客户提取失败: {email_id}, {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"客户提取失败: {str(e)}"
        )
