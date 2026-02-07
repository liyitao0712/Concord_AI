# app/temporal/workflows/customer_approval.py
# 客户建议审批工作流
#
# 当 CustomerExtractorAgent 从邮件中识别到新客户/新联系人时，启动此工作流。
# 流程：通知管理员 → 等待审批信号（7天超时自动拒绝）→ 执行审批操作
#
# Signals:
#   - approve(reviewer_id, note): 批准建议
#   - reject(reviewer_id, note): 拒绝建议
#
# Queries:
#   - get_status(): 查询当前审批状态

from typing import Optional
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities.customer import (
        notify_admin_customer_activity,
        approve_customer_activity,
        reject_customer_activity,
    )


@workflow.defn
class CustomerApprovalWorkflow:
    """
    客户建议审批工作流

    执行流程：
    1. 发送管理员通知
    2. 等待审批信号（最长 7 天）
    3. 批准 → 创建 Customer + Contact
       拒绝 → 标记为 rejected
       超时 → 自动拒绝
    """

    def __init__(self):
        self._approved: Optional[bool] = None
        self._reviewer_id: Optional[str] = None
        self._review_note: Optional[str] = None

    @workflow.run
    async def run(self, suggestion_id: str) -> dict:
        """
        主工作流逻辑

        Args:
            suggestion_id: CustomerSuggestion 的 ID

        Returns:
            dict: 执行结果
        """
        workflow.logger.info(f"开始客户审批工作流: suggestion_id={suggestion_id}")

        # 1. 通知管理员
        try:
            await workflow.execute_activity(
                notify_admin_customer_activity,
                suggestion_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
            workflow.logger.info("管理员通知已发送")
        except Exception as e:
            workflow.logger.warning(f"发送通知失败: {e}")

        # 2. 等待审批信号（最长 7 天）
        try:
            await workflow.wait_condition(
                lambda: self._approved is not None,
                timeout=timedelta(days=7),
            )
        except TimeoutError:
            workflow.logger.info("审批超时，自动拒绝")
            self._approved = False
            self._review_note = "超时自动拒绝（7天未处理）"

        # 3. 执行审批操作
        if self._approved:
            result = await workflow.execute_activity(
                approve_customer_activity,
                args=[
                    suggestion_id,
                    self._reviewer_id or "system",
                    self._review_note or "",
                ],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
        else:
            result = await workflow.execute_activity(
                reject_customer_activity,
                args=[
                    suggestion_id,
                    self._reviewer_id or "system",
                    self._review_note or "",
                ],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )

        workflow.logger.info(f"客户审批工作流完成: result={result}")
        return result

    @workflow.signal
    def approve(self, reviewer_id: str, note: str = ""):
        """批准信号"""
        workflow.logger.info(f"收到批准信号: reviewer={reviewer_id}")
        self._approved = True
        self._reviewer_id = reviewer_id
        self._review_note = note

    @workflow.signal
    def reject(self, reviewer_id: str, note: str = ""):
        """拒绝信号"""
        workflow.logger.info(f"收到拒绝信号: reviewer={reviewer_id}")
        self._approved = False
        self._reviewer_id = reviewer_id
        self._review_note = note

    @workflow.query
    def get_status(self) -> dict:
        """查询当前审批状态"""
        return {
            "approved": self._approved,
            "reviewer_id": self._reviewer_id,
            "review_note": self._review_note,
            "waiting_for_approval": self._approved is None,
        }
