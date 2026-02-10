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
import { PageHeader } from '@/components/PageHeader';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { FormSection } from '@/components/FormSection';
import { StatusBadge, type StatusConfig } from '@/components/StatusBadge';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { formatDateTime, formatDate } from '@/lib/format';

// ==================== 状态配置 ====================

const ORDER_STATUSES: Record<string, StatusConfig> = {
  draft: { label: '草稿', color: 'draft' },
  confirmed: { label: '已确认', color: 'confirmed' },
  partial_shipped: { label: '部分发货', color: 'pending' },
  shipped: { label: '已发货', color: 'completed' },
  cancelled: { label: '已取消', color: 'cancelled' },
};

// 状态标签查找（用于详情弹窗等需要纯文本的场景）
const ORDER_STATUS_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(ORDER_STATUSES).map(([key, { label }]) => [key, label])
);

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
      </FormSection>

      <FormSection title="备注" collapsible={false}>
        <Textarea
          rows={3}
          placeholder="可选备注信息"
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
        />
      </FormSection>

      <FormFooter
        onCancel={onCancel}
        submitText="创建"
        loading={loading}
        disabled={!form.warehouse_id.trim()}
      />
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
  const statusConfig = ORDER_STATUSES[data.status] || ORDER_STATUSES.draft;

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
    const targetLabel = ORDER_STATUS_LABELS[newStatus] || newStatus;
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
                <StatusBadge status={data.status} statusMap={ORDER_STATUSES} />
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
                  <span className="text-sm text-foreground">{data.expected_date ? formatDate(data.expected_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">实际日期</span>
                  <span className="text-sm text-foreground">{data.actual_date ? formatDate(data.actual_date) : '-'}</span>
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
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [search, setSearch] = useState('');
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
    setSearch(debouncedSearch);
    setPage(1);
  }, [debouncedSearch]);

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
      <PageHeader
        title="出仓单管理"
        description="管理出仓单和发货"
        actions={can('outbound_order', 'create') ? (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            新建出仓单
          </Button>
        ) : undefined}
      />

      {/* 搜索和筛选 */}
      <SearchFilterBar
        searchPlaceholder="搜索单号、客户、合同号..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'status',
            placeholder: '全部状态',
            options: Object.entries(ORDER_STATUSES).map(([value, { label }]) => ({ value, label })),
          },
        ]}
        filterValues={{ status: filterStatus }}
        onFilterChange={(key, value) => {
          if (key === 'status') { setFilterStatus(value); setPage(1); }
        }}
      />

      {/* 出仓单列表 */}
      <DataTableShell
        loading={loading}
        itemCount={orders.length}
        columns={8}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle={search || filterStatus ? '没有匹配的出仓单' : '暂无出仓单数据'}
      >
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
          {orders.map(order => (
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
          ))}
        </TableBody>
      </DataTableShell>

      {/* 新建出仓单弹窗 */}
      <FormDialog
        open={showCreate}
        onOpenChange={(open) => { if (!open) setShowCreate(false); }}
        title="新建出仓单"
        size="md"
      >
        <CreateOrderForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={saving}
        />
      </FormDialog>

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
