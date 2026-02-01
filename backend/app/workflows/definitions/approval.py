# app/workflows/definitions/approval.py
# 审批工作流定义
#
# 功能说明：
# 这是一个通用的审批工作流，支持：
# 1. 创建审批请求
# 2. 发送通知给审批人
# 3. 等待审批响应（Signal）
# 4. 超时自动拒绝
# 5. 记录审批结果
#
# 使用场景：
# - 订单金额超限审批
# - 合同条款修改审批
# - 特殊折扣申请审批
#
# 工作流流程：
# 1. 收到审批请求
# 2. 记录工作流启动事件
# 3. 发送通知给审批人
# 4. 等待审批结果（或超时）
# 5. 记录审批结果事件
# 6. 返回审批结果

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# 导入共享类型（这些不包含任何非确定性操作）
from app.workflows.types import (
    ApprovalStatus,
    ApprovalRequest,
    ApprovalResult,
    NotificationRequest,
    NotificationType,
    WorkflowEvent,
)


# ==================== Workflow 定义 ====================

@workflow.defn
class ApprovalWorkflow:
    """
    通用审批工作流

    这个 Workflow 处理通用的审批流程：
    1. 接收审批请求
    2. 通知审批人
    3. 等待审批响应或超时
    4. 返回审批结果

    使用方法：
        # 启动工作流
        handle = await client.start_workflow(
            ApprovalWorkflow.run,
            args=(approval_request,),
            id=f"approval-{request_id}",
            task_queue="concord-main-queue",
        )

        # 发送审批通过信号
        await handle.signal(ApprovalWorkflow.approve, approver_id, "同意")

        # 或发送审批拒绝信号
        await handle.signal(ApprovalWorkflow.reject, approver_id, "不同意")

        # 获取结果
        result = await handle.result()
    """

    def __init__(self):
        """初始化 Workflow 状态"""
        # 审批状态
        self._status: ApprovalStatus = ApprovalStatus.PENDING
        # 审批人ID
        self._approver_id: Optional[str] = None
        # 审批意见
        self._comment: Optional[str] = None
        # 审批请求
        self._request: Optional[ApprovalRequest] = None

    # ==================== 主流程 ====================

    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        """
        工作流主函数

        这是工作流的入口点，定义了整个审批流程。

        Args:
            request: 审批请求

        Returns:
            ApprovalResult: 审批结果
        """
        self._request = request
        workflow.logger.info(f"审批工作流启动: {request.request_id}")
        workflow.logger.info(f"  类型: {request.request_type}")
        workflow.logger.info(f"  标题: {request.title}")
        workflow.logger.info(f"  申请人: {request.requester_name}")

        # 定义 Activity 重试策略
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),   # 首次重试间隔
            maximum_interval=timedelta(seconds=30),  # 最大重试间隔
            backoff_coefficient=2.0,                 # 退避系数
            maximum_attempts=3,                      # 最大重试次数
        )

        # 1. 记录工作流启动事件
        await workflow.execute_activity(
            "log_workflow_event",
            WorkflowEvent(
                workflow_id=workflow.info().workflow_id,
                workflow_type="ApprovalWorkflow",
                event_type="started",
                event_data={
                    "request_id": request.request_id,
                    "request_type": request.request_type,
                    "requester_id": request.requester_id,
                },
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        # 2. 发送通知给审批人
        await workflow.execute_activity(
            "send_notification",
            NotificationRequest(
                type=NotificationType.EMAIL,
                recipient=request.approver_email,
                title=f"[待审批] {request.title}",
                content=self._build_notification_content(request),
                metadata={"request_id": request.request_id},
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        workflow.logger.info(f"已发送通知给审批人: {request.approver_email}")

        # 3. 等待审批响应或超时
        timeout = timedelta(hours=request.timeout_hours)
        workflow.logger.info(f"等待审批响应，超时时间: {request.timeout_hours} 小时")

        try:
            # 使用 wait_condition 等待状态变化
            # 如果在超时时间内状态没有变化，会抛出 asyncio.TimeoutError
            await workflow.wait_condition(
                lambda: self._status != ApprovalStatus.PENDING,
                timeout=timeout,
            )
        except TimeoutError:
            # 超时，自动拒绝
            workflow.logger.warning(f"审批超时: {request.request_id}")
            self._status = ApprovalStatus.TIMEOUT

        # 4. 记录审批结果事件
        await workflow.execute_activity(
            "log_workflow_event",
            WorkflowEvent(
                workflow_id=workflow.info().workflow_id,
                workflow_type="ApprovalWorkflow",
                event_type="completed",
                event_data={
                    "request_id": request.request_id,
                    "status": self._status.value,
                    "approver_id": self._approver_id,
                    "comment": self._comment,
                },
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        # 5. 返回审批结果
        result = ApprovalResult(
            request_id=request.request_id,
            status=self._status,
            approver_id=self._approver_id,
            comment=self._comment,
            approved_at=str(workflow.now()) if self._status != ApprovalStatus.PENDING else None,
        )

        workflow.logger.info(f"审批工作流完成: {request.request_id} -> {self._status.value}")
        return result

    # ==================== Signal 处理 ====================

    @workflow.signal
    async def approve(self, approver_id: str, comment: str = "") -> None:
        """
        审批通过信号

        外部调用此方法来通知 Workflow 审批已通过。

        Args:
            approver_id: 审批人ID
            comment: 审批意见
        """
        if self._status != ApprovalStatus.PENDING:
            workflow.logger.warning(f"审批已完成，忽略信号: {self._status}")
            return

        workflow.logger.info(f"收到审批通过信号: {approver_id}")
        self._status = ApprovalStatus.APPROVED
        self._approver_id = approver_id
        self._comment = comment

    @workflow.signal
    async def reject(self, approver_id: str, comment: str = "") -> None:
        """
        审批拒绝信号

        外部调用此方法来通知 Workflow 审批已拒绝。

        Args:
            approver_id: 审批人ID
            comment: 拒绝原因
        """
        if self._status != ApprovalStatus.PENDING:
            workflow.logger.warning(f"审批已完成，忽略信号: {self._status}")
            return

        workflow.logger.info(f"收到审批拒绝信号: {approver_id}")
        self._status = ApprovalStatus.REJECTED
        self._approver_id = approver_id
        self._comment = comment

    @workflow.signal
    async def cancel(self, reason: str = "") -> None:
        """
        取消审批信号

        申请人可以调用此方法取消审批请求。

        Args:
            reason: 取消原因
        """
        if self._status != ApprovalStatus.PENDING:
            workflow.logger.warning(f"审批已完成，无法取消: {self._status}")
            return

        workflow.logger.info(f"收到取消信号: {reason}")
        self._status = ApprovalStatus.CANCELLED
        self._comment = reason

    # ==================== Query 处理 ====================

    @workflow.query
    def get_status(self) -> ApprovalStatus:
        """
        查询当前审批状态

        Query 是只读操作，不会影响 Workflow 执行。

        Returns:
            ApprovalStatus: 当前审批状态
        """
        return self._status

    @workflow.query
    def get_details(self) -> dict:
        """
        查询审批详情

        返回当前审批的完整状态信息。

        Returns:
            dict: 审批详情
        """
        return {
            "request_id": self._request.request_id if self._request else None,
            "status": self._status.value,
            "approver_id": self._approver_id,
            "comment": self._comment,
        }

    # ==================== 辅助方法 ====================

    def _build_notification_content(self, request: ApprovalRequest) -> str:
        """
        构建通知内容

        Args:
            request: 审批请求

        Returns:
            str: 格式化的通知内容
        """
        content = f"""
您有一个新的审批请求需要处理：

申请人：{request.requester_name}
申请类型：{request.request_type}
标题：{request.title}

详情：
{request.description}
"""
        if request.amount is not None:
            content += f"\n涉及金额：¥{request.amount:,.2f}"

        content += f"\n\n请在 {request.timeout_hours} 小时内完成审批，否则将自动拒绝。"
        return content.strip()
