'use client';

// 项目管理面板组件
// 可嵌入工作台 Tab 或作为独立页面使用

import { useEffect, useState, useCallback } from 'react';
import {
  projectsApi, tasksApi, progressApi, customersApi, suppliersApi,
  type Project, type ProjectDetail, type ProjectCreate, type ProjectUpdate,
  type TaskItem, type TaskCreate, type TaskUpdate,
  type ProgressEntry, type ProgressCreate,
  type Customer, type Supplier, type ProjectAssociation,
} from '@/lib/api';
import { useConfirm } from '@/components/ConfirmProvider';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Plus, Search, Pencil, Trash2, Eye, ChevronLeft, ChevronRight,
  FolderKanban, ListChecks, Clock, MessageSquare, ArrowRight, X, Link2,
} from 'lucide-react';
import { usePermission } from '@/hooks/usePermission';

// ==================== 常量 ====================

const PROJECT_STATUSES: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-800' },
  active: { label: '进行中', color: 'bg-blue-100 text-blue-800' },
  on_hold: { label: '暂停', color: 'bg-yellow-100 text-yellow-800' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
  cancelled: { label: '已取消', color: 'bg-red-100 text-red-800' },
};

const PRIORITIES: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: 'bg-slate-100 text-slate-700' },
  medium: { label: '中', color: 'bg-blue-100 text-blue-700' },
  high: { label: '高', color: 'bg-orange-100 text-orange-700' },
  urgent: { label: '紧急', color: 'bg-red-100 text-red-700' },
};

const TASK_STATUSES: Record<string, { label: string; color: string }> = {
  pending: { label: '待办', color: 'bg-gray-100 text-gray-800' },
  in_progress: { label: '进行中', color: 'bg-blue-100 text-blue-800' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
  cancelled: { label: '已取消', color: 'bg-red-100 text-red-800' },
};

const PROGRESS_TYPES: Record<string, { label: string; icon: typeof Clock }> = {
  status_update: { label: '状态变更', icon: ArrowRight },
  completion: { label: '进度更新', icon: ListChecks },
  communication: { label: '沟通记录', icon: MessageSquare },
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  customer: '客户',
  supplier: '供应商',
  purchase_contract: '采购合同',
  sales_contract: '销售合同',
  product: '产品',
  inbound_order: '入仓单',
  outbound_order: '出仓单',
  client_rfq: '客户询价',
  quotation: '报价单',
  supplier_rfq: '供应商询价',
  supplier_quotation: '供应商报价',
};

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN');
}

// ==================== 项目表单 ====================

