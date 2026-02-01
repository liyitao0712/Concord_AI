# tests/test_email_account_cascade.py
# 邮箱账户级联删除测试

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_account_service import EmailAccountService
from app.models.email_account import EmailAccount
from app.models.email_raw import EmailRawMessage, EmailAttachment
from app.models.email_analysis import EmailAnalysis


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def sample_account():
    """示例邮箱账户"""
    return EmailAccount(
        id=1,
        name="Test Account",
        smtp_user="test@example.com",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_password="password",
        smtp_use_tls=True,
    )


@pytest.fixture
def sample_email():
    """示例邮件"""
    return EmailRawMessage(
        id="email-001",
        email_account_id=1,
        message_id="msg-001",
        sender="sender@example.com",
        recipients='["recipient@example.com"]',
        subject="Test Email",
        oss_key="emails/raw/1/2026-01-15/email-001.eml",
        storage_type="oss",
        size_bytes=1024,
    )


@pytest.fixture
def sample_attachment():
    """示例附件"""
    return EmailAttachment(
        id="att-001",
        email_id="email-001",
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=2048,
        oss_key="emails/attachments/1/2026-01-15/att-001/test.pdf",
        storage_type="oss",
    )


class TestEmailAccountCascadeDelete:
    """邮箱账户级联删除测试"""

    @pytest.mark.asyncio
    async def test_delete_with_tolerant_mode_success(
        self,
        mock_session,
        sample_account,
        sample_email,
        sample_attachment
    ):
        """测试宽容模式成功删除"""
        # 安排
        service = EmailAccountService(strict_file_deletion=False)

        # 模拟数据库查询
        mock_session.execute = AsyncMock()

        # 第一次查询：获取账户
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = sample_account

        # 第二次查询：获取邮件列表
        emails_result = MagicMock()
        emails_result.scalars.return_value.all.return_value = [sample_email]

        # 第三次查询：删除分析结果
        analysis_result = MagicMock()
        analysis_result.rowcount = 1

        # 第四次查询：获取附件列表
        attachments_result = MagicMock()
        attachments_result.scalars.return_value.all.return_value = [sample_attachment]

        mock_session.execute.side_effect = [
            account_result,
            emails_result,
            analysis_result,
            attachments_result,
        ]

        # 模拟文件删除成功
        with patch.object(service, '_delete_storage_file', return_value=True):
            # 执行
            stats = await service._delete_cascade_impl(
                account_id=1,
                session=mock_session,
                strict_file_deletion=False
            )

        # 断言
        assert stats["emails_deleted"] == 1
        assert stats["analyses_deleted"] == 1
        assert stats["attachments_deleted"] == 1
        assert stats["files_deleted"] == 2  # 1 邮件 + 1 附件
        assert stats["files_failed"] == 0

    @pytest.mark.asyncio
    async def test_delete_with_tolerant_mode_file_failure(
        self,
        mock_session,
        sample_account,
        sample_email
    ):
        """测试宽容模式下文件删除失败"""
        # 安排
        service = EmailAccountService(strict_file_deletion=False)

        # 模拟数据库查询
        mock_session.execute = AsyncMock()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = sample_account

        emails_result = MagicMock()
        emails_result.scalars.return_value.all.return_value = [sample_email]

        analysis_result = MagicMock()
        analysis_result.rowcount = 0

        attachments_result = MagicMock()
        attachments_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            account_result,
            emails_result,
            analysis_result,
            attachments_result,
        ]

        # 模拟文件删除失败
        with patch.object(service, '_delete_storage_file', return_value=False):
            # 执行
            stats = await service._delete_cascade_impl(
                account_id=1,
                session=mock_session,
                strict_file_deletion=False
            )

        # 断言：宽容模式下，文件删除失败不影响数据库删除
        assert stats["emails_deleted"] == 1
        assert stats["files_deleted"] == 0
        assert stats["files_failed"] == 1  # 邮件文件删除失败

    @pytest.mark.asyncio
    async def test_delete_with_strict_mode_file_failure(
        self,
        mock_session,
        sample_account,
        sample_email
    ):
        """测试严格模式下文件删除失败抛出异常"""
        # 安排
        service = EmailAccountService(strict_file_deletion=True)

        # 模拟数据库查询
        mock_session.execute = AsyncMock()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = sample_account

        emails_result = MagicMock()
        emails_result.scalars.return_value.all.return_value = [sample_email]

        analysis_result = MagicMock()
        analysis_result.rowcount = 0

        attachments_result = MagicMock()
        attachments_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            account_result,
            emails_result,
            analysis_result,
            attachments_result,
        ]

        # 模拟文件删除失败
        with patch.object(service, '_delete_storage_file', return_value=False):
            # 执行并断言抛出异常
            with pytest.raises(RuntimeError, match="删除邮件 email-001 失败"):
                await service._delete_cascade_impl(
                    account_id=1,
                    session=mock_session,
                    strict_file_deletion=True
                )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_account(self, mock_session):
        """测试删除不存在的账户"""
        # 安排
        service = EmailAccountService()

        # 模拟账户不存在
        mock_session.execute = AsyncMock()
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = account_result

        # 执行并断言抛出异常
        with pytest.raises(ValueError, match="邮箱账户不存在"):
            await service._delete_cascade_impl(
                account_id=999,
                session=mock_session,
                strict_file_deletion=False
            )

    @pytest.mark.asyncio
    async def test_delete_with_multiple_emails_and_attachments(
        self,
        mock_session,
        sample_account
    ):
        """测试删除包含多封邮件和附件的账户"""
        # 安排
        service = EmailAccountService()

        # 创建多封邮件
        emails = [
            EmailRawMessage(
                id=f"email-{i}",
                email_account_id=1,
                message_id=f"msg-{i}",
                sender="sender@example.com",
                recipients='["recipient@example.com"]',
                subject=f"Email {i}",
                oss_key=f"emails/raw/1/2026-01-15/email-{i}.eml",
                storage_type="oss",
                size_bytes=1024,
            )
            for i in range(3)
        ]

        # 创建多个附件
        attachments = [
            EmailAttachment(
                id=f"att-{i}",
                email_id="email-0",
                filename=f"file-{i}.pdf",
                content_type="application/pdf",
                size_bytes=2048,
                oss_key=f"emails/attachments/1/2026-01-15/att-{i}/file-{i}.pdf",
                storage_type="oss",
            )
            for i in range(2)
        ]

        # 模拟数据库查询
        mock_session.execute = AsyncMock()

        # 返回值序列
        results = [
            # 第一次：获取账户
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_account)),
            # 第二次：获取所有邮件
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=emails)))),
        ]

        # 为每封邮件添加分析和附件查询结果
        for i in range(3):
            # 分析结果
            results.append(MagicMock(rowcount=1))
            # 附件列表（只有第一封邮件有附件）
            if i == 0:
                results.append(MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=attachments)))))
            else:
                results.append(MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

        mock_session.execute.side_effect = results

        # 模拟文件删除成功
        with patch.object(service, '_delete_storage_file', return_value=True):
            # 执行
            stats = await service._delete_cascade_impl(
                account_id=1,
                session=mock_session,
                strict_file_deletion=False
            )

        # 断言
        assert stats["emails_deleted"] == 3
        assert stats["analyses_deleted"] == 3
        assert stats["attachments_deleted"] == 2
        assert stats["files_deleted"] == 5  # 3 邮件 + 2 附件
        assert stats["files_failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
