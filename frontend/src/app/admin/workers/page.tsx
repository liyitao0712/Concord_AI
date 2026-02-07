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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Plus, Play, Square, FlaskConical, Pencil, Trash2 } from 'lucide-react';

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
  const confirm = useConfirm();

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
    const confirmed = await confirm({
      title: '删除 Worker',
      description: `确定要删除 Worker "${worker.name}" 吗？`,
      variant: 'destructive',
    });
    if (!confirmed) return;

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

  // 获取状态 Badge variant
  const getStatusBadgeProps = (status: string): { variant: 'default' | 'destructive' | 'secondary'; className?: string } => {
    switch (status) {
      case 'running':
        return { variant: 'default', className: 'bg-green-600' };
      case 'error':
        return { variant: 'destructive' };
      default:
        return { variant: 'secondary' };
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
        <LoadingSpinner size="lg" text="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Worker 管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理消息渠道 Worker（飞书、邮件等）
          </p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-1" />
          添加 Worker
        </Button>
      </div>

      {/* 提示信息 */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4">
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700">{success}</p>
        </div>
      )}

      {/* Worker 列表 */}
      <Card>
        <CardContent className="p-0">
          {workers.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>暂无 Worker 配置</p>
              <p className="text-sm mt-2">点击「添加 Worker」创建第一个渠道</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="px-6">名称</TableHead>
                  <TableHead className="px-6">类型</TableHead>
                  <TableHead className="px-6">Agent</TableHead>
                  <TableHead className="px-6">状态</TableHead>
                  <TableHead className="px-6">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workers.map((worker) => (
                  <TableRow key={worker.id}>
                    <TableCell className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium">{worker.name}</div>
                        <div className="text-sm text-muted-foreground">{worker.config.app_id || '-'}</div>
                      </div>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <span className="text-sm">{getTypeName(worker.worker_type)}</span>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <span className="text-sm text-muted-foreground">{worker.agent_id}</span>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <div className="flex items-center">
                        <Badge {...getStatusBadgeProps(worker.status)}>
                          {getStatusText(worker.status)}
                        </Badge>
                        {worker.pid && (
                          <span className="ml-2 text-xs text-muted-foreground">PID: {worker.pid}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm">
                      <div className="flex space-x-1">
                        {worker.status === 'running' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStop(worker)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Square className="h-4 w-4 mr-1" />
                            停止
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStart(worker)}
                            disabled={!worker.is_enabled}
                            className="text-green-600 hover:text-green-700"
                          >
                            <Play className="h-4 w-4 mr-1" />
                            启动
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTest(worker)}
                        >
                          <FlaskConical className="h-4 w-4 mr-1" />
                          测试
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditModal(worker)}
                        >
                          <Pencil className="h-4 w-4 mr-1" />
                          编辑
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(worker)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 创建/编辑模态框 */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {modalMode === 'create' ? '添加 Worker' : '编辑 Worker'}
            </DialogTitle>
            <DialogDescription>
              {modalMode === 'create' ? '配置新的消息渠道 Worker' : '修改 Worker 配置'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Worker 类型 */}
            <div>
              <Label className="mb-1">类型</Label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                disabled={modalMode === 'edit'}
                className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted disabled:cursor-not-allowed"
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
              <Label className="mb-1">名称</Label>
              <Input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="如：客服机器人"
              />
            </div>

            {/* 飞书配置 */}
            {formType === 'feishu' && (
              <>
                <div>
                  <Label className="mb-1">App ID</Label>
                  <Input
                    type="text"
                    value={formAppId}
                    onChange={(e) => setFormAppId(e.target.value)}
                    placeholder="cli_xxxxxxxx"
                  />
                </div>

                <div>
                  <Label className="mb-1">App Secret</Label>
                  <Input
                    type="password"
                    value={formAppSecret}
                    onChange={(e) => setFormAppSecret(e.target.value)}
                    placeholder={modalMode === 'edit' ? '留空保持不变' : '输入 App Secret'}
                  />
                </div>
              </>
            )}

            {/* Agent */}
            <div>
              <Label className="mb-1">绑定 Agent</Label>
              <select
                value={formAgentId}
                onChange={(e) => setFormAgentId(e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="chat_agent">通用聊天助手</option>
                <option value="email_summarizer">邮件摘要</option>
              </select>
            </div>

            {/* 启用 */}
            <div className="flex items-center space-x-2">
              <Switch
                id="enabled"
                checked={formEnabled}
                onCheckedChange={setFormEnabled}
              />
              <Label htmlFor="enabled">启用</Label>
            </div>

            {/* 描述 */}
            <div>
              <Label className="mb-1">描述（可选）</Label>
              <Textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowModal(false)}
            >
              取消
            </Button>
            <Button onClick={handleSave}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