function ProjectForm({
  initial,
  initialAssociations,
  onSubmit,
  onCancel,
  loading,
}: {
  initial?: Partial<ProjectCreate>;
  initialAssociations?: { entity_type: string; entity_id: string }[];
  onSubmit: (data: ProjectCreate | ProjectUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<ProjectCreate>({
    name: initial?.name || '',
    project_type: initial?.project_type || 'general',
    description: initial?.description || '',
    status: initial?.status || 'draft',
    priority: initial?.priority || 'medium',
    start_date: initial?.start_date || '',
    due_date: initial?.due_date || '',
    tags: initial?.tags || [],
    notes: initial?.notes || '',
    associations: initialAssociations || [],
  });
  const [tagInput, setTagInput] = useState('');

  // 加载客户和供应商列表
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  useEffect(() => {
    customersApi.list({ page_size: 100 }).then(res => setCustomers(res.items)).catch(console.error);
    suppliersApi.list({ page_size: 100 }).then(res => setSuppliers(res.items)).catch(console.error);
  }, []);

  // 已选中的客户/供应商 ID
  const selectedCustomerIds = (form.associations || []).filter(a => a.entity_type === 'customer').map(a => a.entity_id);
  const selectedSupplierIds = (form.associations || []).filter(a => a.entity_type === 'supplier').map(a => a.entity_id);

  const toggleAssociation = (entityType: string, entityId: string) => {
    const assocs = form.associations || [];
    const exists = assocs.find(a => a.entity_type === entityType && a.entity_id === entityId);
    if (exists) {
      setForm({ ...form, associations: assocs.filter(a => !(a.entity_type === entityType && a.entity_id === entityId)) });
    } else {
      setForm({ ...form, associations: [...assocs, { entity_type: entityType, entity_id: entityId }] });
    }
  };

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.tags!.includes(tag)) {
      setForm({ ...form, tags: [...(form.tags || []), tag] });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setForm({ ...form, tags: (form.tags || []).filter(t => t !== tag) });
  };

  const handleSubmit = () => {
    if (!form.name.trim()) return;
    // 清理空字段
    const cleaned: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(form)) {
      if (value !== '' && value !== null && value !== undefined) {
        cleaned[key] = value;
      }
    }
    onSubmit(cleaned as unknown as ProjectCreate);
  };

  const selectClass = 'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label>项目名称 *</Label>
          <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="输入项目名称" />
        </div>
        <div>
          <Label>项目类型</Label>
          <select className={selectClass} value={form.project_type} onChange={e => setForm({ ...form, project_type: e.target.value })}>
            <option value="general">通用</option>
            <option value="research">研发</option>
            <option value="order">订单</option>
            <option value="purchase">采购</option>
            <option value="sales">销售</option>
          </select>
        </div>
        <div>
          <Label>状态</Label>
          <select className={selectClass} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
            {Object.entries(PROJECT_STATUSES).map(([v, { label }]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>优先级</Label>
          <select className={selectClass} value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
            {Object.entries(PRIORITIES).map(([v, { label }]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>开始日期</Label>
          <Input type="date" value={form.start_date || ''} onChange={e => setForm({ ...form, start_date: e.target.value })} />
        </div>
        <div>
          <Label>截止日期</Label>
          <Input type="date" value={form.due_date || ''} onChange={e => setForm({ ...form, due_date: e.target.value })} />
        </div>
      </div>

      {/* 关联客户（多选） */}
      <div>
        <Label>关联客户</Label>
        <div className="border rounded-md p-2 max-h-32 overflow-y-auto mt-1">
          {customers.length === 0 ? (
            <span className="text-sm text-muted-foreground">加载中...</span>
          ) : customers.map(c => (
            <label key={c.id} className="flex items-center gap-2 py-1 px-1 hover:bg-muted/50 rounded cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={selectedCustomerIds.includes(c.id)}
                onChange={() => toggleAssociation('customer', c.id)}
                className="rounded"
              />
              {c.name}
            </label>
          ))}
        </div>
      </div>

      {/* 关联供应商（多选） */}
      <div>
        <Label>关联供应商</Label>
        <div className="border rounded-md p-2 max-h-32 overflow-y-auto mt-1">
          {suppliers.length === 0 ? (
            <span className="text-sm text-muted-foreground">加载中...</span>
          ) : suppliers.map(s => (
            <label key={s.id} className="flex items-center gap-2 py-1 px-1 hover:bg-muted/50 rounded cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={selectedSupplierIds.includes(s.id)}
                onChange={() => toggleAssociation('supplier', s.id)}
                className="rounded"
              />
              {s.name}
            </label>
          ))}
        </div>
      </div>

      <div>
        <Label>描述</Label>
        <Textarea rows={3} value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="项目描述" />
      </div>
      <div>
        <Label>标签</Label>
        <div className="flex gap-2 mt-1">
          <Input value={tagInput} onChange={e => setTagInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())} placeholder="输入标签" className="flex-1" />
          <Button type="button" variant="outline" size="sm" onClick={addTag}>添加</Button>
        </div>
        {form.tags && form.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {form.tags.map(tag => (
              <Badge key={tag} variant="secondary" className="cursor-pointer" onClick={() => removeTag(tag)}>{tag} x</Badge>
            ))}
          </div>
        )}
      </div>
      <div>
        <Label>备注</Label>
        <Textarea rows={2} value={form.notes || ''} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="备注" />
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel} disabled={loading}>取消</Button>
        <Button onClick={handleSubmit} disabled={loading || !form.name.trim()}>
          {loading ? '保存中...' : '保存'}
        </Button>
      </DialogFooter>
    </div>
  );
}

// ==================== 任务表单 ====================

function TaskForm({
  projectId,
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  projectId: string;
  initial?: Partial<TaskItem>;
  onSubmit: (data: TaskCreate | TaskUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<TaskCreate>({
    project_id: projectId,
    title: initial?.title || '',
    description: initial?.description || '',
    task_type: initial?.task_type || 'action',
    phase_name: initial?.phase_name || '',
    status: initial?.status || 'pending',
    priority: initial?.priority || 'medium',
    completion_percentage: initial?.completion_percentage ?? 0,
    due_date: initial?.due_date ?? '',
  });

  const selectClass = 'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

  const handleSubmit = () => {
    if (!form.title.trim()) return;
    const cleaned: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(form)) {
      if (value !== '' && value !== null && value !== undefined) {
        cleaned[key] = value;
      }
    }
    onSubmit(cleaned as unknown as TaskCreate);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <Label>任务标题 *</Label>
          <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="输入任务标题" />
        </div>
        <div>
          <Label>任务类型</Label>
          <select className={selectClass} value={form.task_type} onChange={e => setForm({ ...form, task_type: e.target.value })}>
            <option value="action">具体任务</option>
            <option value="milestone">里程碑</option>
          </select>
        </div>
        {form.task_type === 'milestone' && (
          <div>
            <Label>阶段名称</Label>
            <Input value={form.phase_name || ''} onChange={e => setForm({ ...form, phase_name: e.target.value })} placeholder="如：报价阶段" />
          </div>
        )}
        <div>
          <Label>状态</Label>
          <select className={selectClass} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
            {Object.entries(TASK_STATUSES).map(([v, { label }]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>优先级</Label>
          <select className={selectClass} value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
            {Object.entries(PRIORITIES).map(([v, { label }]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>完成度 ({form.completion_percentage}%)</Label>
          <Input type="range" min={0} max={100} value={form.completion_percentage} onChange={e => setForm({ ...form, completion_percentage: Number(e.target.value) })} />
        </div>
        <div>
          <Label>截止日期</Label>
          <Input type="date" value={form.due_date || ''} onChange={e => setForm({ ...form, due_date: e.target.value })} />
        </div>
      </div>
      <div>
        <Label>描述</Label>
        <Textarea rows={3} value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="任务描述" />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel} disabled={loading}>取消</Button>
        <Button onClick={handleSubmit} disabled={loading || !form.title.trim()}>
          {loading ? '保存中...' : '保存'}
        </Button>
      </div>
    </div>
  );
}

// ==================== 进度时间线 ====================

function ProgressTimeline({
  taskId,
  entries,
  onAdd,
  onDelete,
  loading,
}: {
  taskId: string;
  entries: ProgressEntry[];
  onAdd: (data: ProgressCreate) => void;
  onDelete: (id: string) => void;
  loading: boolean;
}) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProgressCreate>({
    task_id: taskId,
    progress_type: 'communication',
    content: '',
  });

  const selectClass = 'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

  const handleSubmit = () => {
    if (!form.content?.trim()) return;
    onAdd(form);
    setForm({ task_id: taskId, progress_type: 'communication', content: '' });
    setShowForm(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium">进度记录</h4>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-3 w-3 mr-1" />添加
        </Button>
      </div>

      {showForm && (
        <div className="border rounded-lg p-3 space-y-2 bg-muted/30">
          <select className={selectClass} value={form.progress_type} onChange={e => setForm({ ...form, progress_type: e.target.value })}>
            <option value="communication">沟通记录</option>
            <option value="status_update">状态变更</option>
            <option value="completion">进度更新</option>
          </select>
          <Textarea rows={2} value={form.content || ''} onChange={e => setForm({ ...form, content: e.target.value })} placeholder="输入内容..." />
          {form.progress_type === 'completion' && (
            <Input type="number" min={0} max={100} value={form.percentage ?? ''} onChange={e => setForm({ ...form, percentage: Number(e.target.value) })} placeholder="完成百分比" />
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowForm(false)}>取消</Button>
            <Button size="sm" onClick={handleSubmit} disabled={loading || !form.content?.trim()}>
              {loading ? '保存中...' : '添加'}
            </Button>
          </div>
        </div>
      )}

      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4">暂无进度记录</p>
      ) : (
        <div className="space-y-2">
          {entries.map(entry => {
            const typeInfo = PROGRESS_TYPES[entry.progress_type] || PROGRESS_TYPES.communication;
            const Icon = typeInfo.icon;
            return (
              <div key={entry.id} className="flex gap-3 p-2 rounded-lg hover:bg-muted/50 group">
                <div className="mt-0.5">
                  <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center">
                    <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{typeInfo.label}</Badge>
                    <span className="text-xs text-muted-foreground">{formatDateTime(entry.created_at)}</span>
                    {entry.created_by_name && (
                      <span className="text-xs text-muted-foreground">- {entry.created_by_name}</span>
                    )}
                    <Button variant="ghost" size="sm" className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 ml-auto" onClick={() => onDelete(entry.id)}>
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </div>
                  {entry.content && <p className="text-sm mt-1">{entry.content}</p>}
                  {entry.percentage !== null && (
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1.5 bg-muted rounded-full">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${entry.percentage}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground">{entry.percentage}%</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ==================== 项目详情弹窗 ====================

function ProjectDetailModal({
  project,
  isOpen,
  onClose,
  onRefresh,
}: {
  project: ProjectDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onRefresh?: () => void;
}) {
  const confirm = useConfirm();
  const { can } = usePermission();
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState<TaskItem | null>(null);
  const [taskSaving, setTaskSaving] = useState(false);
  // 任务详情展开
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [progressEntries, setProgressEntries] = useState<ProgressEntry[]>([]);
  const [progressLoading, setProgressLoading] = useState(false);

  const loadTasks = useCallback(async () => {
    if (!project) return;
    setTasksLoading(true);
    try {
      const res = await tasksApi.list({ project_id: project.id, page_size: 100 });
      setTasks(res.items);
    } catch (e) {
      console.error('加载任务失败:', e);
    } finally {
      setTasksLoading(false);
    }
  }, [project]);

  useEffect(() => {
    if (isOpen && project) {
      loadTasks();
      setExpandedTaskId(null);
      setShowTaskForm(false);
      setEditingTask(null);
    }
  }, [isOpen, project, loadTasks]);

  const loadProgress = useCallback(async (taskId: string) => {
    setProgressLoading(true);
    try {
      const res = await progressApi.list({ task_id: taskId, page_size: 100 });
      setProgressEntries(res.items);
    } catch (e) {
      console.error('加载进度失败:', e);
    } finally {
      setProgressLoading(false);
    }
  }, []);

  const toggleTaskExpand = (taskId: string) => {
    if (expandedTaskId === taskId) {
      setExpandedTaskId(null);
    } else {
      setExpandedTaskId(taskId);
      loadProgress(taskId);
    }
  };

  const handleCreateTask = async (data: TaskCreate | TaskUpdate) => {
    setTaskSaving(true);
    try {
      await tasksApi.create(data as TaskCreate);
      setShowTaskForm(false);
      loadTasks();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setTaskSaving(false);
    }
  };

  const handleUpdateTask = async (data: TaskCreate | TaskUpdate) => {
    if (!editingTask) return;
    setTaskSaving(true);
    try {
      await tasksApi.update(editingTask.id, data as TaskUpdate);
      setEditingTask(null);
      loadTasks();
      if (expandedTaskId === editingTask.id) loadProgress(editingTask.id);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setTaskSaving(false);
    }
  };

  const handleDeleteTask = async (task: TaskItem) => {
    const confirmed = await confirm({
      title: '删除任务',
      description: `确定要删除「${task.title}」吗？子任务和进度记录也会被删除。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await tasksApi.delete(task.id);
      loadTasks();
      if (expandedTaskId === task.id) setExpandedTaskId(null);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddProgress = async (data: ProgressCreate) => {
    setProgressLoading(true);
    try {
      await progressApi.create(data);
      if (expandedTaskId) loadProgress(expandedTaskId);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setProgressLoading(false);
    }
  };

  const handleDeleteProgress = async (id: string) => {
    const confirmed = await confirm({
      title: '删除进度记录',
      description: '确定要删除这条记录吗？',
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await progressApi.delete(id);
      if (expandedTaskId) loadProgress(expandedTaskId);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleRemoveAssociation = async (assoc: ProjectAssociation) => {
    if (!project) return;
    const label = assoc.entity_name || assoc.entity_id;
    const confirmed = await confirm({
      title: '移除关联',
      description: `确定要移除「${label}」的关联吗？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await projectsApi.removeAssociation(project.id, assoc.id);
      onRefresh?.();
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (!project) return null;

  // 按 entity_type 分组关联
  const groupedAssociations = (project.associations || []).reduce((groups, assoc) => {
    const key = assoc.entity_type;
    if (!groups[key]) groups[key] = [];
    groups[key].push(assoc);
    return groups;
  }, {} as Record<string, ProjectAssociation[]>);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5" />
            {project.name}
          </DialogTitle>
        </DialogHeader>

        {/* 项目基本信息 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">类型: </span>
            <span>{project.project_type}</span>
          </div>
          <div>
            <span className="text-muted-foreground">状态: </span>
            <Badge className={PROJECT_STATUSES[project.status]?.color || ''}>
              {PROJECT_STATUSES[project.status]?.label || project.status}
            </Badge>
          </div>
          <div>
            <span className="text-muted-foreground">优先级: </span>
            <Badge className={PRIORITIES[project.priority]?.color || ''}>
              {PRIORITIES[project.priority]?.label || project.priority}
            </Badge>
          </div>
          <div>
            <span className="text-muted-foreground">负责人: </span>
            <span>{project.owner_name || '-'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">开始: </span>
            <span>{formatDate(project.start_date)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">截止: </span>
            <span>{formatDate(project.due_date)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">创建: </span>
            <span>{formatDateTime(project.created_at)}</span>
          </div>
        </div>

        {project.description && (
          <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">{project.description}</p>
        )}

        {project.tags && project.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {project.tags.map(tag => <Badge key={tag} variant="outline">{tag}</Badge>)}
          </div>
        )}

        {/* 关联实体 */}
        {project.associations && project.associations.length > 0 && (
          <>
            <Separator />
            <div>
              <h3 className="text-base font-semibold flex items-center gap-2 mb-3">
                <Link2 className="h-4 w-4" /> 关联实体 ({project.associations.length})
              </h3>
              <div className="space-y-2">
                {Object.entries(groupedAssociations).map(([entityType, assocs]) => (
                  <div key={entityType} className="border rounded-lg p-3">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">
                      {ENTITY_TYPE_LABELS[entityType] || entityType}
                    </h4>
                    <div className="space-y-1">
                      {assocs.map(assoc => (
                        <div key={assoc.id} className="flex items-center justify-between py-1 px-2 rounded hover:bg-muted/30 group">
                          <span className="text-sm">{assoc.entity_name || assoc.entity_id}</span>
                          {can('project', 'update') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                            onClick={() => handleRemoveAssociation(assoc)}
                          >
                            <X className="h-3 w-3 text-destructive" />
                          </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        <Separator />

        {/* 任务列表 */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <ListChecks className="h-4 w-4" /> 任务 ({tasks.length})
            </h3>
            {can('project', 'update') && (
            <Button size="sm" onClick={() => { setShowTaskForm(true); setEditingTask(null); }}>
              <Plus className="h-3 w-3 mr-1" /> 新建任务
            </Button>
            )}
          </div>

          {showTaskForm && !editingTask && (
            <div className="border rounded-lg p-4 mb-3 bg-muted/20">
              <h4 className="text-sm font-medium mb-2">新建任务</h4>
              <TaskForm
                projectId={project.id}
                onSubmit={handleCreateTask}
                onCancel={() => setShowTaskForm(false)}
                loading={taskSaving}
              />
            </div>
          )}

          {tasksLoading ? (
            <LoadingSpinner text="加载任务..." />
          ) : tasks.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">暂无任务</p>
          ) : (
            <div className="space-y-2">
              {tasks.map(task => (
                <div key={task.id} className="border rounded-lg">
                  {editingTask?.id === task.id ? (
                    <div className="p-4 bg-muted/20">
                      <h4 className="text-sm font-medium mb-2">编辑任务</h4>
                      <TaskForm
                        projectId={project.id}
                        initial={editingTask}
                        onSubmit={handleUpdateTask}
                        onCancel={() => setEditingTask(null)}
                        loading={taskSaving}
                      />
                    </div>
                  ) : (
                    <>
                      <div
                        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/30"
                        onClick={() => toggleTaskExpand(task.id)}
                      >
                        {task.task_type === 'milestone' ? (
                          <div className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium truncate">{task.title}</span>
                            {task.phase_name && <Badge variant="outline" className="text-xs">{task.phase_name}</Badge>}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge className={`text-xs ${TASK_STATUSES[task.status]?.color || ''}`}>
                              {TASK_STATUSES[task.status]?.label || task.status}
                            </Badge>
                            <Badge className={`text-xs ${PRIORITIES[task.priority]?.color || ''}`}>
                              {PRIORITIES[task.priority]?.label || task.priority}
                            </Badge>
                            {task.due_date && (
                              <span className="text-xs text-muted-foreground">截止: {formatDate(task.due_date)}</span>
                            )}
                            {task.assignee_name && (
                              <span className="text-xs text-muted-foreground">{task.assignee_name}</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {/* 完成度条 */}
                          <div className="w-16 h-1.5 bg-muted rounded-full">
                            <div className="h-full bg-primary rounded-full" style={{ width: `${task.completion_percentage}%` }} />
                          </div>
                          <span className="text-xs text-muted-foreground w-8">{task.completion_percentage}%</span>
                          {can('project', 'update') && (
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={e => { e.stopPropagation(); setEditingTask(task); setShowTaskForm(false); }}>
                            <Pencil className="h-3 w-3" />
                          </Button>
                          )}
                          {can('project', 'delete') && (
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={e => { e.stopPropagation(); handleDeleteTask(task); }}>
                            <Trash2 className="h-3 w-3 text-destructive" />
                          </Button>
                          )}
                        </div>
                      </div>

                      {/* 展开区域：进度时间线 */}
                      {expandedTaskId === task.id && (
                        <div className="border-t px-4 py-3 bg-muted/10">
                          {task.description && (
                            <p className="text-sm text-muted-foreground mb-3">{task.description}</p>
                          )}
                          {progressLoading ? (
                            <LoadingSpinner text="加载进度..." />
                          ) : (
                            <ProgressTimeline
                              taskId={task.id}
                              entries={progressEntries}
                              onAdd={handleAddProgress}
                              onDelete={handleDeleteProgress}
                              loading={progressLoading}
                            />
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ==================== 主页面 ====================

export function ProjectsPanel() {
  const confirm = useConfirm();
  const { can } = usePermission();
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 搜索和筛选
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // 表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [editingAssociations, setEditingAssociations] = useState<{ entity_type: string; entity_id: string }[]>([]);
  const [saving, setSaving] = useState(false);

  // 详情弹窗
  const [detailProject, setDetailProject] = useState<ProjectDetail | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => { setSearch(searchInput); setPage(1); }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // 加载数据
  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectsApi.list({
        page, page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
        project_type: typeFilter || undefined,
      });
      setProjects(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error('加载项目失败:', e);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, typeFilter]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const handleCreate = async (data: ProjectCreate | ProjectUpdate) => {
    setSaving(true);
    try {
      await projectsApi.create(data as ProjectCreate);
      setShowForm(false);
      loadProjects();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (data: ProjectCreate | ProjectUpdate) => {
    if (!editingProject) return;
    setSaving(true);
    try {
      // 更新项目基本信息
      const { associations: newAssocs, ...updateData } = data as ProjectCreate;
      await projectsApi.update(editingProject.id, updateData as ProjectUpdate);

      // 同步关联：对比旧关联和新关联，增删差异
      if (newAssocs) {
        const oldSet = new Set(editingAssociations.map(a => `${a.entity_type}:${a.entity_id}`));
        const newSet = new Set(newAssocs.map(a => `${a.entity_type}:${a.entity_id}`));

        // 需要新增的关联
        const toAdd = newAssocs.filter(a => !oldSet.has(`${a.entity_type}:${a.entity_id}`));
        // 需要删除的关联（需要 assoc id，重新拉详情获取）
        const toRemoveKeys = editingAssociations.filter(a => !newSet.has(`${a.entity_type}:${a.entity_id}`));

        // 获取完整关联信息（含 id）以便删除
        if (toRemoveKeys.length > 0) {
          const detail = await projectsApi.get(editingProject.id);
          for (const key of toRemoveKeys) {
            const found = detail.associations.find(a => a.entity_type === key.entity_type && a.entity_id === key.entity_id);
            if (found) await projectsApi.removeAssociation(editingProject.id, found.id);
          }
        }
        for (const assoc of toAdd) {
          await projectsApi.addAssociation(editingProject.id, assoc);
        }
      }

      setShowForm(false);
      setEditingProject(null);
      setEditingAssociations([]);
      loadProjects();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (project: Project) => {
    const confirmed = await confirm({
      title: '删除项目',
      description: `确定要删除「${project.name}」吗？项目下的所有任务和进度记录也会被删除。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await projectsApi.delete(project.id);
      loadProjects();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const openDetail = async (project: Project) => {
    try {
      const detail = await projectsApi.get(project.id);
      setDetailProject(detail);
      setShowDetail(true);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const openEdit = async (project: Project) => {
    try {
      const detail = await projectsApi.get(project.id);
      setEditingProject(project);
      setEditingAssociations(
        (detail.associations || []).map(a => ({ entity_type: a.entity_type, entity_id: a.entity_id }))
      );
      setShowForm(true);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const refreshDetail = useCallback(async () => {
    if (!detailProject) return;
    try {
      const detail = await projectsApi.get(detailProject.id);
      setDetailProject(detail);
    } catch (e) {
      console.error('刷新详情失败:', e);
    }
  }, [detailProject]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* 操作栏 */}
      <div className="flex items-center justify-end">
        {can('project', 'create') && (
        <Button onClick={() => { setEditingProject(null); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1" /> 新建项目
        </Button>
        )}
      </div>

      {/* 搜索和筛选 */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="搜索项目名称..."
            className="pl-9"
          />
        </div>
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
        >
          <option value="">全部状态</option>
          {Object.entries(PROJECT_STATUSES).map(([v, { label }]) => (
            <option key={v} value={v}>{label}</option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
          value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
        >
          <option value="">全部类型</option>
          <option value="general">通用</option>
          <option value="research">研发</option>
          <option value="order">订单</option>
          <option value="purchase">采购</option>
          <option value="sales">销售</option>
        </select>
      </div>

      {/* 项目列表 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>项目名称</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>优先级</TableHead>
              <TableHead>任务</TableHead>
              <TableHead>关联</TableHead>
              <TableHead>截止日期</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-12 text-center">
                  <LoadingSpinner text="加载中..." />
                </TableCell>
              </TableRow>
            ) : projects.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-12 text-center text-muted-foreground">
                  {search || statusFilter || typeFilter ? '没有匹配数据' : '暂无项目'}
                </TableCell>
              </TableRow>
            ) : (
              projects.map(project => (
                <TableRow key={project.id}>
                  <TableCell>
                    <button
                      onClick={() => openDetail(project)}
                      className="text-sm font-medium text-primary hover:text-primary/80 text-left"
                    >
                      {project.name}
                    </button>
                    {project.tags && project.tags.length > 0 && (
                      <div className="flex gap-1 mt-1">
                        {project.tags.slice(0, 3).map(tag => (
                          <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-sm">{project.project_type}</TableCell>
                  <TableCell>
                    <Badge className={PROJECT_STATUSES[project.status]?.color || ''}>
                      {PROJECT_STATUSES[project.status]?.label || project.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={PRIORITIES[project.priority]?.color || ''}>
                      {PRIORITIES[project.priority]?.label || project.priority}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{project.task_count}</TableCell>
                  <TableCell className="text-sm">{project.association_count}</TableCell>
                  <TableCell className="text-sm">{formatDate(project.due_date)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openDetail(project)}>
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                      {can('project', 'update') && (
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(project)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      )}
                      {can('project', 'delete') && (
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => handleDelete(project)}>
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t">
            <span className="text-sm text-muted-foreground">共 {total} 条</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm">{page} / {totalPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 创建/编辑弹窗 */}
      <Dialog open={showForm} onOpenChange={() => { setShowForm(false); setEditingProject(null); setEditingAssociations([]); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingProject ? '编辑项目' : '新建项目'}</DialogTitle>
          </DialogHeader>
          <ProjectForm
            initial={editingProject ? {
              name: editingProject.name,
              project_type: editingProject.project_type,
              description: editingProject.description || '',
              status: editingProject.status,
              priority: editingProject.priority,
              start_date: editingProject.start_date || '',
              due_date: editingProject.due_date || '',
              tags: editingProject.tags,
              notes: editingProject.notes || '',
            } : undefined}
            initialAssociations={editingProject ? editingAssociations : undefined}
            onSubmit={editingProject ? handleUpdate : handleCreate}
            onCancel={() => { setShowForm(false); setEditingProject(null); setEditingAssociations([]); }}
            loading={saving}
          />
        </DialogContent>
      </Dialog>

      {/* 详情弹窗 */}
      <ProjectDetailModal
        project={detailProject}
        isOpen={showDetail}
        onClose={() => setShowDetail(false)}
        onRefresh={refreshDetail}
      />
    </div>
  );
}
