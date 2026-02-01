// src/app/admin/workers/page.tsx
// Worker 管理页面
//
// 功能说明：
// 1. 列出所有 Worker 配置
// 2. 添加/编辑/删除 Worker
// 3. 启动/停止/重启 Worker
// 4. 测试连接

'use client';

import { useState, useEffect } from 'react';

// Worker 配置类型
interface WorkerConfig {
  id: string;
  worker_type: string;
  name: string;
  config: Record<string, string>;
  agent_id: string;
  is_enabled: boolean;
  description: string | null;
  status: string;
  pid: number | null;
  started_at: string | null;
  created_at: string;
  updated_at: string;
}

// Worker 类型信息
interface WorkerTypeInfo {
  type: string;
  name: string;
  description: string;
  required_fields: string[];
  optional_fields: string[];
}

// API 基础 URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API 请求函数
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(error.detail || '请求失败');
  }

  return response.json();
}

// Worker API
const workerApi = {
  list: () => request<WorkerConfig[]>('/admin/workers'),
  getTypes: () => request<WorkerTypeInfo[]>('/admin/workers/types'),
  create: (data: any) => request<WorkerConfig>('/admin/workers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: any) => request<WorkerConfig>(`/admin/workers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => request<any>(`/admin/workers/${id}`, {
    method: 'DELETE',
  }),
  start: (id: string) => request<{ success: boolean; message: string }>(`/admin/workers/${id}/start`, {
    method: 'POST',
  }),
  stop: (id: string) => request<{ success: boolean; message: string }>(`/admin/workers/${id}/stop`, {
    method: 'POST',
  }),
  restart: (id: string) => request<{ success: boolean; message: string }>(`/admin/workers/${id}/restart`, {
    method: 'POST',
  }),
  test: (id: string) => request<{ success: boolean; message: string }>(`/admin/workers/${id}/test`, {
    method: 'POST',
  }),
};

