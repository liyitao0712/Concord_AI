# app/tools/email.py
# 邮件工具
#
# 提供 Agent 发送和读取邮件的能力：
# - 发送邮件（支持 HTML 和附件）
# - 读取收件箱
# - 搜索邮件
# - 标记已读
# - 支持多邮箱账户

from datetime import datetime, timedelta
from typing import Optional

from app.core.logging import get_logger
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool
from app.storage.email import (
    smtp_send,
    imap_fetch,
    imap_mark_as_read,
    check_email_config,
    get_email_account,
    EmailMessage,
)

logger = get_logger(__name__)


@register_tool
class EmailTool(BaseTool):
    """
    邮件工具

    提供 Agent 发送和读取邮件的能力，支持多邮箱账户。
    """

    name = "email"
    description = "发送和读取邮件，支持多邮箱账户"

    @tool(
        name="send_email",
        description="发送邮件",
        parameters={
            "to": {
                "type": "string",
                "description": "收件人邮箱（多个用逗号分隔）",
            },
            "subject": {
                "type": "string",
                "description": "邮件主题",
            },
            "body": {
                "type": "string",
                "description": "邮件正文（纯文本）",
            },
            "html_body": {
                "type": "string",
                "description": "HTML 格式的正文（可选）",
            },
            "cc": {
                "type": "string",
                "description": "抄送（多个用逗号分隔，可选）",
            },
            "reply_to": {
                "type": "string",
                "description": "回复地址（可选）",
            },
            "account_id": {
                "type": "integer",
                "description": "邮箱账户 ID（可选，不指定则使用默认邮箱）",
            },
            "purpose": {
                "type": "string",
                "description": "业务用途：sales/support/notification/general（可选，用于自动选择邮箱）",
            },
        },
    )
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[str] = None,
        reply_to: Optional[str] = None,
        account_id: Optional[int] = None,
        purpose: Optional[str] = None,
    ) -> dict:
        """发送邮件"""
        logger.info(f"[EmailTool] 发送邮件: {subject} -> {to}")
        if account_id:
            logger.info(f"[EmailTool]   账户 ID: {account_id}")
        if purpose:
            logger.info(f"[EmailTool]   业务用途: {purpose}")

        try:
            # 获取邮箱账户配置（验证账户存在且已配置 SMTP）
            account = await get_email_account(account_id=account_id, purpose=purpose)
            if not account.smtp_configured:
                return {
                    "success": False,
                    "error": f"邮箱 {account.name} 未配置 SMTP",
                }

            # 解析收件人
            recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
            cc_list = (
                [addr.strip() for addr in cc.split(",") if addr.strip()]
                if cc
                else None
            )

            # 发送邮件
            message_id = await smtp_send(
                to=recipients,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc_list,
                reply_to=reply_to,
                account_id=account_id,
                purpose=purpose,
            )

            return {
                "success": True,
                "message_id": message_id,
                "recipients": recipients,
                "from_account": account.name,
            }

        except Exception as e:
            logger.error(f"[EmailTool] 发送失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="read_inbox",
        description="读取收件箱邮件",
        parameters={
            "limit": {
                "type": "integer",
                "description": "返回数量上限（默认10）",
            },
            "unread_only": {
                "type": "boolean",
                "description": "只返回未读邮件",
            },
            "days": {
                "type": "integer",
                "description": "只获取最近N天的邮件",
            },
            "account_id": {
                "type": "integer",
                "description": "邮箱账户 ID（可选，不指定则使用默认邮箱）",
            },
            "purpose": {
                "type": "string",
                "description": "业务用途：sales/support/notification/general（可选）",
            },
        },
    )
    async def read_inbox(
        self,
        limit: int = 10,
        unread_only: bool = False,
        days: Optional[int] = None,
        account_id: Optional[int] = None,
        purpose: Optional[str] = None,
    ) -> dict:
        """读取收件箱"""
        logger.info(f"[EmailTool] 读取收件箱: limit={limit}, unread_only={unread_only}")

        try:
            # 获取邮箱账户配置
            account = await get_email_account(account_id=account_id, purpose=purpose)
            if not account.imap_configured:
                return {
                    "success": False,
                    "error": f"邮箱 {account.name} 未配置 IMAP",
                    "emails": [],
                }

            # 计算时间范围
            since = None
            if days:
                since = datetime.now() - timedelta(days=days)

            # 拉取邮件
            emails = await imap_fetch(
                folder="INBOX",
                limit=limit,
                since=since,
                unseen_only=unread_only,
                account_id=account_id,
                purpose=purpose,
            )

            # 转换为字典
            email_list = [email.to_dict() for email in emails]

            return {
                "success": True,
                "count": len(email_list),
                "emails": email_list,
                "from_account": account.name,
            }

        except Exception as e:
            logger.error(f"[EmailTool] 读取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "emails": [],
            }

    @tool(
        name="search_emails",
        description="搜索邮件",
        parameters={
            "keyword": {
                "type": "string",
                "description": "搜索关键词（在主题和正文中搜索）",
            },
            "sender": {
                "type": "string",
                "description": "发件人邮箱（可选）",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量上限（默认10）",
            },
            "account_id": {
                "type": "integer",
                "description": "邮箱账户 ID（可选，不指定则使用默认邮箱）",
            },
            "purpose": {
                "type": "string",
                "description": "业务用途：sales/support/notification/general（可选）",
            },
        },
    )
    async def search_emails(
        self,
        keyword: Optional[str] = None,
        sender: Optional[str] = None,
        limit: int = 10,
        account_id: Optional[int] = None,
        purpose: Optional[str] = None,
    ) -> dict:
        """搜索邮件"""
        logger.info(f"[EmailTool] 搜索邮件: keyword={keyword}, sender={sender}")

        try:
            # 获取邮箱账户配置
            account = await get_email_account(account_id=account_id, purpose=purpose)
            if not account.imap_configured:
                return {
                    "success": False,
                    "error": f"邮箱 {account.name} 未配置 IMAP",
                    "emails": [],
                }

            # 拉取邮件
            emails = await imap_fetch(
                folder="INBOX",
                limit=limit * 2,  # 多拉一些用于过滤
                account_id=account_id,
                purpose=purpose,
            )

            # 本地过滤
            results = []
            for email in emails:
                match = True

                # 关键词匹配
                if keyword:
                    keyword_lower = keyword.lower()
                    if (
                        keyword_lower not in email.subject.lower()
                        and keyword_lower not in email.body_text.lower()
                    ):
                        match = False

                # 发件人匹配
                if sender and match:
                    if sender.lower() not in email.sender.lower():
                        match = False

                if match:
                    results.append(email.to_dict())

                if len(results) >= limit:
                    break

            return {
                "success": True,
                "count": len(results),
                "emails": results,
                "from_account": account.name,
            }

        except Exception as e:
            logger.error(f"[EmailTool] 搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "emails": [],
            }

    @tool(
        name="mark_as_read",
        description="标记邮件为已读",
        parameters={
            "message_id": {
                "type": "string",
                "description": "邮件的 Message-ID",
            },
            "account_id": {
                "type": "integer",
                "description": "邮箱账户 ID（可选，不指定则使用默认邮箱）",
            },
        },
    )
    async def mark_as_read(
        self,
        message_id: str,
        account_id: Optional[int] = None,
    ) -> dict:
        """标记邮件为已读"""
        logger.info(f"[EmailTool] 标记已读: {message_id}")

        try:
            # 获取邮箱账户配置
            account = await get_email_account(account_id=account_id)
            if not account.imap_configured:
                return {
                    "success": False,
                    "error": f"邮箱 {account.name} 未配置 IMAP",
                }

            success = await imap_mark_as_read(message_id, account_id=account_id)
            return {
                "success": success,
                "message_id": message_id,
                "from_account": account.name,
            }

        except Exception as e:
            logger.error(f"[EmailTool] 标记失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="check_email_status",
        description="检查邮件配置状态",
        parameters={
            "account_id": {
                "type": "integer",
                "description": "邮箱账户 ID（可选，不指定则检查环境变量配置）",
            },
        },
    )
    async def check_email_status(
        self,
        account_id: Optional[int] = None,
    ) -> dict:
        """检查邮件配置状态"""
        if account_id:
            # 检查指定账户
            account = await get_email_account(account_id=account_id)
            return {
                "account_id": account_id,
                "account_name": account.name,
                "smtp_configured": account.smtp_configured,
                "imap_configured": account.imap_configured,
            }
        else:
            # 检查环境变量配置（向后兼容）
            config_check = check_email_config()
            return {
                "smtp_configured": config_check["smtp"],
                "imap_configured": config_check["imap"],
                "errors": config_check["errors"],
            }

    @tool(
        name="list_email_accounts",
        description="列出所有可用的邮箱账户",
        parameters={},
    )
    async def list_email_accounts(self) -> dict:
        """列出所有可用的邮箱账户"""
        from app.storage.email import get_active_imap_accounts

        try:
            accounts = await get_active_imap_accounts()
            return {
                "success": True,
                "count": len(accounts),
                "accounts": [
                    {
                        "id": acc.id,
                        "name": acc.name,
                        "smtp_user": acc.smtp_user,
                        "imap_user": acc.imap_user,
                        "smtp_configured": acc.smtp_configured,
                        "imap_configured": acc.imap_configured,
                    }
                    for acc in accounts
                ],
            }
        except Exception as e:
            logger.error(f"[EmailTool] 获取账户列表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "accounts": [],
            }
