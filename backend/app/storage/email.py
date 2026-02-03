# app/storage/email.py
# 邮件收发底层实现
#
# 功能说明：
# 1. IMAP - 接收邮件（拉取收件箱）
# 2. SMTP - 发送邮件
# 3. 支持多邮箱账户（从数据库读取配置）
#
# 这是底层实现，被以下模块调用：
# - tools/email.py - Agent 的邮件工具
# - workers/email_worker.py - 邮件 Worker（定时轮询）
#
# 使用异步库：
# - aioimaplib - 异步 IMAP
# - aiosmtplib - 异步 SMTP

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from email.utils import parseaddr, formatdate
from typing import Optional, Union, List
import uuid

import aiosmtplib
from aioimaplib import aioimaplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ==================== 数据类型 ====================

@dataclass
class EmailAccountConfig:
    """邮箱账户配置（统一接口，来源可以是数据库或环境变量）"""
    id: Optional[int]
    name: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool
    imap_host: Optional[str]
    imap_port: int
    imap_user: Optional[str]
    imap_password: Optional[str]
    imap_use_ssl: bool
    imap_folder: str = "INBOX"           # 监控的邮件文件夹
    imap_mark_as_read: bool = False      # 拉取后是否标记已读
    imap_sync_days: Optional[int] = None # 同步多少天的历史邮件（None=全部）
    imap_unseen_only: bool = False       # 是否只同步未读邮件
    imap_fetch_limit: int = 50           # 每次拉取的最大邮件数

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def imap_configured(self) -> bool:
        return bool(self.imap_host and self.imap_user and self.imap_password)


class EmailMessage:
    """邮件消息数据类"""

    def __init__(
        self,
        message_id: str,
        subject: str,
        sender: str,
        sender_name: str,
        recipients: list[str],
        date: datetime,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[list[dict]] = None,
        headers: Optional[dict] = None,
        raw_bytes: Optional[bytes] = None,
    ):
        self.message_id = message_id
        self.subject = subject
        self.sender = sender
        self.sender_name = sender_name
        self.recipients = recipients
        self.date = date
        self.body_text = body_text
        self.body_html = body_html
        self.attachments = attachments or []
        self.headers = headers or {}
        self.raw_bytes = raw_bytes  # 原始邮件内容（RFC822 格式）

    def to_dict(self, include_raw_bytes: bool = False) -> dict:
        """
        转换为字典（用于 Celery 任务序列化）

        Args:
            include_raw_bytes: 是否包含原始邮件字节（默认 False 以优化传输）

        注意：raw_bytes 默认不包含（太大），但持久化时需要包含
        """
        data = {
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "recipients": self.recipients,
            "date": self.date.isoformat() if self.date else None,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": self.attachments,
            "headers": self.headers,
        }

        # 可选包含 raw_bytes（用于持久化）
        if include_raw_bytes and self.raw_bytes:
            import base64
            data["raw_bytes"] = base64.b64encode(self.raw_bytes).decode('utf-8')

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "EmailMessage":
        """从字典创建 EmailMessage 实例"""
        from datetime import datetime

        date_str = data.get("date")
        date = datetime.fromisoformat(date_str) if date_str else None

        # 解码 raw_bytes（如果存在）
        raw_bytes = None
        if "raw_bytes" in data and data["raw_bytes"]:
            import base64
            raw_bytes = base64.b64decode(data["raw_bytes"])

        return cls(
            message_id=data["message_id"],
            subject=data.get("subject", ""),
            sender=data["sender"],
            sender_name=data.get("sender_name", ""),
            recipients=data.get("recipients", []),
            date=date,
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            attachments=data.get("attachments", []),
            headers=data.get("headers", {}),
            raw_bytes=raw_bytes,  # 从 base64 解码（如果提供）
        )


# ==================== 账户获取 ====================

