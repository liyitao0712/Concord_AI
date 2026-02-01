# app/workflows/definitions/email_process.py
# 邮件处理工作流
#
# 功能说明：
# 1. 接收邮件事件
# 2. 根据意图路由到不同的处理分支
# 3. 调用相应的 Agent 处理
# 4. 如需审批，启动审批子流程
# 5. 发送回复邮件
# 6. 更新事件状态
#
# 支持的意图：
# - inquiry: 询价 -> 报价 Agent -> 生成报价单 -> (审批) -> 发送回复
# - order: 订单 -> 订单 Agent -> 创建订单 -> 通知
# - complaint: 投诉 -> 投诉 Agent -> 升级处理
# - follow_up: 跟进 -> 跟进 Agent -> 更新状态
# - other: 其他 -> 人工处理通知

from datetime import timedelta
from typing import Optional
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.workflows.types import (
    ApprovalStatus,
    ApprovalRequest,
    NotificationRequest,
    NotificationType,
    WorkflowEvent,
)
from app.workflows.activities.email import (
    RunAgentRequest,
    SendEmailRequest,
    UpdateEventRequest,
)


# ==================== 数据类型 ====================

@dataclass
class EmailProcessInput:
    """邮件处理 Workflow 输入"""
    event_id: str
    event_type: str
    source: str
    source_id: Optional[str]
    content: str
    content_type: str
    user_external_id: Optional[str]
    user_name: Optional[str]
    session_id: Optional[str]
    thread_id: Optional[str]
    intent: str
    metadata: Optional[dict]


@dataclass
class EmailProcessResult:
    """邮件处理 Workflow 结果"""
    success: bool
    event_id: str
    intent: str
    action_taken: str
    response_sent: bool
    error: Optional[str] = None
    data: Optional[dict] = None


# ==================== Workflow 定义 ====================

