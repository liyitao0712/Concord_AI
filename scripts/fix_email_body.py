#!/usr/bin/env python3
"""
修复邮件正文

支持两种方式：
1. 从 OSS 下载原始邮件重新解析（推荐，更快）
2. 从 IMAP 重新获取邮件

用法:
    cd backend
    source venv/bin/activate
    python ../scripts/fix_email_body.py [--limit N] [--account-id ID] [--from-oss]
"""

import asyncio
import argparse
import sys
import os

# 添加 backend 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import datetime
from sqlalchemy import select, update
from aioimaplib import aioimaplib
import email as email_lib
from email.policy import default as email_policy
from email.header import decode_header
from email.utils import parseaddr

from app.core.database import async_session_maker
from app.core.logging import get_logger, setup_logging
from app.models.email_raw import EmailRawMessage
from app.storage.email import get_email_account, get_active_imap_accounts
from app.storage.oss import oss_client

setup_logging()
logger = get_logger(__name__)


async def fetch_email_body_from_imap(
    message_id: str,
    sender: str,
    subject: str,
    received_at: datetime,
    account_id: int = None,
) -> tuple[str, str]:
    """
    从 IMAP 获取邮件正文

    使用多种搜索策略：
    1. 按 Message-ID 搜索
    2. 按发件人 + 日期范围搜索
    3. 按主题搜索（作为最后手段）

    Args:
        message_id: 邮件 Message-ID
        sender: 发件人地址
        subject: 邮件主题
        received_at: 接收时间
        account_id: 邮箱账户 ID

    Returns:
        tuple[str, str]: (纯文本正文, HTML正文)
    """
    # 获取邮箱配置
    account = await get_email_account(account_id=account_id)
    if not account.imap_configured:
        raise ValueError(f"邮箱 {account.name} 未配置 IMAP")

    try:
        # 连接 IMAP
        imap = aioimaplib.IMAP4_SSL(
            host=account.imap_host,
            port=account.imap_port,
        )
        await imap.wait_hello_from_server()
        await imap.login(account.imap_user, account.imap_password)

        # 搜索邮件（在多个文件夹中查找）
        folders = [account.imap_folder, "INBOX", "Sent", "已发送", "Drafts", "Archive", "归档"]
        msg_data = None

        # 准备多种搜索条件
        clean_id = message_id.strip('<>') if message_id else ""
        date_str = received_at.strftime("%d-%b-%Y") if received_at else ""

        search_strategies = []
        # 策略1: Message-ID（最精确）
        if clean_id:
            search_strategies.append(f'HEADER Message-ID "<{clean_id}>"')
        # 策略2: 发件人 + 日期
        if sender and date_str:
            search_strategies.append(f'FROM "{sender}" ON {date_str}')
        # 策略3: 发件人 + 日期范围（前后1天）
        if sender and received_at:
            from datetime import timedelta
            day_before = (received_at - timedelta(days=1)).strftime("%d-%b-%Y")
            day_after = (received_at + timedelta(days=1)).strftime("%d-%b-%Y")
            search_strategies.append(f'FROM "{sender}" SINCE {day_before} BEFORE {day_after}')

        for folder in folders:
            if msg_data:
                break
            try:
                status, _ = await imap.select(folder)
                if status != "OK":
                    continue

                for search_criteria in search_strategies:
                    try:
                        status, data = await imap.search(search_criteria)
                        if status == "OK" and data[0]:
                            msg_ids = data[0].split()
                            if msg_ids:
                                # 如果找到多封，需要进一步匹配
                                for mid in msg_ids[-5:]:  # 只检查最近5封
                                    status, fetch_data = await imap.fetch(mid.decode(), "(RFC822)")
                                    if status == "OK" and fetch_data[1]:
                                        # 验证是否是我们要找的邮件
                                        test_data = fetch_data[1]
                                        if isinstance(test_data, tuple):
                                            test_data = test_data[1]
                                        test_msg = email_lib.message_from_bytes(test_data, policy=email_policy)
                                        test_id = test_msg.get("Message-ID", "").strip('<>')

                                        # 匹配 Message-ID 或主题
                                        if clean_id and clean_id in test_id:
                                            msg_data = fetch_data[1]
                                            break
                                        elif subject and subject in str(test_msg.get("Subject", "")):
                                            msg_data = fetch_data[1]
                                            break
                                if msg_data:
                                    break
                    except Exception as e:
                        logger.debug(f"搜索 '{search_criteria}' 失败: {e}")
                        continue
            except Exception as e:
                logger.debug(f"在文件夹 {folder} 中搜索失败: {e}")
                continue

        await imap.logout()

        if not msg_data:
            return "", ""

        # 解析邮件
        if isinstance(msg_data, tuple):
            msg_data = msg_data[1]

        msg = email_lib.message_from_bytes(msg_data, policy=email_policy)

        # 提取正文
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not body_text:
                    try:
                        body_text = part.get_content()
                    except Exception:
                        pass
                elif content_type == "text/html" and not body_html:
                    try:
                        body_html = part.get_content()
                    except Exception:
                        pass
        else:
            try:
                content = msg.get_content()
                if msg.get_content_type() == "text/html":
                    body_html = content
                else:
                    body_text = content
            except Exception:
                pass

        return body_text or "", body_html or ""

    except Exception as e:
        logger.error(f"从 IMAP 获取邮件失败: {e}")
        return "", ""