async def get_email_account(
    account_id: Optional[int] = None,
    purpose: Optional[str] = None,
) -> EmailAccountConfig:
    """
    获取邮箱账户配置

    优先级：
    1. 指定 account_id → 从数据库获取
    2. 指定 purpose → 从数据库获取该用途的账户
    3. 查找默认账户（is_default=True）
    4. 回退到环境变量配置

    Args:
        account_id: 邮箱账户 ID
        purpose: 业务用途 (sales/support/notification/general)

    Returns:
        EmailAccountConfig: 邮箱配置
    """
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.email_account import EmailAccount

    async with async_session_maker() as session:
        account = None

        # 1. 指定 ID
        if account_id:
            stmt = select(EmailAccount).where(
                EmailAccount.id == account_id,
                EmailAccount.is_active == True,
            )
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()

        # 2. 指定用途
        if not account and purpose:
            stmt = select(EmailAccount).where(
                EmailAccount.purpose == purpose,
                EmailAccount.is_active == True,
            )
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()

        # 3. 默认账户
        if not account:
            stmt = select(EmailAccount).where(
                EmailAccount.is_default == True,
                EmailAccount.is_active == True,
            )
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()

        # 4. 数据库有账户，转换为配置对象
        if account:
            return EmailAccountConfig(
                id=account.id,
                name=account.name,
                smtp_host=account.smtp_host,
                smtp_port=account.smtp_port,
                smtp_user=account.smtp_user,
                smtp_password=account.smtp_password,
                smtp_use_tls=account.smtp_use_tls,
                imap_host=account.imap_host,
                imap_port=account.imap_port,
                imap_user=account.imap_user,
                imap_password=account.imap_password,
                imap_use_ssl=account.imap_use_ssl,
                imap_folder=account.imap_folder,
                imap_mark_as_read=account.imap_mark_as_read,
                imap_sync_days=account.imap_sync_days,
                imap_unseen_only=account.imap_unseen_only,
                imap_fetch_limit=account.imap_fetch_limit,
            )

    # 5. 回退到环境变量
    return _get_account_from_env()


def _get_account_from_env() -> EmailAccountConfig:
    """从环境变量获取邮箱配置（向后兼容）"""
    return EmailAccountConfig(
        id=None,
        name="环境变量配置",
        smtp_host=getattr(settings, "SMTP_HOST", "") or "",
        smtp_port=getattr(settings, "SMTP_PORT", 465) or 465,
        smtp_user=getattr(settings, "SMTP_USER", "") or "",
        smtp_password=getattr(settings, "SMTP_PASSWORD", "") or "",
        smtp_use_tls=getattr(settings, "SMTP_USE_TLS", True),
        imap_host=getattr(settings, "IMAP_HOST", None),
        imap_port=getattr(settings, "IMAP_PORT", 993) or 993,
        imap_user=getattr(settings, "IMAP_USER", None),
        imap_password=getattr(settings, "IMAP_PASSWORD", None),
        imap_use_ssl=getattr(settings, "IMAP_USE_SSL", True),
    )


async def get_active_imap_accounts() -> List[EmailAccountConfig]:
    """
    获取所有启用了 IMAP 的邮箱账户

    Returns:
        List[EmailAccountConfig]: 邮箱配置列表
    """
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.email_account import EmailAccount

    accounts = []

    async with async_session_maker() as session:
        stmt = select(EmailAccount).where(
            EmailAccount.is_active == True,
            EmailAccount.imap_host.isnot(None),
            EmailAccount.imap_host != "",
        )
        result = await session.execute(stmt)
        db_accounts = result.scalars().all()

        for account in db_accounts:
            if account.imap_configured:
                accounts.append(EmailAccountConfig(
                    id=account.id,
                    name=account.name,
                    smtp_host=account.smtp_host,
                    smtp_port=account.smtp_port,
                    smtp_user=account.smtp_user,
                    smtp_password=account.smtp_password,
                    smtp_use_tls=account.smtp_use_tls,
                    imap_host=account.imap_host,
                    imap_port=account.imap_port,
                    imap_user=account.imap_user,
                    imap_password=account.imap_password,
                    imap_use_ssl=account.imap_use_ssl,
                    imap_folder=account.imap_folder,
                    imap_mark_as_read=account.imap_mark_as_read,
                    imap_sync_days=account.imap_sync_days,
                    imap_unseen_only=account.imap_unseen_only,
                    imap_fetch_limit=account.imap_fetch_limit,
                ))

    # 如果数据库没有配置，回退到环境变量
    if not accounts:
        env_account = _get_account_from_env()
        if env_account.imap_configured:
            accounts.append(env_account)

    return accounts