@workflow.defn
class EmailProcessWorkflow:
    """
    邮件处理工作流

    根据邮件意图路由到不同的处理分支，
    调用相应的 Agent 处理，并发送回复。

    流程：
    1. 记录开始事件
    2. 根据意图路由
    3. 调用对应的 Agent
    4. (如需) 启动审批子流程
    5. 发送回复邮件
    6. 更新事件状态
    7. 返回结果
    """

    def __init__(self):
        """初始化 Workflow 状态"""
        self._status = "processing"
        self._result: Optional[EmailProcessResult] = None

    @workflow.run
    async def run(self, input_data: dict, intent: str) -> EmailProcessResult:
        """
        工作流主函数

        Args:
            input_data: 事件数据字典
            intent: 意图类型

        Returns:
            EmailProcessResult: 处理结果
        """
        workflow.logger.info(f"邮件处理工作流启动")
        workflow.logger.info(f"  Event ID: {input_data.get('event_id')}")
        workflow.logger.info(f"  Intent: {intent}")
        workflow.logger.info(f"  From: {input_data.get('user_external_id')}")

        # 定义重试策略
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
            maximum_attempts=3,
        )

        event_id = input_data.get("event_id", "")

        try:
            # 1. 记录开始事件
            await workflow.execute_activity(
                "log_workflow_event",
                WorkflowEvent(
                    workflow_id=workflow.info().workflow_id,
                    workflow_type="EmailProcessWorkflow",
                    event_type="started",
                    event_data={
                        "event_id": event_id,
                        "intent": intent,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=retry_policy,
            )

            # 2. 根据意图路由处理
            if intent == "inquiry":
                result = await self._handle_inquiry(input_data, retry_policy)
            elif intent == "order":
                result = await self._handle_order(input_data, retry_policy)
            elif intent == "complaint":
                result = await self._handle_complaint(input_data, retry_policy)
            elif intent == "follow_up":
                result = await self._handle_follow_up(input_data, retry_policy)
            else:
                result = await self._handle_other(input_data, retry_policy)

            # 3. 更新事件状态
            await workflow.execute_activity(
                "update_event_status",
                UpdateEventRequest(
                    event_id=event_id,
                    status="completed" if result.success else "failed",
                    response=result.data.get("reply_content") if result.data else None,
                    workflow_id=workflow.info().workflow_id,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=retry_policy,
            )

            # 4. 记录完成事件
            await workflow.execute_activity(
                "log_workflow_event",
                WorkflowEvent(
                    workflow_id=workflow.info().workflow_id,
                    workflow_type="EmailProcessWorkflow",
                    event_type="completed",
                    event_data={
                        "event_id": event_id,
                        "success": result.success,
                        "action_taken": result.action_taken,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=retry_policy,
            )

            self._status = "completed"
            self._result = result
            return result

        except Exception as e:
            workflow.logger.error(f"邮件处理失败: {e}")

            # 更新事件状态为失败
            await workflow.execute_activity(
                "update_event_status",
                UpdateEventRequest(
                    event_id=event_id,
                    status="failed",
                    error=str(e),
                    workflow_id=workflow.info().workflow_id,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=retry_policy,
            )

            self._status = "failed"
            return EmailProcessResult(
                success=False,
                event_id=event_id,
                intent=intent,
                action_taken="error",
                response_sent=False,
                error=str(e),
            )

    async def _handle_inquiry(
        self,
        input_data: dict,
        retry_policy: RetryPolicy,
    ) -> EmailProcessResult:
        """
        处理询价

        流程：
        1. 调用报价 Agent
        2. 检查是否需要审批
        3. (如需) 启动审批子流程
        4. 发送报价邮件
        """
        workflow.logger.info("处理询价请求")
        event_id = input_data.get("event_id", "")
        metadata = input_data.get("metadata", {})

        # 1. 调用报价 Agent
        agent_result = await workflow.execute_activity(
            "run_quote_agent",
            RunAgentRequest(
                agent_name="quote_agent",
                input_text=input_data.get("content", ""),
                input_data={
                    "subject": metadata.get("subject", ""),
                    "sender": input_data.get("user_external_id", ""),
                },
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        if not agent_result.success:
            return EmailProcessResult(
                success=False,
                event_id=event_id,
                intent="inquiry",
                action_taken="quote_agent_failed",
                response_sent=False,
                error=agent_result.error,
            )

        quote_data = agent_result.data or {}
        workflow.logger.info(f"报价生成成功: total={quote_data.get('total_price')}")

        # 2. 检查是否需要审批
        needs_approval = quote_data.get("needs_approval", False)
        total_price = quote_data.get("total_price", 0)

        if needs_approval and total_price > 10000:
            workflow.logger.info(f"金额超过阈值，需要审批: {total_price}")

            # 启动审批子流程
            from app.workflows.definitions.approval import ApprovalWorkflow

            approval_result = await workflow.execute_child_workflow(
                ApprovalWorkflow.run,
                ApprovalRequest(
                    request_id=f"quote-{event_id}",
                    request_type="quote_approval",
                    requester_id="system",
                    requester_name="系统",
                    approver_id="manager",  # TODO: 从配置获取审批人
                    approver_email="manager@example.com",  # TODO: 从配置获取
                    title=f"报价审批 - {metadata.get('subject', '')}",
                    description=f"客户 {input_data.get('user_external_id')} 的询价，金额 {total_price}",
                    amount=total_price,
                    timeout_hours=24,
                ),
                id=f"approval-quote-{event_id}",
            )

            if approval_result.status != ApprovalStatus.APPROVED:
                workflow.logger.warning(f"报价审批未通过: {approval_result.status}")
                return EmailProcessResult(
                    success=False,
                    event_id=event_id,
                    intent="inquiry",
                    action_taken="approval_rejected",
                    response_sent=False,
                    data={"approval_status": approval_result.status.value},
                )

        # 3. 生成报价草稿（不自动发送！需要人工审核）
        # ⚠️ 安全措施：自动回复功能已禁用
        # 报价内容保存在 quote_data 中，等待人工审核后再发送
        reply_content = quote_data.get("reply_content", "")
        workflow.logger.info(f"报价草稿已生成（不自动发送），长度: {len(reply_content)}")

        return EmailProcessResult(
            success=True,
            event_id=event_id,
            intent="inquiry",
            action_taken="quote_draft_created",  # 草稿已创建，待人工审核
            response_sent=False,  # 不自动发送
            data=quote_data,
        )

    async def _handle_order(
        self,
        input_data: dict,
        retry_policy: RetryPolicy,
    ) -> EmailProcessResult:
        """处理订单"""
        workflow.logger.info("处理订单请求")
        event_id = input_data.get("event_id", "")

        # TODO: 实现订单处理逻辑
        # 1. 调用订单 Agent
        # 2. 创建订单
        # 3. 发送确认邮件

        return EmailProcessResult(
            success=True,
            event_id=event_id,
            intent="order",
            action_taken="order_pending",
            response_sent=False,
            data={"message": "订单处理功能待实现"},
        )

    async def _handle_complaint(
        self,
        input_data: dict,
        retry_policy: RetryPolicy,
    ) -> EmailProcessResult:
        """处理投诉"""
        workflow.logger.info("处理投诉请求")
        event_id = input_data.get("event_id", "")
        metadata = input_data.get("metadata", {})

        # 发送通知给管理员
        await workflow.execute_activity(
            "send_notification",
            NotificationRequest(
                type=NotificationType.EMAIL,
                recipient="admin@example.com",  # TODO: 从配置获取
                title=f"[投诉] {metadata.get('subject', '客户投诉')}",
                content=f"收到来自 {input_data.get('user_external_id')} 的投诉：\n\n{input_data.get('content', '')}",
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        return EmailProcessResult(
            success=True,
            event_id=event_id,
            intent="complaint",
            action_taken="escalated",
            response_sent=False,
            data={"message": "已转交管理员处理"},
        )

    async def _handle_follow_up(
        self,
        input_data: dict,
        retry_policy: RetryPolicy,
    ) -> EmailProcessResult:
        """处理跟进"""
        workflow.logger.info("处理跟进请求")
        event_id = input_data.get("event_id", "")

        # TODO: 实现跟进处理逻辑

        return EmailProcessResult(
            success=True,
            event_id=event_id,
            intent="follow_up",
            action_taken="follow_up_pending",
            response_sent=False,
            data={"message": "跟进处理功能待实现"},
        )

    async def _handle_other(
        self,
        input_data: dict,
        retry_policy: RetryPolicy,
    ) -> EmailProcessResult:
        """处理其他类型"""
        workflow.logger.info("处理其他类型请求")
        event_id = input_data.get("event_id", "")
        metadata = input_data.get("metadata", {})

        # 发送通知，需要人工处理
        await workflow.execute_activity(
            "send_notification",
            NotificationRequest(
                type=NotificationType.EMAIL,
                recipient="support@example.com",  # TODO: 从配置获取
                title=f"[待处理] {metadata.get('subject', '新邮件')}",
                content=f"收到来自 {input_data.get('user_external_id')} 的邮件，需要人工处理：\n\n{input_data.get('content', '')}",
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        return EmailProcessResult(
            success=True,
            event_id=event_id,
            intent="other",
            action_taken="manual_review",
            response_sent=False,
            data={"message": "已转交人工处理"},
        )

    # ==================== Query ====================

    @workflow.query
    def get_status(self) -> str:
        """查询当前状态"""
        return self._status

    @workflow.query
    def get_result(self) -> Optional[dict]:
        """查询处理结果"""
        if self._result:
            return {
                "success": self._result.success,
                "intent": self._result.intent,
                "action_taken": self._result.action_taken,
                "response_sent": self._result.response_sent,
            }
        return None
