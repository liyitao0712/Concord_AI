# app/storage/email_persistence.py
# 邮件持久化服务
#
# 功能说明：
# 1. 将邮件原始内容 (.eml) 上传到 OSS
# 2. 解析并上传附件，识别签名图片
# 3. 创建数据库记录
# 4. 提供附件访问接口
#
# 使用方法：
#   from app.storage.email_persistence import persistence_service
#
#   # 持久化邮件
#   raw_record = await persistence_service.persist(email_message, account_id)
#
#   # 标记处理完成
#   await persistence_service.mark_processed(raw_record.id, event_id)
#
#   # 获取附件下载链接
#   url = await persistence_service.get_attachment_url(attachment_id)

import json
import email
from email.policy import default as email_policy
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core import database  # 导入模块而不是直接导入 async_session_maker
from app.storage.oss import oss_client
from app.storage.local_file import local_storage
from app.storage.email import EmailMessage
from app.models.email_raw import EmailRawMessage, EmailAttachment

logger = get_logger(__name__)


class StorageBackend:
    """存储后端枚举"""
    OSS = "oss"
    LOCAL = "local"


def is_signature_image(part: email.message.Message) -> bool:
    """
    判断邮件部分是否为签名图片

    签名图片的特征：
    1. Content-Type 是图片类型 (image/*)
    2. Content-Disposition 为 inline
    3. 有 Content-ID（被 HTML 正文通过 cid: 引用）

    Args:
        part: 邮件 MIME 部分

    Returns:
        bool: 是否为签名图片
    """
    content_type = part.get_content_type()
    disposition = part.get("Content-Disposition", "")
    content_id = part.get("Content-ID")

    # 必须是图片
    if not content_type.startswith("image/"):
        return False

    # inline + 有 Content-ID = 签名图片
    if "inline" in disposition.lower() and content_id:
        return True

    return False


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名（用于 OSS key）

    Args:
        filename: 原始文件名

    Returns:
        str: URL 安全的文件名
    """
    if not filename:
        return "attachment"
    # URL 编码，但保留一些常见字符
    return quote(filename, safe=".-_")


class EmailPersistenceService:
    """
    邮件持久化服务

    负责将邮件原始数据和附件持久化到 OSS 或本地存储，并在数据库记录元数据。

    存储策略：
    1. 优先使用 OSS（如果已配置）
    2. OSS 失败或未配置时，降级到本地存储
    3. 本地存储也失败时，抛出异常
    """

    @staticmethod
    def _to_naive_datetime(dt: datetime) -> datetime:
        """将 timezone-aware datetime 转换为 timezone-naive（UTC）"""
        if dt.tzinfo is not None:
            # 转换为 UTC 并移除时区信息
            from datetime import timezone
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    async def _upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> tuple[str, str]:
        """
        上传文件（自动选择 OSS 或本地存储）

        Args:
            key: 文件路径
            data: 文件内容
            content_type: MIME 类型

        Returns:
            tuple[str, str]: (存储后端类型, 存储路径/URL)
        """
        # 尝试 OSS
        try:
            oss_client.connect()
            url = await oss_client.upload(key=key, data=data, content_type=content_type)
            logger.debug(f"[EmailPersistence] OSS 上传成功: {key}")
            return (StorageBackend.OSS, key)
        except Exception as e:
            logger.warning(f"[EmailPersistence] OSS 上传失败，尝试本地存储: {e}")

        # 降级到本地存储
        try:
            local_storage.connect()
            url = await local_storage.upload(key=key, data=data, content_type=content_type)
            logger.info(f"[EmailPersistence] 本地存储上传成功: {key}")
            return (StorageBackend.LOCAL, key)
        except Exception as e:
            logger.error(f"[EmailPersistence] 本地存储上传也失败: {e}")
            raise RuntimeError(f"文件上传失败（OSS 和本地存储均失败）: {key}")

    async def _delete_file(self, key: str, storage_type: str) -> bool:
        """
        删除文件

        Args:
            key: 文件路径
            storage_type: 存储类型（oss/local）

        Returns:
            bool: 是否删除成功
        """
        try:
            if storage_type == StorageBackend.OSS:
                return await oss_client.delete(key)
            elif storage_type == StorageBackend.LOCAL:
                return await local_storage.delete(key)
            else:
                logger.warning(f"[EmailPersistence] 未知存储类型: {storage_type}")
                return False
        except Exception as e:
            logger.error(f"[EmailPersistence] 删除文件失败: {key}, {e}")
            return False

    async def persist(
        self,
        email_msg: EmailMessage,
        account_id: Optional[int] = None,
    ) -> EmailRawMessage:
        """
        持久化邮件

        流程：
        1. 检查是否已存在（幂等）
        2. 上传原始 .eml 到 OSS
        3. 解析附件，判断签名图片
        4. 上传附件到 OSS
        5. 创建数据库记录

        Args:
            email_msg: 邮件消息对象（需要包含 raw_bytes）
            account_id: 邮箱账户 ID

        Returns:
            EmailRawMessage: 创建的记录

        Raises:
            ValueError: 如果邮件没有 raw_bytes
        """
        if not email_msg.raw_bytes:
            raise ValueError("EmailMessage 没有 raw_bytes，无法持久化")

        async with database.async_session_maker() as session:
            # 1. 幂等检查
            existing = await self._get_by_message_id(session, email_msg.message_id)
            if existing:
                logger.info(f"[EmailPersistence] 邮件已存在: {email_msg.message_id}")
                return existing

            # 2. 生成 ID 和存储路径
            record_id = str(uuid4())
            account_prefix = str(account_id) if account_id else "env"
            date_str = datetime.now().strftime("%Y-%m-%d")
            storage_key = f"emails/raw/{account_prefix}/{date_str}/{record_id}.eml"

            # 3. 上传原始邮件（自动选择 OSS 或本地存储）
            storage_type, storage_path = await self._upload_file(
                key=storage_key,
                data=email_msg.raw_bytes,
                content_type="message/rfc822",
            )
            logger.info(f"[EmailPersistence] 上传原始邮件: {storage_path} ({storage_type})")

            # 4. 创建主记录
            # 保存完整正文到数据库
            raw_record = EmailRawMessage(
                id=record_id,
                email_account_id=account_id,
                message_id=email_msg.message_id,
                sender=email_msg.sender,
                sender_name=email_msg.sender_name,
                subject=email_msg.subject or "",
                body_text=email_msg.body_text or "",  # 保存完整正文（不再截断）
                received_at=self._to_naive_datetime(email_msg.date) if email_msg.date else datetime.now(),
                oss_key=storage_path,  # 存储路径（兼容字段名）
                storage_type=storage_type,  # 存储类型
                size_bytes=len(email_msg.raw_bytes),
            )
            raw_record.set_recipients(email_msg.recipients)

            session.add(raw_record)

            # 5. 解析并上传附件
            attachments = await self._process_attachments(
                raw_bytes=email_msg.raw_bytes,
                email_id=record_id,
                account_prefix=account_prefix,
                date_str=date_str,
            )
            for att in attachments:
                session.add(att)
                raw_record.attachments.append(att)

            await session.commit()
            await session.refresh(raw_record)

            logger.info(
                f"[EmailPersistence] 持久化完成: {record_id}, "
                f"附件: {len(attachments)} 个"
            )

            return raw_record

    async def _process_attachments(
        self,
        raw_bytes: bytes,
        email_id: str,
        account_prefix: str,
        date_str: str,
    ) -> List[EmailAttachment]:
        """
        解析并上传附件

        Args:
            raw_bytes: 原始邮件内容
            email_id: 邮件记录 ID
            account_prefix: OSS 路径前缀（account_id 或 'env'）
            date_str: 日期字符串

        Returns:
            List[EmailAttachment]: 附件记录列表
        """
        attachments = []

        # 解析邮件
        msg = email.message_from_bytes(raw_bytes, policy=email_policy)

        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            # 跳过非附件部分
            content_disposition = part.get("Content-Disposition", "")
            if not content_disposition:
                continue

            # 跳过纯文本/HTML 正文
            content_type = part.get_content_type()
            if content_type in ("text/plain", "text/html") and "attachment" not in content_disposition.lower():
                continue

            # 获取文件名
            filename = part.get_filename()
            if not filename:
                # inline 图片可能没有 filename
                if "inline" in content_disposition.lower():
                    # 根据 Content-Type 生成文件名
                    ext = content_type.split("/")[-1] if "/" in content_type else "bin"
                    filename = f"inline_{uuid4().hex[:8]}.{ext}"
                else:
                    continue

            # 获取内容
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
            except Exception as e:
                logger.warning(f"[EmailPersistence] 解析附件失败: {filename}, {e}")
                continue

            # 判断是否为签名图片
            is_inline = "inline" in content_disposition.lower()
            content_id = part.get("Content-ID")
            is_sig = is_signature_image(part)

            # 生成附件 ID 和存储路径
            att_id = str(uuid4())
            safe_name = safe_filename(filename)
            storage_key = f"emails/attachments/{account_prefix}/{date_str}/{att_id}/{safe_name}"

            # 上传附件（自动选择 OSS 或本地存储）
            try:
                att_storage_type, att_storage_path = await self._upload_file(
                    key=storage_key,
                    data=payload,
                    content_type=content_type,
                )
                logger.debug(f"[EmailPersistence] 上传附件: {att_storage_path} ({att_storage_type})")
            except Exception as e:
                logger.error(f"[EmailPersistence] 附件上传失败: {filename}, {e}")
                # 附件上传失败，跳过该附件
                continue

            # 创建附件记录
            attachment = EmailAttachment(
                id=att_id,
                email_id=email_id,
                filename=filename,
                content_type=content_type,
                size_bytes=len(payload),
                oss_key=att_storage_path,  # 存储路径
                storage_type=att_storage_type,  # 存储类型
                is_inline=is_inline,
                content_id=content_id.strip("<>") if content_id else None,
                is_signature=is_sig,
            )
            attachments.append(attachment)

            if is_sig:
                logger.debug(f"[EmailPersistence] 检测到签名图片: {filename}")

        return attachments

    async def _get_by_message_id(
        self,
        session: AsyncSession,
        message_id: str,
    ) -> Optional[EmailRawMessage]:
        """根据 Message-ID 查询"""
        stmt = select(EmailRawMessage).where(
            EmailRawMessage.message_id == message_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_processed(
        self,
        email_id: str,
        event_id: str,
    ) -> None:
        """
        标记邮件已处理

        Args:
            email_id: 邮件记录 ID
            event_id: 关联的 UnifiedEvent ID
        """
        async with database.async_session_maker() as session:
            stmt = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                record.is_processed = True
                record.event_id = event_id
                record.processed_at = datetime.utcnow()
                await session.commit()
                logger.debug(f"[EmailPersistence] 标记已处理: {email_id}")

    async def get_attachments(
        self,
        email_id: str,
        include_signatures: bool = False,
    ) -> List[EmailAttachment]:
        """
        获取邮件附件列表

        Args:
            email_id: 邮件记录 ID
            include_signatures: 是否包含签名图片

        Returns:
            List[EmailAttachment]: 附件列表
        """
        async with database.async_session_maker() as session:
            stmt = select(EmailAttachment).where(
                EmailAttachment.email_id == email_id
            )
            if not include_signatures:
                stmt = stmt.where(EmailAttachment.is_signature == False)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_attachment_url(
        self,
        attachment_id: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        获取附件下载 URL（签名）

        Args:
            attachment_id: 附件 ID
            expires: URL 有效期（秒），默认 1 小时

        Returns:
            str: 签名 URL，如果附件不存在返回 None
        """
        async with database.async_session_maker() as session:
            stmt = select(EmailAttachment).where(
                EmailAttachment.id == attachment_id
            )
            result = await session.execute(stmt)
            attachment = result.scalar_one_or_none()

            if not attachment:
                return None

            # 根据存储类型生成 URL
            if attachment.storage_type == StorageBackend.OSS:
                return oss_client.get_signed_url(attachment.oss_key, expires=expires)
            elif attachment.storage_type == StorageBackend.LOCAL:
                return local_storage.get_signed_url(attachment.oss_key, expires=expires)
            else:
                logger.warning(f"[EmailPersistence] 未知存储类型: {attachment.storage_type}")
                return None

    async def get_raw_email_url(
        self,
        email_id: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        获取原始邮件下载 URL（签名）

        Args:
            email_id: 邮件记录 ID
            expires: URL 有效期（秒）

        Returns:
            str: 签名 URL
        """
        async with database.async_session_maker() as session:
            stmt = select(EmailRawMessage).where(EmailRawMessage.id == email_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return None

            # 根据存储类型生成 URL
            if record.storage_type == StorageBackend.OSS:
                return oss_client.get_signed_url(record.oss_key, expires=expires)
            elif record.storage_type == StorageBackend.LOCAL:
                return local_storage.get_signed_url(record.oss_key, expires=expires)
            else:
                logger.warning(f"[EmailPersistence] 未知存储类型: {record.storage_type}")
                return None


# 全局单例
persistence_service = EmailPersistenceService()
