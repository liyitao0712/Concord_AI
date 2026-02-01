# app/storage/__init__.py
# 存储层模块
#
# 这个模块包含所有外部存储资源的访问实现：
# - oss.py: 阿里云 OSS 文件存储
# - email.py: 邮件收发 (IMAP/SMTP)
# - (未来) database.py: PostgreSQL 数据库访问
# - (未来) cache.py: Redis 缓存访问
# - (未来) vector.py: pgvector 向量检索

from app.storage.oss import oss_client, get_oss_client, OSSClient
from app.storage.email import (
    smtp_send,
    imap_fetch,
    imap_mark_as_read,
    check_email_config,
    check_account_config,
    get_email_account,
    get_active_imap_accounts,
    EmailMessage,
    EmailAccountConfig,
)
from app.storage.email_persistence import (
    persistence_service,
    EmailPersistenceService,
    is_signature_image,
)

__all__ = [
    # OSS
    "oss_client",
    "get_oss_client",
    "OSSClient",
    # Email
    "smtp_send",
    "imap_fetch",
    "imap_mark_as_read",
    "check_email_config",
    "check_account_config",
    "get_email_account",
    "get_active_imap_accounts",
    "EmailMessage",
    "EmailAccountConfig",
    # Email Persistence
    "persistence_service",
    "EmailPersistenceService",
    "is_signature_image",
]
