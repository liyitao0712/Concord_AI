# app/workflows/types.py
# 工作流共享数据类型
#
# 这个文件定义了 Workflow 和 Activity 之间共享的数据类型。
# 放在单独的文件中是为了避免在 Workflow 沙箱中导入不允许的模块。
#
# 注意：这个文件不应该导入任何可能包含非确定性操作的模块
# （如 logging、pathlib、random 等）

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


# ==================== 通知相关类型 ====================

class NotificationType(str, Enum):
    """通知类型枚举"""
    EMAIL = "email"           # 邮件通知
    SMS = "sms"               # 短信通知
    WEBHOOK = "webhook"       # Webhook 回调
    IN_APP = "in_app"         # 应用内通知


@dataclass
class NotificationRequest:
    """
    通知请求数据类

    用于统一表示各类通知请求。

    Attributes:
        type: 通知类型
        recipient: 接收者（邮箱/手机号/URL）
        title: 通知标题
        content: 通知内容
        metadata: 附加元数据
    """
    type: NotificationType
    recipient: str
    title: str
    content: str
    metadata: Optional[dict] = None


# ==================== 工作流事件类型 ====================

@dataclass
class WorkflowEvent:
    """
    工作流事件数据类

    用于记录工作流执行过程中的事件。

    Attributes:
        workflow_id: 工作流 ID
        workflow_type: 工作流类型
        event_type: 事件类型（started, completed, failed, etc.）
        event_data: 事件数据
        timestamp: 事件时间
    """
    workflow_id: str
    workflow_type: str
    event_type: str
    event_data: Optional[dict] = None
    timestamp: Optional[datetime] = None


# ==================== 审批相关类型 ====================

class ApprovalStatus(str, Enum):
    """审批状态枚举"""
    PENDING = "pending"       # 待审批
    APPROVED = "approved"     # 已通过
    REJECTED = "rejected"     # 已拒绝
    TIMEOUT = "timeout"       # 已超时
    CANCELLED = "cancelled"   # 已取消


@dataclass
class ApprovalRequest:
    """
    审批请求数据类

    Attributes:
        request_id: 请求唯一标识（如订单ID）
        request_type: 请求类型（如 "order_approval"）
        requester_id: 申请人ID
        requester_name: 申请人姓名
        approver_id: 审批人ID
        approver_email: 审批人邮箱
        title: 审批标题
        description: 审批描述
        amount: 涉及金额（可选）
        timeout_hours: 超时时间（小时），默认24小时
        metadata: 附加元数据
    """
    request_id: str
    request_type: str
    requester_id: str
    requester_name: str
    approver_id: str
    approver_email: str
    title: str
    description: str
    amount: Optional[float] = None
    timeout_hours: int = 24
    metadata: Optional[dict] = None


@dataclass
class ApprovalResult:
    """
    审批结果数据类

    Attributes:
        request_id: 请求唯一标识
        status: 审批状态
        approver_id: 实际审批人ID（可能与预期不同）
        comment: 审批意见
        approved_at: 审批时间（ISO 格式字符串）
    """
    request_id: str
    status: ApprovalStatus
    approver_id: Optional[str] = None
    comment: Optional[str] = None
    approved_at: Optional[str] = None