# ==================== SMTP 发送邮件 ====================

async def smtp_send(
    to: Union[str, List[str]],
    subject: str,
    body: str,
    *,
    html_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[dict]] = None,
    reply_to: Optional[str] = None,
    account_id: Optional[int] = None,
    purpose: Optional[str] = None,
) -> str:
    """
    发送邮件

    Args:
        to: 收件人（单个或多个）
        subject: 邮件主题
        body: 纯文本正文
        html_body: HTML 正文（可选）
        cc: 抄送（可选）
        bcc: 密送（可选）
        attachments: 附件列表 [{"filename": "...", "content": bytes, "mime_type": "..."}]
        reply_to: 回复地址（可选）
        account_id: 邮箱账户 ID（可选，不指定则使用默认）
        purpose: 业务用途（可选，用于自动选择邮箱）

    Returns:
        str: 邮件 Message-ID

    Raises:
        Exception: 发送失败
    """
    # 获取邮箱配置
    account = await get_email_account(account_id=account_id, purpose=purpose)

    if not account.smtp_configured:
        raise ValueError(f"邮箱 {account.name} 未配置 SMTP")

    # 确保 to 是列表
    if isinstance(to, str):
        to = [to]

    # 生成 Message-ID
    message_id = f"<{uuid.uuid4()}@{account.smtp_host}>"

    logger.info(f"[SMTP] 发送邮件: {subject}")
    logger.info(f"[SMTP]   账户: {account.name} ({account.smtp_user})")
    logger.info(f"[SMTP]   收件人: {to}")

    try:
        # 创建邮件
        if html_body or attachments:
            msg = MIMEMultipart("alternative" if html_body and not attachments else "mixed")
        else:
            msg = MIMEText(body, "plain", "utf-8")

        # 设置邮件头
        msg["From"] = account.smtp_user
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = message_id

        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        # 添加正文
        if isinstance(msg, MIMEMultipart):
            # 添加纯文本部分
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # 添加 HTML 部分
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)

            # 添加附件
            if attachments:
                for att in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(att["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={att['filename']}",
                    )
                    msg.attach(part)

        # 收集所有收件人
        all_recipients = to.copy()
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        # 发送邮件
        await aiosmtplib.send(
            msg,
            hostname=account.smtp_host,
            port=account.smtp_port,
            username=account.smtp_user,
            password=account.smtp_password,
            use_tls=account.smtp_use_tls,
            start_tls=not account.smtp_use_tls,
        )

        logger.info(f"[SMTP] 发送成功: {message_id}")
        return message_id

    except Exception as e:
        logger.error(f"[SMTP] 发送失败: {e}")
        raise


# ==================== IMAP 接收邮件 ====================

async def imap_fetch(
    folder: str = "INBOX",
    limit: int = 10,
    since: Optional[datetime] = None,
    unseen_only: bool = False,
    account_id: Optional[int] = None,
    purpose: Optional[str] = None,
) -> list[EmailMessage]:
    """
    拉取邮件

    Args:
        folder: 邮件文件夹（默认收件箱）
        limit: 最大返回数量
        since: 只获取此时间之后的邮件
        unseen_only: 只获取未读邮件
        account_id: 邮箱账户 ID（可选）
        purpose: 业务用途（可选）

    Returns:
        list[EmailMessage]: 邮件列表

    Raises:
        Exception: 拉取失败
    """
    # 获取邮箱配置
    account = await get_email_account(account_id=account_id, purpose=purpose)

    if not account.imap_configured:
        raise ValueError(f"邮箱 {account.name} 未配置 IMAP")

    logger.info(f"[IMAP] 拉取邮件: account={account.name}, folder={folder}, limit={limit}")

    try:
        # 连接 IMAP 服务器
        imap = aioimaplib.IMAP4_SSL(
            host=account.imap_host,
            port=account.imap_port,
        )
        await imap.wait_hello_from_server()

        # 登录
        await imap.login(account.imap_user, account.imap_password)

        # 选择文件夹
        await imap.select(folder)

        # 构建搜索条件
        search_criteria = []
        if unseen_only:
            search_criteria.append("UNSEEN")
        if since:
            date_str = since.strftime("%d-%b-%Y")
            search_criteria.append(f"SINCE {date_str}")

        if not search_criteria:
            search_criteria = ["ALL"]

        # 搜索邮件
        status, data = await imap.search(" ".join(search_criteria))
        if status != "OK":
            logger.warning(f"[IMAP] 搜索失败: {status}")
            return []

        # 获取邮件 ID 列表
        message_ids = data[0].split()
        if not message_ids:
            logger.info("[IMAP] 没有找到邮件")
            await imap.logout()
            return []

        # 取最新的 N 封
        message_ids = message_ids[-limit:]

        # 获取邮件内容
        emails = []
        for msg_id in message_ids:
            try:
                email_msg = await _fetch_email(imap, msg_id)
                if email_msg:
                    emails.append(email_msg)
            except Exception as e:
                logger.warning(f"[IMAP] 解析邮件失败 {msg_id}: {e}")

        # 登出
        await imap.logout()

        logger.info(f"[IMAP] 获取到 {len(emails)} 封邮件")
        return emails

    except Exception as e:
        logger.error(f"[IMAP] 拉取失败: {e}")
        raise


async def _fetch_email(imap, msg_id: bytes) -> Optional[EmailMessage]:
    """获取单封邮件详情"""
    status, data = await imap.fetch(msg_id.decode(), "(RFC822)")
    if status != "OK":
        return None

    # 解析邮件
    import email
    from email.policy import default

    raw_email = data[1]
    if isinstance(raw_email, tuple):
        raw_email = raw_email[1]

    msg = email.message_from_bytes(raw_email, policy=default)

    # 提取发件人
    sender_raw = msg.get("From", "")
    sender_name, sender_addr = parseaddr(sender_raw)
    if not sender_name:
        sender_name = sender_addr.split("@")[0] if sender_addr else ""

    # 解码主题
    subject = msg.get("Subject", "")
    if subject:
        decoded = decode_header(subject)
        subject = "".join(
            part.decode(charset or "utf-8") if isinstance(part, bytes) else part
            for part, charset in decoded
        )

    # 提取收件人
    recipients = []
    to_raw = msg.get("To", "")
    if to_raw:
        for addr in to_raw.split(","):
            _, email_addr = parseaddr(addr.strip())
            if email_addr:
                recipients.append(email_addr)

    # 提取日期
    date_raw = msg.get("Date", "")
    try:
        from email.utils import parsedate_to_datetime
        date = parsedate_to_datetime(date_raw)
    except Exception:
        date = datetime.now()

    # 提取正文
    body_text = ""
    body_html = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body_text = part.get_content()
                except Exception as e:
                    logger.warning(f"[IMAP] 提取纯文本失败: {e}")
            elif content_type == "text/html":
                try:
                    body_html = part.get_content()
                except Exception as e:
                    logger.warning(f"[IMAP] 提取 HTML 失败: {e}")
    else:
        try:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                body_html = msg.get_content()
            else:
                body_text = msg.get_content()
        except Exception as e:
            logger.warning(f"[IMAP] 提取邮件内容失败: {e}")

    # 如果没有纯文本，从 HTML 中提取
    if (not body_text or not body_text.strip()) and body_html:
        try:
            import re
            # 简单去除 HTML 标签
            text = re.sub(r'<style[^>]*>.*?</style>', '', body_html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            body_text = text.strip()
        except Exception as e:
            logger.warning(f"[IMAP] 从 HTML 提取文本失败: {e}")

    # 提取附件信息（不下载内容）
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachments.append({
                    "filename": part.get_filename() or "attachment",
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                })

    return EmailMessage(
        message_id=msg.get("Message-ID", f"<{uuid.uuid4()}>"),
        subject=subject,
        sender=sender_addr,
        sender_name=sender_name,
        recipients=recipients,
        date=date,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
        headers={
            "from": sender_raw,
            "to": to_raw,
            "cc": msg.get("Cc", ""),
            "reply-to": msg.get("Reply-To", ""),
        },
        raw_bytes=raw_email,  # 保留原始邮件内容用于持久化
    )


async def imap_mark_as_read(
    message_id: str,
    folder: str = "INBOX",
    account_id: Optional[int] = None,
    purpose: Optional[str] = None,
) -> bool:
    """
    标记邮件为已读

    Args:
        message_id: 邮件 Message-ID
        folder: 邮件文件夹
        account_id: 邮箱账户 ID（可选）
        purpose: 业务用途（可选）

    Returns:
        bool: 是否成功
    """
    # 获取邮箱配置
    account = await get_email_account(account_id=account_id, purpose=purpose)

    if not account.imap_configured:
        logger.warning(f"[IMAP] 邮箱 {account.name} 未配置 IMAP，无法标记已读")
        return False

    logger.info(f"[IMAP] 标记已读: {message_id} (账户: {account.name})")

    try:
        imap = aioimaplib.IMAP4_SSL(
            host=account.imap_host,
            port=account.imap_port,
        )
        await imap.wait_hello_from_server()
        await imap.login(account.imap_user, account.imap_password)
        await imap.select(folder)

        # 搜索邮件
        status, data = await imap.search(f'HEADER Message-ID "{message_id}"')
        if status == "OK" and data[0]:
            msg_id = data[0].split()[0]
            await imap.store(msg_id.decode(), "+FLAGS", "\\Seen")

        await imap.logout()
        return True

    except Exception as e:
        logger.error(f"[IMAP] 标记已读失败: {e}")
        return False


# ==================== 辅助函数 ====================

def check_email_config() -> dict:
    """
    检查环境变量邮件配置是否完整（向后兼容）

    Returns:
        dict: {"smtp": bool, "imap": bool, "errors": list}
    """
    errors = []
    smtp_ok = True
    imap_ok = True

    # 检查 SMTP 配置
    if not getattr(settings, "SMTP_HOST", None):
        errors.append("SMTP_HOST 未配置")
        smtp_ok = False
    if not getattr(settings, "SMTP_USER", None):
        errors.append("SMTP_USER 未配置")
        smtp_ok = False
    if not getattr(settings, "SMTP_PASSWORD", None):
        errors.append("SMTP_PASSWORD 未配置")
        smtp_ok = False

    # 检查 IMAP 配置
    if not getattr(settings, "IMAP_HOST", None):
        errors.append("IMAP_HOST 未配置")
        imap_ok = False
    if not getattr(settings, "IMAP_USER", None):
        errors.append("IMAP_USER 未配置")
        imap_ok = False
    if not getattr(settings, "IMAP_PASSWORD", None):
        errors.append("IMAP_PASSWORD 未配置")
        imap_ok = False

    return {
        "smtp": smtp_ok,
        "imap": imap_ok,
        "errors": errors,
    }


async def check_account_config(account_id: int) -> dict:
    """
    检查指定邮箱账户的配置状态

    Args:
        account_id: 邮箱账户 ID

    Returns:
        dict: {"smtp": bool, "imap": bool, "account_name": str}
    """
    account = await get_email_account(account_id=account_id)
    return {
        "smtp": account.smtp_configured,
        "imap": account.imap_configured,
        "account_name": account.name,
    }
