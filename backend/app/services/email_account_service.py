# app/services/email_account_service.py
# 邮箱账户服务层
#
# 功能说明：
# 1. 邮箱账户的业务逻辑封装
# 2. 级联删除邮箱账户及关联数据
# 3. 清理 OSS/本地存储文件
#
# 使用方法：
#   from app.services.email_account_service import email_account_service
#
#   # 删除邮箱账户（级联删除所有关联数据）
#   await email_account_service.delete_account_cascade(account_id)
#
# 配置项：
#   - strict_file_deletion: 文件删除失败时是否回滚事务（默认 False）

from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.models.email_account import EmailAccount
from app.models.email_raw import EmailRawMessage, EmailAttachment
from app.models.email_analysis import EmailAnalysis
from app.storage.oss import oss_client
from app.storage.local_file import local_storage

logger = get_logger(__name__)


class EmailAccountService:
    """
    邮箱账户服务

    提供邮箱账户相关的业务逻辑，特别是级联删除功能。
    """

    def __init__(self, strict_file_deletion: bool = False):
        """
        初始化服务

        Args:
            strict_file_deletion: 文件删除失败时是否回滚事务
                - False（默认）: 宽容模式，记录失败但继续删除数据库记录
                - True: 严格模式，文件删除失败则抛出异常，回滚整个事务
        """
        self.strict_file_deletion = strict_file_deletion

    async def delete_account_cascade(
        self,
        account_id: int,
        session: Optional[AsyncSession] = None,
        strict_file_deletion: Optional[bool] = None
    ) -> dict:
        """
        级联删除邮箱账户及所有关联数据

        删除范围：
        1. 该账户的所有邮件原始记录（email_raw_messages）
        2. 所有邮件的分析结果（email_analyses）
        3. 所有邮件的附件记录（email_attachments）
        4. OSS/本地存储中的 .eml 文件
        5. OSS/本地存储中的附件文件
        6. 邮箱账户本身（email_accounts）

        Args:
            account_id: 邮箱账户 ID
            session: 数据库会话（可选，用于事务管理）
            strict_file_deletion: 是否严格模式（覆盖实例配置）
                - None: 使用实例配置
                - True: 文件删除失败时抛出异常
                - False: 文件删除失败时仅记录日志

        Returns:
            dict: 删除统计信息
                - emails_deleted: 删除的邮件数
                - analyses_deleted: 删除的分析结果数
                - attachments_deleted: 删除的附件数
                - files_deleted: 删除的文件数
                - files_failed: 删除失败的文件数（仅宽容模式）

        Raises:
            ValueError: 账户不存在
            RuntimeError: 删除过程中发生错误（严格模式下文件删除失败）
        """
        # 确定使用的严格模式配置
        use_strict = strict_file_deletion if strict_file_deletion is not None else self.strict_file_deletion

        # 如果没有传入 session，创建新的
        if session:
            return await self._delete_cascade_impl(account_id, session, use_strict)
        else:
            async with async_session_maker() as session:
                async with session.begin():
                    return await self._delete_cascade_impl(account_id, session, use_strict)

    async def _delete_cascade_impl(
        self,
        account_id: int,
        session: AsyncSession,
        strict_file_deletion: bool
    ) -> dict:
        """
        级联删除的实际实现

        Args:
            account_id: 邮箱账户 ID
            session: 数据库会话
            strict_file_deletion: 是否严格模式

        Returns:
            dict: 删除统计
        """
        logger.info(
            f"[EmailAccountService] 开始级联删除邮箱账户: {account_id} "
            f"(严格模式: {strict_file_deletion})"
        )

        # 统计信息
        stats = {
            "emails_deleted": 0,
            "analyses_deleted": 0,
            "attachments_deleted": 0,
            "files_deleted": 0,
            "files_failed": 0,
        }

        # 1. 检查账户是否存在
        stmt = select(EmailAccount).where(EmailAccount.id == account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise ValueError(f"邮箱账户不存在: {account_id}")

        logger.info(f"[EmailAccountService] 删除账户: {account.name} ({account.email_address})")

        # 2. 查询该账户的所有邮件
        stmt = select(EmailRawMessage).where(
            EmailRawMessage.email_account_id == account_id
        )
        result = await session.execute(stmt)
        emails = result.scalars().all()

        logger.info(f"[EmailAccountService] 找到 {len(emails)} 封邮件")

        # 3. 逐个删除邮件（含附件和文件）
        for email in emails:
            try:
                await self._delete_email_with_files(email, session, stats, strict_file_deletion)
            except Exception as e:
                logger.error(f"[EmailAccountService] 删除邮件失败: {email.id}, {e}")
                # 严格模式下重新抛出异常
                if strict_file_deletion:
                    raise RuntimeError(f"删除邮件 {email.id} 失败: {e}") from e
                # 宽容模式下继续删除其他邮件

        # 4. 删除邮箱账户
        await session.delete(account)

        logger.info(
            f"[EmailAccountService] 级联删除完成: "
            f"邮件 {stats['emails_deleted']} 封, "
            f"分析 {stats['analyses_deleted']} 条, "
            f"附件 {stats['attachments_deleted']} 个, "
            f"文件 {stats['files_deleted']} 个"
            + (f", 失败 {stats['files_failed']} 个" if stats['files_failed'] > 0 else "")
        )

        return stats

    async def _delete_email_with_files(
        self,
        email: EmailRawMessage,
        session: AsyncSession,
        stats: dict,
        strict_file_deletion: bool
    ) -> None:
        """
        删除单封邮件及其文件

        Args:
            email: 邮件记录
            session: 数据库会话
            stats: 统计信息（会被修改）
            strict_file_deletion: 是否严格模式

        Raises:
            RuntimeError: 严格模式下文件删除失败
        """
        logger.debug(f"[EmailAccountService] 删除邮件: {email.id}")

        # 1. 删除邮件分析结果（显式删除，不依赖数据库级联）
        stmt = delete(EmailAnalysis).where(EmailAnalysis.email_id == email.id)
        result = await session.execute(stmt)
        analyses_count = result.rowcount
        stats["analyses_deleted"] += analyses_count
        if analyses_count > 0:
            logger.debug(f"[EmailAccountService] 删除邮件分析: {analyses_count} 条")

        # 2. 删除原始 .eml 文件
        if email.oss_key:
            success = await self._delete_storage_file(
                email.oss_key,
                email.storage_type,
                strict_file_deletion
            )
            if success:
                stats["files_deleted"] += 1
            else:
                stats["files_failed"] += 1
                if strict_file_deletion:
                    raise RuntimeError(f"删除邮件文件失败: {email.oss_key}")

        # 3. 查询并删除所有附件
        stmt = select(EmailAttachment).where(
            EmailAttachment.email_id == email.id
        )
        result = await session.execute(stmt)
        attachments = result.scalars().all()

        for attachment in attachments:
            # 删除附件文件
            if attachment.oss_key:
                success = await self._delete_storage_file(
                    attachment.oss_key,
                    attachment.storage_type,
                    strict_file_deletion
                )
                if success:
                    stats["files_deleted"] += 1
                else:
                    stats["files_failed"] += 1
                    if strict_file_deletion:
                        raise RuntimeError(f"删除附件文件失败: {attachment.oss_key}")

            # 删除附件记录（显式删除便于统计）
            await session.delete(attachment)
            stats["attachments_deleted"] += 1

        # 4. 删除邮件记录
        await session.delete(email)
        stats["emails_deleted"] += 1

    async def _delete_storage_file(
        self,
        key: str,
        storage_type: str,
        strict_mode: bool = False
    ) -> bool:
        """
        从存储中删除文件

        Args:
            key: 文件路径
            storage_type: 存储类型（oss/local）
            strict_mode: 是否严格模式（用于日志级别）

        Returns:
            bool: 是否删除成功
        """
        try:
            if storage_type == "oss":
                # 确保 OSS 客户端已连接
                if not oss_client._initialized:
                    oss_client.connect()
                result = await oss_client.delete(key)
                if result:
                    logger.debug(f"[EmailAccountService] 已删除 OSS 文件: {key}")
                return result

            elif storage_type == "local":
                # 确保本地存储已初始化
                if not local_storage._initialized:
                    local_storage.connect()
                result = await local_storage.delete(key)
                if result:
                    logger.debug(f"[EmailAccountService] 已删除本地文件: {key}")
                return result

            else:
                error_msg = f"未知存储类型: {storage_type}, 文件: {key}"
                if strict_mode:
                    logger.error(f"[EmailAccountService] {error_msg}")
                else:
                    logger.warning(f"[EmailAccountService] {error_msg}")
                return False

        except Exception as e:
            error_msg = f"删除文件失败: {key} ({storage_type}), 错误: {e}"
            if strict_mode:
                logger.error(f"[EmailAccountService] {error_msg}")
            else:
                logger.warning(f"[EmailAccountService] {error_msg}")
            return False

    async def get_account_stats(self, account_id: int) -> dict:
        """
        获取邮箱账户统计信息

        Args:
            account_id: 邮箱账户 ID

        Returns:
            dict: 统计信息（邮件数、附件数、总大小等）
        """
        async with async_session_maker() as session:
            # 查询邮件数量
            stmt = select(EmailRawMessage).where(
                EmailRawMessage.email_account_id == account_id
            )
            result = await session.execute(stmt)
            emails = result.scalars().all()

            email_count = len(emails)
            total_size = sum(email.size_bytes for email in emails)

            # 查询附件数量
            attachment_count = 0
            attachment_size = 0

            for email in emails:
                stmt = select(EmailAttachment).where(
                    EmailAttachment.email_id == email.id
                )
                result = await session.execute(stmt)
                attachments = result.scalars().all()

                attachment_count += len(attachments)
                attachment_size += sum(att.size_bytes for att in attachments)

            return {
                "email_count": email_count,
                "attachment_count": attachment_count,
                "total_email_size": total_size,
                "total_attachment_size": attachment_size,
                "total_size": total_size + attachment_size,
            }


# ==================== 全局单例 ====================

email_account_service = EmailAccountService()
