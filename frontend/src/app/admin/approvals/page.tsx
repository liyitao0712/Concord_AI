// src/app/admin/approvals/page.tsx
// 审批管理页面
//
// 功能说明：
// 1. 显示待审批和已审批列表
// 2. 支持通过/拒绝操作
// 3. 查看审批详情

'use client';

import { useState, useEffect, useCallback } from 'react';
import { monitorApi, workflowApi, WorkflowItem } from '@/lib/api';
import { Modal } from '@/components/Modal';

// 状态标签颜色映射
const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
};

// 状态中文名称
const statusNames: Record<string, string> = {
  pending: '待审批',
  running: '处理中',
  completed: '已完成',
  approved: '已通过',
  rejected: '已拒绝',
  failed: '失败',
  cancelled: '已取消',
};

export default function ApprovalsPage() {
  // 列表状态
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<string>('pending');

  // 模态框状态
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowItem | null>(null);

  // 表单状态
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 加载工作流列表
  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const data = await monitorApi.getWorkflows({
        limit: 50,
        status: statusFilter || undefined,
      });
      setWorkflows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  // 打开详情模态框
  const openDetailModal = (workflow: WorkflowItem) => {
    setSelectedWorkflow(workflow);
    setShowDetailModal(true);
  };

  // 打开通过模态框
  const openApproveModal = (workflow: WorkflowItem) => {
    setSelectedWorkflow(workflow);
    setComment('');
    setShowApproveModal(true);
  };

  // 打开拒绝模态框
  const openRejectModal = (workflow: WorkflowItem) => {
    setSelectedWorkflow(workflow);
    setComment('');
    setShowRejectModal(true);
  };

  // 审批通过
  const handleApprove = async () => {
    if (!selectedWorkflow) return;

    setSubmitting(true);
    try {
      await workflowApi.approve(selectedWorkflow.workflow_id, comment || undefined);
      setShowApproveModal(false);
      setSelectedWorkflow(null);
      setComment('');
      loadWorkflows();
    } catch (err) {
      alert(err instanceof Error ? err.message : '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 审批拒绝
  const handleReject = async () => {
    if (!selectedWorkflow) return;

    if (!comment.trim()) {
      alert('请输入拒绝原因');
      return;
    }

    setSubmitting(true);
    try {
      await workflowApi.reject(selectedWorkflow.workflow_id, comment);
      setShowRejectModal(false);
      setSelectedWorkflow(null);
      setComment('');
      loadWorkflows();
    } catch (err) {
      alert(err instanceof Error ? err.message : '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 取消工作流
  const handleCancel = async (workflow: WorkflowItem) => {
    if (!confirm('确定要取消此工作流吗？')) return;

    try {
      await workflowApi.cancel(workflow.workflow_id);
      loadWorkflows();
    } catch (err) {
      alert(err instanceof Error ? err.message : '取消失败');
    }
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">审批管理</h1>
          <p className="mt-1 text-sm text-gray-500">管理工作流审批请求</p>
        </div>
        <button
          onClick={loadWorkflows}
          className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          刷新
        </button>
      </div>

      {/* 筛选 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">状态筛选：</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">全部</option>
            <option value="pending">待审批</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 审批表格 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                工作流
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                类型
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建时间
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  <div className="flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mr-2" />
                    加载中...
                  </div>
                </td>
              </tr>
            ) : workflows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  暂无审批记录
                </td>
              </tr>
            ) : (
              workflows.map((workflow) => (
                <tr key={workflow.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {workflow.title || workflow.workflow_id}
                      </div>
                      <div className="text-xs text-gray-500">
                        {workflow.workflow_id}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">
                      {workflow.workflow_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        statusColors[workflow.status] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {statusNames[workflow.status] || workflow.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(workflow.started_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => openDetailModal(workflow)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      详情
                    </button>
                    {workflow.status === 'pending' && (
                      <>
                        <button
                          onClick={() => openApproveModal(workflow)}
                          className="text-green-600 hover:text-green-900"
                        >
                          通过
                        </button>
                        <button
                          onClick={() => openRejectModal(workflow)}
                          className="text-red-600 hover:text-red-900"
                        >
                          拒绝
                        </button>
                        <button
                          onClick={() => handleCancel(workflow)}
                          className="text-yellow-600 hover:text-yellow-900"
                        >
                          取消
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 详情模态框 */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title="审批详情"
        size="lg"
      >
        {selectedWorkflow && (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">工作流 ID</dt>
                <dd className="mt-1 text-sm text-gray-900 break-all">
                  {selectedWorkflow.workflow_id}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">类型</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {selectedWorkflow.workflow_type}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">标题</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {selectedWorkflow.title || '-'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">状态</dt>
                <dd className="mt-1">
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      statusColors[selectedWorkflow.status] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {statusNames[selectedWorkflow.status] || selectedWorkflow.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">创建时间</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(selectedWorkflow.started_at).toLocaleString('zh-CN')}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">完成时间</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {selectedWorkflow.completed_at
                    ? new Date(selectedWorkflow.completed_at).toLocaleString('zh-CN')
                    : '-'}
                </dd>
              </div>
            </dl>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                关闭
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* 通过模态框 */}
      <Modal
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        title="审批通过"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            确定要通过 <strong>{selectedWorkflow?.title || selectedWorkflow?.workflow_id}</strong> 吗？
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              审批意见（可选）
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入审批意见..."
            />
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              onClick={() => setShowApproveModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleApprove}
              disabled={submitting}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {submitting ? '处理中...' : '确认通过'}
            </button>
          </div>
        </div>
      </Modal>

      {/* 拒绝模态框 */}
      <Modal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        title="审批拒绝"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            确定要拒绝 <strong>{selectedWorkflow?.title || selectedWorkflow?.workflow_id}</strong> 吗？
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              拒绝原因 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入拒绝原因..."
            />
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              onClick={() => setShowRejectModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleReject}
              disabled={submitting || !comment.trim()}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {submitting ? '处理中...' : '确认拒绝'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