export default function WorkersPage() {
  const [workers, setWorkers] = useState<WorkerConfig[]>([]);
  const [workerTypes, setWorkerTypes] = useState<WorkerTypeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 模态框状态
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingWorker, setEditingWorker] = useState<WorkerConfig | null>(null);

  // 表单状态
  const [formType, setFormType] = useState('feishu');
  const [formName, setFormName] = useState('');
  const [formAppId, setFormAppId] = useState('');
  const [formAppSecret, setFormAppSecret] = useState('');
  const [formAgentId, setFormAgentId] = useState('chat_agent');
  const [formEnabled, setFormEnabled] = useState(true);
  const [formDescription, setFormDescription] = useState('');

  // 加载数据
  const loadData = async () => {
    try {
      setError(null);
      const [workersData, typesData] = await Promise.all([
        workerApi.list(),
        workerApi.getTypes(),
      ]);
      setWorkers(workersData);
      setWorkerTypes(typesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 每 10 秒刷新状态
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  // 打开创建模态框
  const openCreateModal = () => {
    setModalMode('create');
    setEditingWorker(null);
    setFormType('feishu');
    setFormName('');
    setFormAppId('');
    setFormAppSecret('');
    setFormAgentId('chat_agent');
    setFormEnabled(true);
    setFormDescription('');
    setShowModal(true);
  };

  // 打开编辑模态框
  const openEditModal = (worker: WorkerConfig) => {
    setModalMode('edit');
    setEditingWorker(worker);
    setFormType(worker.worker_type);
    setFormName(worker.name);
    setFormAppId(worker.config.app_id || '');
    setFormAppSecret('');
    setFormAgentId(worker.agent_id);
    setFormEnabled(worker.is_enabled);
    setFormDescription(worker.description || '');
    setShowModal(true);
  };

  // 保存 Worker
  const handleSave = async () => {
    try {
      setError(null);

      const config: Record<string, string> = {};
      if (formAppId) config.app_id = formAppId;
      if (formAppSecret) config.app_secret = formAppSecret;

      const data = {
        worker_type: formType,
        name: formName,
        config,
        agent_id: formAgentId,
        is_enabled: formEnabled,
        description: formDescription || null,
      };

      if (modalMode === 'create') {
        await workerApi.create(data);
        setSuccess('Worker 创建成功');
      } else if (editingWorker) {
        await workerApi.update(editingWorker.id, data);
        setSuccess('Worker 更新成功');
      }

      setShowModal(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    }
  };

  // 删除 Worker
  const handleDelete = async (worker: WorkerConfig) => {
    if (!confirm(`确定要删除 Worker "${worker.name}" 吗？`)) return;

    try {
      setError(null);
      await workerApi.delete(worker.id);
      setSuccess('Worker 已删除');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  // 启动 Worker
  const handleStart = async (worker: WorkerConfig) => {
    try {
      setError(null);
      const result = await workerApi.start(worker.id);
      if (result.success) {
        setSuccess(result.message);
      } else {
        setError(result.message);
      }
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动失败');
    }
  };

  // 停止 Worker
  const handleStop = async (worker: WorkerConfig) => {
    try {
      setError(null);
      const result = await workerApi.stop(worker.id);
      if (result.success) {
        setSuccess(result.message);
      } else {
        setError(result.message);
      }
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : '停止失败');
    }
  };

  // 测试连接
  const handleTest = async (worker: WorkerConfig) => {
    try {
      setError(null);
      const result = await workerApi.test(worker.id);
      if (result.success) {
        setSuccess(`连接测试成功: ${result.message}`);
      } else {
        setError(`连接测试失败: ${result.message}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '测试失败');
    }
  };

  // 获取状态样式
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'running':
        return '运行中';
      case 'starting':
        return '启动中';
      case 'stopping':
        return '停止中';
      case 'error':
        return '错误';
      default:
        return '已停止';
    }
  };

  // 获取 Worker 类型名称
  const getTypeName = (type: string) => {
    const typeInfo = workerTypes.find(t => t.type === type);
    return typeInfo?.name || type;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Worker 管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            管理消息渠道 Worker（飞书、邮件等）
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          + 添加 Worker
        </button>
      </div>

      {/* 提示信息 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700">{success}</p>
        </div>
      )}

      {/* Worker 列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {workers.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p>暂无 Worker 配置</p>
            <p className="text-sm mt-2">点击「添加 Worker」创建第一个渠道</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  类型
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {workers.map((worker) => (
                <tr key={worker.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{worker.name}</div>
                      <div className="text-sm text-gray-500">{worker.config.app_id || '-'}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-900">{getTypeName(worker.worker_type)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">{worker.agent_id}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusStyle(worker.status)}`}>
                        {getStatusText(worker.status)}
                      </span>
                      {worker.pid && (
                        <span className="ml-2 text-xs text-gray-500">PID: {worker.pid}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex space-x-2">
                      {worker.status === 'running' ? (
                        <button
                          onClick={() => handleStop(worker)}
                          className="text-red-600 hover:text-red-800"
                        >
                          停止
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStart(worker)}
                          className="text-green-600 hover:text-green-800"
                          disabled={!worker.is_enabled}
                        >
                          启动
                        </button>
                      )}
                      <button
                        onClick={() => handleTest(worker)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        测试
                      </button>
                      <button
                        onClick={() => openEditModal(worker)}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(worker)}
                        className="text-red-600 hover:text-red-800"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 创建/编辑模态框 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">
                {modalMode === 'create' ? '添加 Worker' : '编辑 Worker'}
              </h2>
            </div>

            <div className="px-6 py-4 space-y-4">
              {/* Worker 类型 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  类型
                </label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  disabled={modalMode === 'edit'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  {workerTypes.map((type) => (
                    <option key={type.type} value={type.type}>
                      {type.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  名称
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="如：客服机器人"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* 飞书配置 */}
              {formType === 'feishu' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      App ID
                    </label>
                    <input
                      type="text"
                      value={formAppId}
                      onChange={(e) => setFormAppId(e.target.value)}
                      placeholder="cli_xxxxxxxx"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      App Secret
                    </label>
                    <input
                      type="password"
                      value={formAppSecret}
                      onChange={(e) => setFormAppSecret(e.target.value)}
                      placeholder={modalMode === 'edit' ? '留空保持不变' : '输入 App Secret'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}

              {/* Agent */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  绑定 Agent
                </label>
                <select
                  value={formAgentId}
                  onChange={(e) => setFormAgentId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="chat_agent">通用聊天助手</option>
                  <option value="email_analyzer">邮件分析</option>
                  <option value="intent_classifier">意图分类</option>
                  <option value="quote_agent">报价助手</option>
                </select>
              </div>

              {/* 启用 */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="enabled"
                  checked={formEnabled}
                  onChange={(e) => setFormEnabled(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="enabled" className="ml-2 text-sm text-gray-700">
                  启用
                </label>
              </div>

              {/* 描述 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  描述（可选）
                </label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 使用说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-800 mb-2">使用说明</h3>
        <ul className="text-sm text-blue-700 list-disc list-inside space-y-1">
          <li>每个 Worker 对应一个消息渠道（如一个飞书机器人）</li>
          <li>可以创建多个同类型的 Worker 连接不同的应用</li>
          <li>每个 Worker 可以绑定不同的 Agent 实现差异化处理</li>
          <li>启用的 Worker 会在服务启动时自动运行</li>
        </ul>
      </div>
    </div>
  );
}
