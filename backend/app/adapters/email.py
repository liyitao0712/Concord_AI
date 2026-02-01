# app/adapters/email.py
# 邮件适配器
#
# 功能说明：
# 1. 将 EmailMessage 转换为 UnifiedEvent
# 2. 通过 SMTP 发送回复邮件
#
# 使用方法：
#   from app.adapters.email import EmailAdapter, email_adapter
#
#   # 转换邮件为统一事件
#   event = await email_adapter.to_unified_event(email_message)
#
#   # 发送回复
#   await email_adapter.send_response(event, response, content)

from typing import Optional
from uuid import uuid4

from app.adapters.base import BaseAdapter
from app.schemas.event import UnifiedEvent, EventResponse, Attachment
from app.storage.email import EmailMessage, smtp_send
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailAdapter(BaseAdapter):
    """
    邮件适配器

    负责：
    1. 将邮件消息（EmailMessage）转换为统一事件（UnifiedEvent）
    2. 将系统响应发送回发件人（通过 SMTP）

    转换映射：
    - event_type: "email"
    - source: "email"
    - source_id: 邮件的 Message-ID
    - content: 邮件正文（优先纯文本）
    - user_external_id: 发件人邮箱
    - thread_id: 邮件的 In-Reply-To（用于识别回复链）
    - metadata: 主题、收件人、日期等
    """

    name = "email"

    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """
        将邮件数据转换为统一事件

        Args:
            raw_data: EmailMessage 对象或字典格式的邮件数据

        Returns:
            UnifiedEvent: 统一事件对象
        """
        # 支持 EmailMessage 对象或字典
        if isinstance(raw_data, EmailMessage):
            email = raw_data
        else:
            email = self._dict_to_email(raw_data)

        # 提取邮件正文（优先纯文本）
        content = email.body_text or ""
        content_type = "text"

        if not content and email.body_html:
            content = email.body_html
            content_type = "html"

        # 提取回复链 ID
        thread_id = email.headers.get("reply-to") or email.headers.get("in-reply-to")

        # 构建附件列表
        attachments = []
        for att in email.attachments:
            attachments.append(Attachment(
                name=att.get("filename", "attachment"),
                content_type=att.get("content_type", "application/octet-stream"),
                size=att.get("size", 0),
            ))

        # 生成幂等键
        idempotency_key = f"email:{email.message_id}"

        event = UnifiedEvent(
            event_id=str(uuid4()),
            event_type="email",
            source="email",
            source_id=email.message_id,
            content=content,
            content_type=content_type,
            user_external_id=email.sender,
            user_name=email.sender_name,
            thread_id=thread_id,
            attachments=attachments,
            metadata={
                "subject": email.subject,
                "recipients": email.recipients,
                "date": email.date.isoformat() if email.date else None,
                "sender_name": email.sender_name,
                "headers": email.headers,
            },
            idempotency_key=idempotency_key,
        )

        logger.info(
            f"[EmailAdapter] 转换邮件: {email.message_id} "
            f"from={email.sender} subject={email.subject[:50] if email.subject else ''}"
        )

        return event

    async def send_response(
        self,
        event: UnifiedEvent,
        response: EventResponse,
        content: Optional[str] = None,
    ) -> None:
        """
        发送回复邮件

        Args:
            event: 原始事件（包含发件人信息）
            response: 统一响应对象
            content: 回复内容（如果提供则使用此内容，否则使用 response.message）
        """
        if not event.user_external_id:
            logger.warning("[EmailAdapter] 无法发送回复：缺少发件人邮箱")
            return

        # 回复内容
        reply_content = content or response.message or ""
        if not reply_content:
            logger.warning("[EmailAdapter] 无法发送回复：内容为空")
            return

        # 构建回复主题
        original_subject = event.metadata.get("subject", "")
        if original_subject.lower().startswith("re:"):
            reply_subject = original_subject
        else:
            reply_subject = f"Re: {original_subject}"

        try:
            message_id = await smtp_send(
                to=event.user_external_id,
                subject=reply_subject,
                body=reply_content,
                reply_to=event.source_id,  # 使用原邮件 ID 作为回复引用
            )

            logger.info(
                f"[EmailAdapter] 发送回复成功: {message_id} "
                f"to={event.user_external_id}"
            )

        except Exception as e:
            logger.error(f"[EmailAdapter] 发送回复失败: {e}")
            raise

    async def validate(self, raw_data: dict) -> bool:
        """
        验证邮件数据是否有效

        Args:
            raw_data: 邮件数据

        Returns:
            bool: 是否有效
        """
        if isinstance(raw_data, EmailMessage):
            return bool(raw_data.message_id and raw_data.sender)

        return bool(
            raw_data.get("message_id") and
            raw_data.get("sender")
        )

    def get_idempotency_key(self, raw_data: dict) -> Optional[str]:
        """
        从邮件数据中提取幂等键

        Args:
            raw_data: 邮件数据

        Returns:
            str: 幂等键
        """
        if isinstance(raw_data, EmailMessage):
            return f"email:{raw_data.message_id}"

        message_id = raw_data.get("message_id")
        if message_id:
            return f"email:{message_id}"

        return None

    def _dict_to_email(self, data: dict) -> EmailMessage:
        """将字典转换为 EmailMessage 对象"""
        from datetime import datetime

        date = data.get("date")
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        elif not date:
            date = datetime.now()

        return EmailMessage(
            message_id=data.get("message_id", ""),
            subject=data.get("subject", ""),
            sender=data.get("sender", ""),
            sender_name=data.get("sender_name", ""),
            recipients=data.get("recipients", []),
            date=date,
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            attachments=data.get("attachments", []),
            headers=data.get("headers", {}),
        )


# 全局单例
email_adapter = EmailAdapter()
