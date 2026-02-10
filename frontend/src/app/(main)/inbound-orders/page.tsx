// src/app/admin/inbound-orders/page.tsx
// 入仓单管理页面
//
// 功能说明：
// 1. 入仓单列表（搜索、状态筛选、分页）
// 2. 新建入仓单
// 3. 入仓单详情 + 状态变更
// 4. 删除入仓单

'use client';

import { useState, useEffect, useCallback } from 'react';
import { inboundOrdersApi, InboundOrder } from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { Plus, Trash2, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
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
import { FormSection } from '@/components/FormSection';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { StatusBadge, type StatusConfig } from '@/components/StatusBadge';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { ErrorAlert } from '@/components/ErrorAlert';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { formatDateTime, formatDate } from '@/lib/format';

// ==================== 状态配置 ====================

const ORDER_STATUSES: Record<string, StatusConfig> = {
  draft: { label: '草稿', color: 'draft' },
  confirmed: { label: '已确认', color: 'confirmed' },
  partial_received: { label: '部分收货', color: 'pending' },
  received: { label: '已收货', color: 'completed' },
  cancelled: { label: '已取消', color: 'cancelled' },
};

// ==================== 新建入仓单表单 ====================

interface CreateFormData {
  warehouse_id: string;
  purchase_contract_id: string;
  supplier_id: string;
  expected_date: string;
  notes: string;
}

function CreateOrderForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<CreateFormData>({
    warehouse_id: '',
    purchase_contract_id: '',
    supplier_id: '',
    expected_date: '',
    notes: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned: Record<string, unknown> = {
      warehouse_id: form.warehouse_id,
    };
    if (form.purchase_contract_id.trim()) {
      cleaned.purchase_contract_id = form.purchase_contract_id.trim();
    }
    if (form.supplier_id.trim()) {
      cleaned.supplier_id = form.supplier_id.trim();
    }
    if (form.expected_date) {
      cleaned.expected_date = form.expected_date;
    }
    if (form.notes.trim()) {
      cleaned.notes = form.notes.trim();
    }
    onSubmit(cleaned);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <FormSection title="基本信息" collapsible={false}>
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
            <Label className="mb-1">采购合同 ID</Label>
            <Input
              type="text"
              placeholder="可选"
              value={form.purchase_contract_id}
              onChange={e => setForm({ ...form, purchase_contract_id: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">供应商 ID</Label>
            <Input
              type="text"
              placeholder="可选"
              value={form.supplier_id}
              onChange={e => setForm({ ...form, supplier_id: e.target.value })}
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
      </FormSection>

      <div>
        <Label className="mb-1">备注</Label>
        <Textarea
          rows={3}
          placeholder="可选备注信息"
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
        />
      </div>

      <FormFooter
        onCancel={onCancel}
        submitText="创建"
        loading={loading}
        disabled={!form.warehouse_id.trim()}
      />
    </form>
  );
}

// ==================== 入仓单详情弹窗 ====================

function OrderDetailModal({
  isOpen,
  onClose,
  order,
  onStatusChanged,
}: {
  isOpen: boolean;
  onClose: () => void;
  order: InboundOrder | null;
  onStatusChanged: () => void;
}) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (isOpen && order) {
      setLoading(true);
      inboundOrdersApi
        .get(order.id)
        .then(setDetail)
        .catch(err => {
          console.error('加载入仓单详情失败:', err);
          // 降级使用列表数据
          setDetail(order);
        })
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [isOpen, order]);

  const handleStatusChange = async (newStatus: string) => {
    if (!order) return;
    setStatusLoading(true);
    try {
      await inboundOrdersApi.updateStatus(order.id, newStatus);
      toast.success('状态更新成功');
      // 重新加载详情
      const updated = await inboundOrdersApi.get(order.id);
      setDetail(updated);
      onStatusChanged();
    } catch (err) {
      toast.error('状态更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStatusLoading(false);
    }
  };

  if (!order) return null;

  const data = detail || order;
  const statusConfig = ORDER_STATUSES[data.status];

  // 根据当前状态决定可切换到的目标状态
  const getAvailableTransitions = (currentStatus: string): { value: string; label: string }[] => {
    switch (currentStatus) {
      case 'draft':
        return [
          { value: 'confirmed', label: '确认' },
          { value: 'cancelled', label: '取消' },
        ];
      case 'confirmed':
        return [
          { value: 'partial_received', label: '部分收货' },
          { value: 'received', label: '全部收货' },
          { value: 'cancelled', label: '取消' },
        ];
      case 'partial_received':
        return [
          { value: 'received', label: '全部收货' },
        ];
      default:
        return [];
    }
  };

  const transitions = getAvailableTransitions(data.status);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{`入仓单详情 - ${data.order_no}`}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : (
          <div className="space-y-6">
            {/* 头部概览 */}
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-lg font-semibold text-foreground">{data.order_no}</h4>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {data.warehouse_name || data.warehouse_id}
                </p>
              </div>
              {statusConfig ? (
                <StatusBadge status={data.status} statusMap={ORDER_STATUSES} />
              ) : (
                <Badge variant="secondary">{data.status}</Badge>
              )}
            </div>

            {/* 基本信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">基本信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">单号</span>
                  <span className="text-sm text-foreground">{data.order_no}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">仓库</span>
                  <span className="text-sm text-foreground">{data.warehouse_name || data.warehouse_id}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">供应商</span>
                  <span className="text-sm text-foreground">{data.supplier_name || '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">采购合同</span>
                  <span className="text-sm text-foreground">{data.purchase_contract_no || '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">行数</span>
                  <span className="text-sm text-foreground">{data.line_count}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">预期日期</span>
                  <span className="text-sm text-foreground">{data.expected_date ? formatDate(data.expected_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">实际日期</span>
                  <span className="text-sm text-foreground">{data.actual_date ? formatDate(data.actual_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">创建人</span>
                  <span className="text-sm text-foreground">{data.created_by || '-'}</span>
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

            {/* 状态变更 */}
            {transitions.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2">状态操作</h5>
                <Separator className="mb-2" />
                <div className="flex items-center gap-2">
                  {transitions.map(t => (
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

export default function InboundOrdersPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 列表数据
  const [orders, setOrders] = useState<InboundOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选/搜索
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 弹窗状态
  const [showCreate, setShowCreate] = useState(false);
  const [viewingOrder, setViewingOrder] = useState<InboundOrder | null>(null);
  const [creating, setCreating] = useState(false);

  // ==================== 数据加载 ====================

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter) params.status = statusFilter;

      const res = await inboundOrdersApi.list(
        params as Parameters<typeof inboundOrdersApi.list>[0]
      );
      setOrders(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('加载入仓单列表失败:', err);
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, statusFilter]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // 搜索/筛选变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter]);

  // ==================== 操作 ====================

  const handleCreate = async (data: Record<string, unknown>) => {
    setCreating(true);
    try {
      await inboundOrdersApi.create(data);
      toast.success('入仓单创建成功');
      setShowCreate(false);
      await loadOrders();
    } catch (err) {
      toast.error('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (order: InboundOrder) => {
    const confirmed = await confirm({
      title: '删除入仓单',
      description: `确定要删除入仓单「${order.order_no}」吗？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await inboundOrdersApi.delete(order.id);
      toast.success('删除成功');
      await loadOrders();
      // 如果正在查看该订单详情，关闭弹窗
      if (viewingOrder?.id === order.id) {
        setViewingOrder(null);
      }
    } catch (err) {
      toast.error('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      <SearchFilterBar
        searchPlaceholder="搜索单号、仓库、供应商..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'status',
            placeholder: '全部状态',
            options: Object.entries(ORDER_STATUSES).map(([value, { label }]) => ({
              value,
              label,
            })),
          },
        ]}
        filterValues={{ status: statusFilter }}
        onFilterChange={(key, value) => {
          if (key === 'status') setStatusFilter(value);
        }}
        actions={
          can('inbound_order', 'create') ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" />
              新建入仓单
            </Button>
          ) : undefined
        }
      />

      {/* 错误信息 */}
      {error && <ErrorAlert message={error} onRetry={loadOrders} />}

      {/* 入仓单列表 */}
      <DataTableShell
        loading={loading}
        itemCount={orders.length}
        columns={8}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle="暂无入仓单数据"
      >
        <TableHeader>
          <TableRow>
            <TableHead className="px-6">单号</TableHead>
            <TableHead className="px-6">仓库</TableHead>
            <TableHead className="px-6">供应商</TableHead>
            <TableHead className="px-6">采购合同</TableHead>
            <TableHead className="px-6">行数</TableHead>
            <TableHead className="px-6">预期日期</TableHead>
            <TableHead className="px-6">状态</TableHead>
            <TableHead className="px-6 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map(order => (
            <TableRow key={order.id}>
              <TableCell className="px-6 py-4">
                <button
                  onClick={() => setViewingOrder(order)}
                  className="text-left group"
                >
                  <span className="text-sm font-medium text-foreground group-hover:text-primary">
                    {order.order_no}
                  </span>
                </button>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {order.warehouse_name || '-'}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {order.supplier_name || '-'}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {order.purchase_contract_no || '-'}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {order.line_count}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {order.expected_date ? formatDate(order.expected_date) : '-'}
              </TableCell>
              <TableCell className="px-6 py-4">
                <StatusBadge status={order.status} statusMap={ORDER_STATUSES} />
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
                  {can('inbound_order', 'delete') && (
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
          ))}
        </TableBody>
      </DataTableShell>

      {/* 新建入仓单弹窗 */}
      <FormDialog
        open={showCreate}
        onOpenChange={(open) => { if (!open) setShowCreate(false); }}
        title="新建入仓单"
        size="md"
      >
        <CreateOrderForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={creating}
        />
      </FormDialog>

      {/* 入仓单详情弹窗 */}
      <OrderDetailModal
        isOpen={!!viewingOrder}
        onClose={() => setViewingOrder(null)}
        order={viewingOrder}
        onStatusChanged={loadOrders}
      />
    </div>
  );
}