def html_to_text(html: str) -> str:
    """简单的 HTML 转文本"""
    import re
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


async def fetch_email_body_from_oss(oss_key: str) -> tuple[str, str]:
    """
    从 OSS 下载并解析邮件正文

    Args:
        oss_key: OSS 对象键名

    Returns:
        tuple[str, str]: (纯文本正文, HTML正文)
    """
    try:
        # 从 OSS 下载原始邮件
        raw_bytes = await oss_client.download(oss_key)
        if not raw_bytes:
            return "", ""

        # 解析邮件
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
                    except Exception as e:
                        logger.debug(f"提取纯文本失败: {e}")
                elif content_type == "text/html":
                    try:
                        body_html = part.get_content()
                    except Exception as e:
                        logger.debug(f"提取 HTML 失败: {e}")
        else:
            try:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    body_html = msg.get_content()
                else:
                    body_text = msg.get_content()
            except Exception as e:
                logger.debug(f"提取邮件内容失败: {e}")

        return body_text or "", body_html or ""

    except Exception as e:
        logger.error(f"从 OSS 解析邮件失败: {e}")
        return "", ""


async def fix_emails(limit: int = None, account_id: int = None, dry_run: bool = False, from_oss: bool = True):
    """
    修复没有 body_text 的邮件

    Args:
        limit: 最大处理数量
        account_id: 只处理指定账户的邮件
        dry_run: 仅显示，不实际更新
    """
    async with async_session_maker() as session:
        # 查询没有 body_text 的邮件
        query = select(EmailRawMessage).where(
            (EmailRawMessage.body_text.is_(None)) | (EmailRawMessage.body_text == "")
        )

        if account_id:
            query = query.where(EmailRawMessage.email_account_id == account_id)

        query = query.order_by(EmailRawMessage.received_at.desc())

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        emails = result.scalars().all()

        print(f"\n找到 {len(emails)} 封需要修复的邮件")

        if dry_run:
            print("\n[DRY RUN] 以下邮件将被处理:")
            for email in emails:
                print(f"  - {email.id[:8]}... | {email.sender} | {email.subject[:40]}")
            return

        success_count = 0
        fail_count = 0

        for i, email in enumerate(emails, 1):
            print(f"\n[{i}/{len(emails)}] 处理: {email.subject[:50]}...")

            try:
                body_text = ""
                body_html = ""

                # 优先从 OSS 解析
                if from_oss and email.oss_key and email.oss_key.strip():
                    print(f"  从 OSS 解析: {email.oss_key}")
                    body_text, body_html = await fetch_email_body_from_oss(email.oss_key)

                # 如果 OSS 失败或未指定，从 IMAP 获取
                if not body_text and not body_html and not from_oss:
                    print(f"  从 IMAP 获取...")
                    body_text, body_html = await fetch_email_body_from_imap(
                        message_id=email.message_id,
                        sender=email.sender,
                        subject=email.subject,
                        received_at=email.received_at,
                        account_id=email.email_account_id,
                    )

                # 优先纯文本，否则从 HTML 转换
                final_text = body_text
                if not final_text and body_html:
                    final_text = html_to_text(body_html)

                if final_text:
                    # 截取前 5000 字符
                    final_text = final_text[:5000]

                    # 更新数据库
                    email.body_text = final_text
                    await session.commit()

                    print(f"  ✓ 成功获取正文 ({len(final_text)} 字符)")
                    success_count += 1
                else:
                    print(f"  ✗ 未找到邮件正文")
                    fail_count += 1

            except Exception as e:
                print(f"  ✗ 失败: {e}")
                fail_count += 1
                await session.rollback()

            # 避免请求过快
            if not from_oss:
                await asyncio.sleep(0.5)

        print(f"\n完成! 成功: {success_count}, 失败: {fail_count}")


async def main():
    parser = argparse.ArgumentParser(description="修复邮件正文")
    parser.add_argument("--limit", type=int, help="最大处理数量")
    parser.add_argument("--account-id", type=int, help="只处理指定账户的邮件")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际更新")
    parser.add_argument("--from-oss", action="store_true", default=True, help="从 OSS 解析（默认，更快）")
    parser.add_argument("--from-imap", action="store_true", help="从 IMAP 重新获取")
    args = parser.parse_args()

    print("=" * 60)
    print("  邮件正文修复工具")
    print("=" * 60)

    # 如果指定了 --from-imap，则不使用 OSS
    from_oss = not args.from_imap

    if from_oss:
        print("\n模式: 从 OSS 重新解析（推荐）")
    else:
        print("\n模式: 从 IMAP 重新获取")

    await fix_emails(
        limit=args.limit,
        account_id=args.account_id,
        dry_run=args.dry_run,
        from_oss=from_oss,
    )


if __name__ == "__main__":
    asyncio.run(main())
