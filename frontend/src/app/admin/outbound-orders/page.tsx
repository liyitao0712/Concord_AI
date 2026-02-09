// src/app/admin/outbound-orders/page.tsx
// 出仓单管理页面
//
// 功能说明：
// 1. 出仓单列表（搜索、状态筛选、分页）
// 2. 新建出仓单
// 3. 出仓单详情 + 状态变更

'use client';

import { useState, useEffect, useCallback } from 'react';
import { outboundOrdersApi, OutboundOrder } from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { Plus, Trash2, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
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
} from '@/components/ui/dialog';
import { LoadingSpinner } from '@/components/LoadingSpinner';

// ==================== 工具函数 ====================

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

// ==================== 状态配置 ====================

const ORDER_STATUSES: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-800' },
  confirmed: { label: '已确认', color: 'bg-blue-100 text-blue-800' },
  partial_shipped: { label: '部分发货', color: 'bg-orange-100 text-orange-800' },
  shipped: { label: '已发货', color: 'bg-green-100 text-green-800' },
  cancelled: { label: '已取消', color: 'bg-red-100 text-red-800' },
};

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ==================== 新建出仓单表单 ====================

function CreateOrderForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({
    warehouse_id: '',
    sales_contract_id: '',
    customer_id: '',
    expected_date: '',
    notes: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, unknown> = {
      warehouse_id: form.warehouse_id,
    };
    if (form.sales_contract_id.trim()) data.sales_contract_id = form.sales_contract_id;
    if (form.customer_id.trim()) data.customer_id = form.customer_id;
    if (form.expected_date) data.expected_date = form.expected_date;
    if (form.notes.trim()) data.notes = form.notes;
    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-3">基本信息</h4>
        <Separator className="mb-3" />
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Label className="mb-1">仓库 ID *</Label>
            <Input
              type="text"
              required
              placeholder="请输入仓库 ID"
              value={form.warehouse_id}
              onChange={e => setForm({ ...form, warehouse_id: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">销售合同 ID</Label>
            <Input
              type="text"
              placeholder="可选"
              value={form.sales_contract_id}
              onChange={e => setForm({ ...form, sales_contract_id: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">客户 ID</Label>
            <Input
              type="text"
              placeholder="可选"
              value={form.customer_id}
              onChange={e => setForm({ ...form, customer_id: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">预期日期</Label>
            <Input
              type="date"
              value={form.expected_date}
              onChange={e => setForm({ ...form, expected_date: e.target.value })}
            />
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-foreground mb-3">备注</h4>
        <Separator className="mb-3" />
        <Textarea
          rows={3}
          placeholder="可选备注信息"
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
        />
      </div>

      <Separator />
      <div className="flex justify-end space-x-3 pt-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" disabled={loading || !form.warehouse_id.trim()}>
          {loading ? '创建中...' : '创建'}
        </Button>
      </div>
    </form>
  );
}

// ==================== 出仓单详情弹窗 ====================

function OrderDetailModal({
  isOpen,
  onClose,
  order,
  onStatusChanged,
}: {
  isOpen: boolean;
  onClose: () => void;
  order: OutboundOrder | null;
  onStatusChanged: () => void;
}) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const confirm = useConfirm();

  useEffect(() => {
    if (isOpen && order) {
      setLoading(true);
      outboundOrdersApi
        .get(order.id)
        .then(setDetail)
        .catch(err => {
          console.error('加载出仓单详情失败:', err);
          toast.error('加载详情失败');
        })
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [isOpen, order]);

  if (!order) return null;

  const data = detail || order;
  const statusInfo = ORDER_STATUSES[data.status] || ORDER_STATUSES.draft;

  // 根据当前状态决定可切换的目标状态
  const getAvailableTransitions = (currentStatus: string): { value: string; label: string }[] => {
    switch (currentStatus) {
      case 'draft':
        return [
          { value: 'confirmed', label: '确认出仓单' },
          { value: 'cancelled', label: '取消' },
        ];
      case 'confirmed':
        return [
          { value: 'partial_shipped', label: '部分发货' },
          { value: 'shipped', label: '已发货' },
          { value: 'cancelled', label: '取消' },
        ];
      case 'partial_shipped':
        return [
          { value: 'shipped', label: '已发货' },
          { value: 'cancelled', label: '取消' },
        ];
      default:
        return [];
    }
  };

  const availableTransitions = getAvailableTransitions(data.status);

  const handleStatusChange = async (newStatus: string) => {
    const targetLabel = ORDER_STATUSES[newStatus]?.label || newStatus;
    const confirmed = await confirm({
      title: '变更状态',
      description: `确定要将出仓单「${data.order_no}」的状态变更为「${targetLabel}」吗？`,
      variant: newStatus === 'cancelled' ? 'destructive' : 'default',
    });
    if (!confirmed) return;

    setStatusLoading(true);
    try {
      await outboundOrdersApi.updateStatus(data.id, newStatus);
      toast.success(`状态已变更为「${targetLabel}」`);
      // 刷新详情
      const updated = await outboundOrdersApi.get(data.id);
      setDetail(updated);
      onStatusChanged();
    } catch (err) {
      toast.error('状态变更失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStatusLoading(false);
    }
  };

  const V = (value: string | null | undefined) => value || '-';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{`出仓单详情 - ${data.order_no}`}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : (
          <div className="space-y-6">
            {/* 状态概览 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-lg font-semibold text-foreground">{data.order_no}</span>
                <Badge variant="secondary" className={statusInfo.color}>
                  {statusInfo.label}
                </Badge>
              </div>
            </div>

            {/* 基本信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">基本信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">出仓单号</span>
                  <span className="text-sm text-foreground">{data.order_no}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">仓库</span>
                  <span className="text-sm text-foreground">{V(data.warehouse_name)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">客户</span>
                  <span className="text-sm text-foreground">{V(data.customer_name)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">销售合同</span>
                  <span className="text-sm text-foreground">{V(data.sales_contract_no)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">行数</span>
                  <span className="text-sm text-foreground">{data.line_count}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">创建人</span>
                  <span className="text-sm text-foreground">{V(data.created_by)}</span>
                </div>
              </div>
            </div>

            {/* 日期信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">日期信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">预期日期</span>
                  <span className="text-sm text-foreground">{formatDate(data.expected_date)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">实际日期</span>
                  <span className="text-sm text-foreground">{formatDate(data.actual_date)}</span>
                </div>
              </div>
            </div>

            {/* 备注 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">备注</h5>
              <Separator className="mb-2" />
              <p className={`text-sm whitespace-pre-wrap ${data.notes ? 'text-foreground' : 'text-muted-foreground'}`}>
                {data.notes || '-'}
              </p>
            </div>

            {/* 状态变更操作 */}
            {availableTransitions.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2">状态操作</h5>
                <Separator className="mb-3" />
                <div className="flex items-center gap-2">
                  {availableTransitions.map(t => (
                    <Button
                      key={t.value}
                      size="sm"
                      variant={t.value === 'cancelled' ? 'destructive' : 'default'}
                      disabled={statusLoading}
                      onClick={() => handleStatusChange(t.value)}
                    >
                      {statusLoading ? '处理中...' : t.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* 时间信息 */}
            <Separator />
            <div className="text-xs text-muted-foreground flex gap-6">
              <span>创建时间: {formatDateTime(data.created_at)}</span>
              <span>更新时间: {data.updated_at ? formatDateTime(data.updated_at) : '-'}</span>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==================== 主页面 ====================

export default function OutboundOrdersPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 数据状态
  const [orders, setOrders] = useState<OutboundOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 筛选/搜索
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 弹窗状态
  const [showCreate, setShowCreate] = useState(false);
  const [viewingOrder, setViewingOrder] = useState<OutboundOrder | null>(null);
  const [saving, setSaving] = useState(false);

  // ==================== 数据加载 ====================

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const res = await outboundOrdersApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: filterStatus || undefined,
      });
      setOrders(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('加载出仓单列表失败:', err);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // ==================== 操作 ====================

  const handleCreate = async (data: Record<string, unknown>) => {
    setSaving(true);
    try {
      await outboundOrdersApi.create(data);
      setShowCreate(false);
      toast.success('出仓单创建成功');
      await loadOrders();
    } catch (err) {
      toast.error('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (order: OutboundOrder) => {
    const confirmed = await confirm({
      title: '删除出仓单',
      description: `确定要删除出仓单「${order.order_no}」吗？此操作不可撤销。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await outboundOrdersApi.delete(order.id);
      toast.success('出仓单已删除');
      await loadOrders();
    } catch (err) {
      toast.error('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">出仓单管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理出仓单和发货</p>
        </div>
        {can('outbound_order', 'create') && (
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          新建出仓单
        </Button>
        )}
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <Input
          type="text"
          placeholder="搜索单号、客户、合同号..."
          value={searchInput}
          onChange={e => setSearchInput(e.target.value)}
          className="flex-1"
        />
        <select
          className={selectClass}
          value={filterStatus}
          onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
        >
          <option value="">全部状态</option>
          {Object.entries(ORDER_STATUSES).map(([value, { label }]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* 出仓单列表 */}
      <Card className="py-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="px-6">单号</TableHead>
              <TableHead className="px-6">仓库</TableHead>
              <TableHead className="px-6">客户</TableHead>
              <TableHead className="px-6">销售合同</TableHead>
              <TableHead className="px-6">行数</TableHead>
              <TableHead className="px-6">预期日期</TableHead>
              <TableHead className="px-6">状态</TableHead>
              <TableHead className="px-6 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="px-6 py-12 text-center">
                  <LoadingSpinner text="加载中..." />
                </TableCell>
              </TableRow>
            ) : orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="px-6 py-12 text-center text-muted-foreground">
                  {search || filterStatus ? '没有匹配的出仓单' : '暂无出仓单数据'}
                </TableCell>
              </TableRow>
            ) : (
              orders.map(order => {
                const statusInfo = ORDER_STATUSES[order.status] || ORDER_STATUSES.draft;
                return (
                  <TableRow key={order.id}>
                    <TableCell className="px-6 py-4">
                      <button
                        onClick={() => setViewingOrder(order)}
                        className="text-sm font-medium text-primary hover:text-primary/80"
                      >
                        {order.order_no}
                      </button>
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {order.warehouse_name || '-'}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {order.customer_name || '-'}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {order.sales_contract_no || '-'}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {order.line_count}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {formatDate(order.expected_date)}
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <Badge variant="secondary" className={statusInfo.color}>
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => setViewingOrder(order)}
                          title="查看"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {can('outbound_order', 'delete') && (
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(order)}
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t">
            <div className="text-sm text-muted-foreground">
              共 {total} 条，第 {page}/{totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                下一页
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* 新建出仓单弹窗 */}
      <Dialog open={showCreate} onOpenChange={(open) => { if (!open) setShowCreate(false); }}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>新建出仓单</DialogTitle>
          </DialogHeader>
          <CreateOrderForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreate(false)}
            loading={saving}
          />
        </DialogContent>
      </Dialog>

      {/* 出仓单详情弹窗 */}
      <OrderDetailModal
        isOpen={!!viewingOrder}
        onClose={() => setViewingOrder(null)}
        order={viewingOrder}
        onStatusChanged={loadOrders}
      />
    </div>
  );
}
