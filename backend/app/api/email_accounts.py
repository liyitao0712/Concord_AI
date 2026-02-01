# app/api/email_accounts.py
# 邮箱账户管理 API
#
# 提供邮箱账户的 CRUD 操作和连接测试功能

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.email_account import EmailAccount
from app.schemas.email_account import (
    EmailAccountCreate,
    EmailAccountUpdate,
    EmailAccountResponse,
    EmailAccountListResponse,
    EmailAccountTestRequest,
    EmailAccountTestResponse,
)
from app.services.email_account_service import email_account_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/email-accounts",
    tags=["邮箱管理"],
    dependencies=[Depends(get_current_admin_user)],
)


def _account_to_response(account: EmailAccount) -> EmailAccountResponse:
    """将数据库模型转换为响应模型"""
    return EmailAccountResponse(
        id=account.id,
        name=account.name,
        purpose=account.purpose,
        description=account.description,
        smtp_host=account.smtp_host,
        smtp_port=account.smtp_port,
        smtp_user=account.smtp_user,
        smtp_use_tls=account.smtp_use_tls,
        smtp_configured=account.smtp_configured,
        imap_host=account.imap_host,
        imap_port=account.imap_port,
        imap_user=account.imap_user,
        imap_use_ssl=account.imap_use_ssl,
        imap_configured=account.imap_configured,
        is_default=account.is_default,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("", response_model=EmailAccountListResponse)
async def list_email_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取所有邮箱账户列表
    """
    stmt = select(EmailAccount).order_by(EmailAccount.created_at.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return EmailAccountListResponse(
        total=len(accounts),
        items=[_account_to_response(a) for a in accounts],
    )


@router.post("", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_email_account(
    data: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建新的邮箱账户
    """
    logger.info(f"[EmailAccounts] 创建邮箱账户: {data.name} ({data.purpose})")

    # 如果设为默认，先取消其他默认
    if data.is_default:
        await db.execute(
            update(EmailAccount).values(is_default=False)
        )

    account = EmailAccount(
        name=data.name,
        purpose=data.purpose,
        description=data.description,
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
        smtp_user=data.smtp_user,
        smtp_password=data.smtp_password,
        smtp_use_tls=data.smtp_use_tls,
        imap_host=data.imap_host,
        imap_port=data.imap_port,
        imap_user=data.imap_user,
        imap_password=data.imap_password,
        imap_use_ssl=data.imap_use_ssl,
        is_default=data.is_default,
        is_active=True,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    logger.info(f"[EmailAccounts] 创建成功: id={account.id}")
    return _account_to_response(account)


@router.get("/{account_id}", response_model=EmailAccountResponse)
async def get_email_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取单个邮箱账户详情
    """
    stmt = select(EmailAccount).where(EmailAccount.id == account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱账户不存在",
        )

    return _account_to_response(account)


@router.put("/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: int,
    data: EmailAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新邮箱账户
    """
    stmt = select(EmailAccount).where(EmailAccount.id == account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱账户不存在",
        )

    logger.info(f"[EmailAccounts] 更新邮箱账户: id={account_id}")

    # 更新非空字段
    update_data = data.model_dump(exclude_unset=True)

    # 密码字段特殊处理：空字符串表示不修改
    if "smtp_password" in update_data and not update_data["smtp_password"]:
        del update_data["smtp_password"]
    if "imap_password" in update_data and not update_data["imap_password"]:
        del update_data["imap_password"]

    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    logger.info(f"[EmailAccounts] 更新成功: id={account_id}")
    return _account_to_response(account)


@router.get("/{account_id}/stats")
async def get_email_account_stats(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取邮箱账户统计信息

    返回该账户的邮件数、附件数、存储大小等统计数据
    """
    try:
        stats = await email_account_service.get_account_stats(account_id)
        return stats
    except Exception as e:
        logger.error(f"[EmailAccounts] 获取统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计失败: {str(e)}",
        )


@router.delete("/{account_id}", status_code=status.HTTP_200_OK)
async def delete_email_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除邮箱账户（级联删除）

    自动删除：
    - 该账户的所有邮件记录
    - 所有邮件的附件记录
    - OSS/本地存储中的所有文件
    """
    try:
        # 使用服务层的级联删除
        stats = await email_account_service.delete_account_cascade(
            account_id=account_id,
            session=db,
        )

        logger.info(
            f"[EmailAccounts] 邮箱账户删除成功: id={account_id}, "
            f"邮件={stats['emails_deleted']}, "
            f"附件={stats['attachments_deleted']}, "
            f"文件={stats['files_deleted']}"
        )

        return {
            "message": "邮箱账户已删除",
            "stats": stats,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"[EmailAccounts] 删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {str(e)}",
        )


@router.put("/{account_id}/default", response_model=EmailAccountResponse)
async def set_default_email_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    设置为默认邮箱账户
    """
    stmt = select(EmailAccount).where(EmailAccount.id == account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱账户不存在",
        )

    logger.info(f"[EmailAccounts] 设置默认邮箱: id={account_id}")

    # 取消其他默认
    await db.execute(
        update(EmailAccount).values(is_default=False)
    )

    # 设置当前为默认
    account.is_default = True
    await db.commit()
    await db.refresh(account)

    return _account_to_response(account)


@router.post("/{account_id}/test", response_model=EmailAccountTestResponse)
async def test_email_account(
    account_id: int,
    data: EmailAccountTestRequest = EmailAccountTestRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    测试邮箱连接

    分别测试 SMTP 和 IMAP 连接是否正常
    """
    stmt = select(EmailAccount).where(EmailAccount.id == account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱账户不存在",
        )

    logger.info(f"[EmailAccounts] 测试邮箱连接: id={account_id}")

    response = EmailAccountTestResponse()

    # 测试 SMTP
    if data.test_smtp and account.smtp_configured:
        try:
            import aiosmtplib

            smtp = aiosmtplib.SMTP(
                hostname=account.smtp_host,
                port=account.smtp_port,
                use_tls=account.smtp_use_tls,
            )
            await smtp.connect()
            await smtp.login(account.smtp_user, account.smtp_password)
            await smtp.quit()

            response.smtp_success = True
            response.smtp_message = "SMTP 连接成功"
            logger.info(f"[EmailAccounts] SMTP 测试成功: id={account_id}")

        except Exception as e:
            response.smtp_success = False
            response.smtp_message = f"SMTP 连接失败: {str(e)}"
            logger.warning(f"[EmailAccounts] SMTP 测试失败: id={account_id}, error={e}")

    # 测试 IMAP
    if data.test_imap and account.imap_configured:
        try:
            import aioimaplib

            imap = aioimaplib.IMAP4_SSL(
                host=account.imap_host,
                port=account.imap_port,
            )
            await imap.wait_hello_from_server()
            await imap.login(account.imap_user, account.imap_password)
            await imap.logout()

            response.imap_success = True
            response.imap_message = "IMAP 连接成功"
            logger.info(f"[EmailAccounts] IMAP 测试成功: id={account_id}")

        except Exception as e:
            response.imap_success = False
            response.imap_message = f"IMAP 连接失败: {str(e)}"
            logger.warning(f"[EmailAccounts] IMAP 测试失败: id={account_id}, error={e}")

    return response
