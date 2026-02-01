// src/app/admin/monitor/page.tsx
// 运行监控页面
//
// 功能说明：
// 1. 显示 Workflow 和 Agent 执行统计
// 2. 只读查看，无增删改操作
// 3. 自动刷新数据

'use client';

import { useState, useEffect } from 'react';
import { monitorApi, MonitorSummary, WorkflowItem, AgentStats } from '@/lib/api';

export default function MonitorPage() {
  const [summary, setSummary] = useState<MonitorSummary | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [agentStats, setAgentStats] = useState<AgentStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载数据
  const loadData = async () => {
    try {
      setError(null);
      const [summaryData, workflowsData, agentsData] = await Promise.all([
        monitorApi.getSummary(),
        monitorApi.getWorkflows({ limit: 20 }),
        monitorApi.getAgentStats(),
      ]);
      setSummary(summaryData);
      setWorkflows(workflowsData);
      setAgentStats(agentsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 每 30 秒自动刷新
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 状态标签颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // 状态显示文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '进行中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  // 格式化时间
  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{error}</p>
        <button
          onClick={loadData}
          className="mt-2 text-sm text-red-600 hover:text-red-800"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">运行监控</h1>
        <button
          onClick={loadData}
          className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded hover:bg-gray-50"
        >
          刷新
        </button>
      </div>

      {/* 统计卡片 */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Workflow 总数 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">工作流总数</div>
            <div className="mt-2 flex items-baseline">
              <div className="text-3xl font-bold text-gray-900">{summary.total_workflows}</div>
              <div className="ml-2 text-sm text-gray-500">
                进行中: {summary.pending_workflows}
              </div>
            </div>
          </div>

          {/* Workflow 完成/失败 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">工作流状态</div>
            <div className="mt-2 flex items-baseline space-x-4">
              <div>
                <span className="text-2xl font-bold text-green-600">{summary.completed_workflows}</span>
                <span className="text-sm text-gray-500 ml-1">完成</span>
              </div>
              <div>
                <span className="text-2xl font-bold text-red-600">{summary.failed_workflows}</span>
                <span className="text-sm text-gray-500 ml-1">失败</span>
              </div>
            </div>
          </div>

          {/* Agent 调用总数 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Agent 调用</div>
            <div className="mt-2 flex items-baseline">
              <div className="text-3xl font-bold text-gray-900">{summary.total_agent_calls}</div>
              <div className="ml-2 text-sm text-gray-500">
                今日: {summary.today_agent_calls}
              </div>
            </div>
          </div>

          {/* Agent 成功率 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Agent 成功率</div>
            <div className="mt-2">
              <div className="text-3xl font-bold text-blue-600">{summary.agent_success_rate}%</div>
            </div>
          </div>
        </div>
      )}

      {/* 两栏布局：Workflow 列表 + Agent 统计 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workflow 列表 */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">最近工作流</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {workflows.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                暂无工作流记录
              </div>
            ) : (
              workflows.map((workflow) => (
                <div key={workflow.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {workflow.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {workflow.workflow_id}
                      </p>
                    </div>
                    <span className={`ml-2 px-2 py-1 text-xs font-medium rounded ${getStatusColor(workflow.status)}`}>
                      {getStatusText(workflow.status)}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    开始: {formatTime(workflow.started_at)}
                    {workflow.completed_at && (
                      <span className="ml-4">完成: {formatTime(workflow.completed_at)}</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Agent 统计 */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Agent 调用统计</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Agent
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    调用
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    成功
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    平均耗时
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {agentStats.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                      暂无 Agent 调用记录
                    </td>
                  </tr>
                ) : (
                  agentStats.map((stat) => (
                    <tr key={stat.agent_name}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-gray-900">
                          {stat.agent_name}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {stat.total_calls}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span className="text-sm text-green-600">{stat.success_count}</span>
                        {stat.fail_count > 0 && (
                          <span className="text-sm text-red-600 ml-1">/ {stat.fail_count}</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                        {stat.avg_time_ms > 0 ? `${stat.avg_time_ms}ms` : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
