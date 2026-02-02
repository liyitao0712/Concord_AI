# app/temporal/workflows/work_type_suggestion.py
# 工作类型建议审批工作流
#
# 流程：
# 1. 工作流启动，发送通知给管理员
# 2. 等待审批信号（approve/reject）
# 3. 超时未审批自动拒绝（7天）
# 4. 根据审批结果执行相应操作

import logging
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# 使用 workflow.defn 时，需要导入 activity
with workflow.unsafe.imports_passed_through():
    from app.temporal.activities.work_type import (
        notify_admin_activity,
        approve_suggestion_activity,
        reject_suggestion_activity,
    )

logger = logging.getLogger(__name__)


@workflow.defn
class WorkTypeSuggestionWorkflow:
    """
    工作类型建议审批工作流

    功能：
    - 接收 AI 生成的工作类型建议
    - 通知管理员审批
    - 等待审批信号（最长 7 天）
    - 根据审批结果创建 WorkType 或标记拒绝

    信号：
    - approve(reviewer_id, note): 批准建议
    - reject(reviewer_id, note): 拒绝建议

    查询：
    - get_status(): 获取当前状态
    """

    def __init__(self):
        self._approved: Optional[bool] = None
        self._reviewer_id: Optional[str] = None
        self._review_note: Optional[str] = None

    @workflow.run
    async def run(self, suggestion_id: str) -> dict:
        """
        工作流主逻辑

        Args:
            suggestion_id: WorkTypeSuggestion 的 ID

        Returns:
            dict: 执行结果
        """
        workflow.logger.info(f"开始审批工作流: suggestion_id={suggestion_id}")

        # 1. 发送通知给管理员
        try:
            await workflow.execute_activity(
                notify_admin_activity,
                suggestion_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
            workflow.logger.info("管理员通知已发送")
        except Exception as e:
            workflow.logger.warning(f"发送通知失败（不影响审批流程）: {e}")

        # 2. 等待审批信号（最长等待 7 天）
        try:
            await workflow.wait_condition(
                lambda: self._approved is not None,
                timeout=timedelta(days=7),
            )
        except TimeoutError:
            # 超时未审批，自动拒绝
            workflow.logger.info("审批超时，自动拒绝")
            self._approved = False
            self._review_note = "超时自动拒绝（7天未处理）"

        # 3. 执行审批结果
        if self._approved:
            workflow.logger.info(f"执行批准操作: reviewer={self._reviewer_id}")
            result = await workflow.execute_activity(
                approve_suggestion_activity,
                args=[suggestion_id, self._reviewer_id or "system", self._review_note or ""],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
        else:
            workflow.logger.info(f"执行拒绝操作: reviewer={self._reviewer_id or 'system'}")
            result = await workflow.execute_activity(
                reject_suggestion_activity,
                args=[suggestion_id, self._reviewer_id or "system", self._review_note or ""],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )

        workflow.logger.info(f"审批工作流完成: result={result}")
        return result

    @workflow.signal
    def approve(self, reviewer_id: str, note: str = ""):
        """
        批准信号

        Args:
            reviewer_id: 审批人 ID
            note: 审批备注
        """
        workflow.logger.info(f"收到批准信号: reviewer={reviewer_id}")
        self._approved = True
        self._reviewer_id = reviewer_id
        self._review_note = note

    @workflow.signal
    def reject(self, reviewer_id: str, note: str = ""):
        """
        拒绝信号

        Args:
            reviewer_id: 审批人 ID
            note: 拒绝原因
        """
        workflow.logger.info(f"收到拒绝信号: reviewer={reviewer_id}")
        self._approved = False
        self._reviewer_id = reviewer_id
        self._review_note = note

    @workflow.query
    def get_status(self) -> dict:
        """
        查询当前状态

        Returns:
            dict: 包含 approved, reviewer_id, review_note 的状态字典
        """
        return {
            "approved": self._approved,
            "reviewer_id": self._reviewer_id,
            "review_note": self._review_note,
            "waiting_for_approval": self._approved is None,
        }
