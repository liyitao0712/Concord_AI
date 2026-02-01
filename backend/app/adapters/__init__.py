# app/adapters/__init__.py
# 渠道适配器模块
#
# 功能说明：
# 1. 将各渠道的原始数据转换为统一事件格式 (UnifiedEvent)
# 2. 将处理结果发送回原渠道
#
# 支持的渠道：
# - Chatbox (Web)
# - Feishu (飞书)
# - Webhook
# - Email (邮件)
#
# 注意：邮件监听功能已迁移到 workers/email_worker.py

from app.adapters.base import BaseAdapter
from app.adapters.feishu import FeishuAdapter, FeishuClient, feishu_client, feishu_adapter
from app.adapters.email import EmailAdapter, email_adapter

__all__ = [
    "BaseAdapter",
    "FeishuAdapter",
    "FeishuClient",
    "feishu_client",
    "feishu_adapter",
    "EmailAdapter",
    "email_adapter",
]
