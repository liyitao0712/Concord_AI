// src/app/admin/sales-contracts/page.tsx
// 销售合同管理页面
//
// 功能说明：
// 1. 销售合同列表（搜索、状态筛选、分页）
// 2. 新建销售合同
// 3. 合同详情 + 状态变更

'use client';

import { useState, useEffect, useCallback } from 'react';
import { salesContractsApi, SalesContractItem, SalesContractCreate } from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { Plus, Trash2, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
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
import { FormSection } from '@/components/FormSection';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { StatusBadge, type StatusConfig } from '@/components/StatusBadge';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { formatDateTime, formatDate } from '@/lib/format';

// ==================== 工具函数 ====================

function formatAmount(amount: number, currency: string): string {
  return `${currency} ${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ==================== 合同状态配置 ====================

const CONTRACT_STATUSES: Record<string, StatusConfig> = {
  draft: { label: '草稿', color: 'draft' },
  pending_approval: { label: '待审批', color: 'pending' },
  approved: { label: '已审批', color: 'confirmed' },
  signed: { label: '已签订', color: 'normal' },
  in_progress: { label: '执行中', color: 'active' },
  partial_shipped: { label: '部分发货', color: 'important' },
  shipped: { label: '已发货', color: 'active' },
  completed: { label: '已完成', color: 'completed' },
  cancelled: { label: '已取消', color: 'cancelled' },
};

const CONTRACT_STATUS_OPTIONS = Object.entries(CONTRACT_STATUSES).map(
  ([value, { label }]) => ({ value, label })
);

// 详情弹窗中使用的旧样式状态映射（保留用于状态变更 select 的展示）
const CONTRACT_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-800' },
  pending_approval: { label: '待审批', color: 'bg-yellow-100 text-yellow-800' },
  approved: { label: '已审批', color: 'bg-blue-100 text-blue-800' },
  signed: { label: '已签订', color: 'bg-indigo-100 text-indigo-800' },
  in_progress: { label: '执行中', color: 'bg-cyan-100 text-cyan-800' },
  partial_shipped: { label: '部分发货', color: 'bg-orange-100 text-orange-800' },
  shipped: { label: '已发货', color: 'bg-teal-100 text-teal-800' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
  cancelled: { label: '已取消', color: 'bg-red-100 text-red-800' },
};

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ==================== 合同详情弹窗 ====================

function ContractDetailModal({
  isOpen,
  onClose,
  contract,
  onStatusChange,
}: {
  isOpen: boolean;
  onClose: () => void;
  contract: SalesContractItem | null;
  onStatusChange: () => void;
}) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (isOpen && contract) {
      setLoading(true);
      salesContractsApi
        .get(contract.id)
        .then(setDetail)
        .catch(err => console.error('加载合同详情失败:', err))
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [isOpen, contract]);

  if (!contract) return null;

  const data = detail || contract;
  const statusConfig = CONTRACT_STATUS_LABELS[data.status] || CONTRACT_STATUS_LABELS.draft;
  const V = (value: string | number | null | undefined) => (value !== null && value !== undefined && value !== '') ? String(value) : '-';

  const handleStatusChange = async (newStatus: string) => {
    setStatusLoading(true);
    try {
      await salesContractsApi.updateStatus(data.id, newStatus);
      toast.success('状态更新成功');
      // 重新加载详情
      const updated = await salesContractsApi.get(data.id);
      setDetail(updated);
      onStatusChange();
    } catch (err) {
      toast.error('状态更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStatusLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>{`合同详情 - ${data.contract_no}`}</DialogTitle>
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
                <h4 className="text-lg font-semibold text-foreground">{data.contract_no}</h4>
                <p className="text-sm text-muted-foreground mt-0.5">{data.customer_name || '-'}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className={statusConfig.color}>
                  {statusConfig.label}
                </Badge>
                {data.is_zero_stock && (
                  <Badge variant="secondary" className="bg-purple-100 text-purple-800">
                    零库存
                  </Badge>
                )}
              </div>
            </div>

            {/* 状态变更 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <Label className="mb-2 block text-sm font-medium">变更合同状态</Label>
              <div className="flex items-center gap-2">
                <select
                  className={`flex-1 ${selectClass}`}
                  value={data.status}
                  onChange={(e) => handleStatusChange(e.target.value)}
                  disabled={statusLoading}
                >
                  {Object.entries(CONTRACT_STATUS_LABELS).map(([value, { label }]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
                {statusLoading && <span className="text-sm text-muted-foreground">更新中...</span>}
              </div>
            </div>

            {/* 基本信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">基本信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">合同编号</span>
                  <span className="text-sm text-foreground">{data.contract_no}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">客户</span>
                  <span className="text-sm text-foreground">{V(data.customer_name)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">币种</span>
                  <span className="text-sm text-foreground">{V(data.currency)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">汇率</span>
                  <span className="text-sm text-foreground">{V(data.exchange_rate)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">行数</span>
                  <span className="text-sm text-foreground">{data.line_count}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">零库存</span>
                  <Badge variant="secondary" className={data.is_zero_stock ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}>
                    {data.is_zero_stock ? '是' : '否'}
                  </Badge>
                </div>
              </div>
            </div>

            {/* 金额信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">金额信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">小计</span>
                  <span className="text-sm text-foreground">{formatAmount(data.subtotal, data.currency)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">折扣</span>
                  <span className="text-sm text-foreground">{formatAmount(data.discount_amount, data.currency)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">税额</span>
                  <span className="text-sm text-foreground">{formatAmount(data.tax_amount, data.currency)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">总金额</span>
                  <span className="text-sm text-foreground font-semibold">{formatAmount(data.total_amount, data.currency)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">佣金比例</span>
                  <span className="text-sm text-foreground">{data.commission_rate != null ? `${data.commission_rate}%` : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">佣金金额</span>
                  <span className="text-sm text-foreground">{data.commission_amount != null ? formatAmount(data.commission_amount, data.currency) : '-'}</span>
                </div>
              </div>
            </div>

            {/* 贸易信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">贸易信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">贸易术语</span>
                  <span className="text-sm text-foreground">{V(data.trade_term)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">付款方式</span>
                  <span className="text-sm text-foreground">{V(data.payment_method)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">付款条款</span>
                  <span className="text-sm text-foreground">{V(data.payment_terms)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">装运港</span>
                  <span className="text-sm text-foreground">{V(data.port_of_loading)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">卸货港</span>
                  <span className="text-sm text-foreground">{V(data.port_of_discharge)}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">目的地</span>
                  <span className="text-sm text-foreground">{V(data.destination)}</span>
                </div>
                <div className="flex py-1.5 col-span-2">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">唛头</span>
                  <span className="text-sm text-foreground whitespace-pre-wrap">{V(data.shipping_marks)}</span>
                </div>
              </div>
            </div>

            {/* 日期信息 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">日期信息</h5>
              <Separator className="mb-2" />
              <div className="grid grid-cols-2 gap-x-8">
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">合同日期</span>
                  <span className="text-sm text-foreground">{data.contract_date ? formatDate(data.contract_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">交付日期</span>
                  <span className="text-sm text-foreground">{data.delivery_date ? formatDate(data.delivery_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">发货日期</span>
                  <span className="text-sm text-foreground">{data.shipping_date ? formatDate(data.shipping_date) : '-'}</span>
                </div>
                <div className="flex py-1.5">
                  <span className="text-sm text-muted-foreground w-24 flex-shrink-0">到期日期</span>
                  <span className="text-sm text-foreground">{data.expiry_date ? formatDate(data.expiry_date) : '-'}</span>
                </div>
              </div>
            </div>

            {/* 标签 */}
            {data.tags && data.tags.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2">标签</h5>
                <Separator className="mb-2" />
                <div className="flex flex-wrap gap-2">
                  {data.tags.map((tag: string) => (
                    <Badge key={tag} variant="secondary" className="bg-blue-100 text-blue-800">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* 备注 */}
            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">备注</h5>
              <Separator className="mb-2" />
              <p className={`text-sm whitespace-pre-wrap ${data.notes ? 'text-foreground' : 'text-muted-foreground'}`}>
                {data.notes || '-'}
              </p>
            </div>

            {/* 关联采购合同 */}
            {data.linked_purchase_contract_id && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2">关联采购合同</h5>
                <Separator className="mb-2" />
                <span className="text-sm text-foreground">{data.linked_purchase_contract_id}</span>
              </div>
            )}

            {/* 时间信息 */}
            <Separator />
            <div className="text-xs text-muted-foreground flex gap-6">
              <span>创建时间: {formatDateTime(data.created_at)}</span>
              <span>更新时间: {data.updated_at ? formatDateTime(data.updated_at) : '-'}</span>
              {data.created_by && <span>创建人: {data.created_by}</span>}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==================== 主页面 ====================

export default function SalesContractsPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 数据状态
  const [contracts, setContracts] = useState<SalesContractItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 筛选/搜索
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [filterStatus, setFilterStatus] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 弹窗状态
  const [showCreate, setShowCreate] = useState(false);
  const [viewingContract, setViewingContract] = useState<SalesContractItem | null>(null);
  const [saving, setSaving] = useState(false);

  // 创建表单
  const [createForm, setCreateForm] = useState<SalesContractCreate>({
    customer_id: '',
    currency: 'CNY',
    trade_term: '',
    payment_method: '',
    port_of_loading: '',
    port_of_discharge: '',
    destination: '',
    contract_date: '',
    delivery_date: '',
    shipping_date: '',
    is_zero_stock: false,
    notes: '',
  });

  // 加载合同列表
  const loadContracts = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (debouncedSearch) params.search = debouncedSearch;
      if (filterStatus) params.status = filterStatus;

      const res = await salesContractsApi.list(params as Parameters<typeof salesContractsApi.list>[0]);
      setContracts(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('加载销售合同列表失败:', err);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, filterStatus]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // 搜索变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // 重置创建表单
  const resetCreateForm = () => {
    setCreateForm({
      customer_id: '',
      currency: 'CNY',
      trade_term: '',
      payment_method: '',
      port_of_loading: '',
      port_of_discharge: '',
      destination: '',
      contract_date: '',
      delivery_date: '',
      shipping_date: '',
      is_zero_stock: false,
      notes: '',
    });
  };

  // 创建合同
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.customer_id.trim()) {
      toast.error('请填写客户 ID');
      return;
    }
    setSaving(true);
    try {
      // 清理空字符串
      const cleaned: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(createForm)) {
        if (value === '' || value === null || value === undefined) {
          if (key === 'customer_id' || key === 'is_zero_stock') {
            cleaned[key] = value;
          }
        } else {
          cleaned[key] = value;
        }
      }
      await salesContractsApi.create(cleaned as unknown as SalesContractCreate);
      toast.success('销售合同创建成功');
      setShowCreate(false);
      resetCreateForm();
      await loadContracts();
    } catch (err) {
      toast.error('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  // 删除合同
  const handleDelete = async (contract: SalesContractItem) => {
    const confirmed = await confirm({
      title: '删除销售合同',
      description: `确定要删除销售合同「${contract.contract_no}」吗？此操作不可撤销。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await salesContractsApi.delete(contract.id);
      toast.success('删除成功');
      await loadContracts();
    } catch (err) {
      toast.error('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        title="销售合同"
        actions={can('sales_contract', 'create') ? (
          <Button onClick={() => { resetCreateForm(); setShowCreate(true); }}>
            <Plus className="h-4 w-4" />
            新建合同
          </Button>
        ) : undefined}
      />

      {/* 搜索和筛选 */}
      <SearchFilterBar
        searchPlaceholder="搜索合同编号、客户名称..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'status',
            placeholder: '全部状态',
            options: CONTRACT_STATUS_OPTIONS,
          },
        ]}
        filterValues={{ status: filterStatus }}
        onFilterChange={(key, value) => {
          if (key === 'status') { setFilterStatus(value); setPage(1); }
        }}
      />

      {/* 合同列表 */}
      <DataTableShell
        loading={loading}
        itemCount={contracts.length}
        columns={9}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle={debouncedSearch || filterStatus ? '没有匹配的销售合同' : '暂无销售合同数据'}
      >
        <TableHeader>
          <TableRow>
            <TableHead className="px-6">合同编号</TableHead>
            <TableHead className="px-6">客户</TableHead>
            <TableHead className="px-6">币种</TableHead>
            <TableHead className="px-6">金额</TableHead>
            <TableHead className="px-6">行数</TableHead>
            <TableHead className="px-6">零库存</TableHead>
            <TableHead className="px-6">合同日期</TableHead>
            <TableHead className="px-6">状态</TableHead>
            <TableHead className="px-6 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {contracts.map(contract => (
            <TableRow key={contract.id}>
              <TableCell className="px-6 py-4">
                <button
                  onClick={() => setViewingContract(contract)}
                  className="text-left group"
                >
                  <span className="text-sm font-medium text-foreground group-hover:text-primary">
                    {contract.contract_no}
                  </span>
                </button>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {contract.customer_name || '-'}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {contract.currency}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-foreground">
                {formatAmount(contract.total_amount, contract.currency)}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {contract.line_count}
              </TableCell>
              <TableCell className="px-6 py-4">
                <Badge variant="secondary" className={contract.is_zero_stock ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}>
                  {contract.is_zero_stock ? '是' : '否'}
                </Badge>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {contract.contract_date ? formatDate(contract.contract_date) : '-'}
              </TableCell>
              <TableCell className="px-6 py-4">
                <StatusBadge status={contract.status} statusMap={CONTRACT_STATUSES} />
              </TableCell>
              <TableCell className="px-6 py-4 text-right">
                <div className="flex items-center justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => setViewingContract(contract)}
                    title="查看"
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  {can('sales_contract', 'delete') && (
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDelete(contract)}
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

      {/* 创建合同弹窗 */}
      <FormDialog
        open={showCreate}
        onOpenChange={(open) => { if (!open) setShowCreate(false); }}
        title="新建销售合同"
        size="lg"
      >
        <form onSubmit={handleCreate} className="space-y-6">
          {/* 基本信息 */}
          <FormSection title="基本信息" collapsible={false}>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="mb-1">客户 ID *</Label>
                <Input
                  type="text"
                  required
                  placeholder="请输入客户 ID"
                  value={createForm.customer_id}
                  onChange={e => setCreateForm({ ...createForm, customer_id: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">币种</Label>
                <Input
                  type="text"
                  value={createForm.currency || 'CNY'}
                  onChange={e => setCreateForm({ ...createForm, currency: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">贸易术语</Label>
                <Input
                  type="text"
                  placeholder="如 FOB, CIF, EXW..."
                  value={createForm.trade_term || ''}
                  onChange={e => setCreateForm({ ...createForm, trade_term: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">付款方式</Label>
                <Input
                  type="text"
                  placeholder="如 T/T, L/C..."
                  value={createForm.payment_method || ''}
                  onChange={e => setCreateForm({ ...createForm, payment_method: e.target.value })}
                />
              </div>
            </div>
          </FormSection>

          {/* 港口信息 */}
          <FormSection title="港口/运输信息" collapsible={false}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">装运港</Label>
                <Input
                  type="text"
                  placeholder="Port of Loading"
                  value={createForm.port_of_loading || ''}
                  onChange={e => setCreateForm({ ...createForm, port_of_loading: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">卸货港</Label>
                <Input
                  type="text"
                  placeholder="Port of Discharge"
                  value={createForm.port_of_discharge || ''}
                  onChange={e => setCreateForm({ ...createForm, port_of_discharge: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">目的地</Label>
                <Input
                  type="text"
                  placeholder="Destination"
                  value={createForm.destination || ''}
                  onChange={e => setCreateForm({ ...createForm, destination: e.target.value })}
                />
              </div>
            </div>
          </FormSection>

          {/* 日期信息 */}
          <FormSection title="日期信息" collapsible={false}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">合同日期</Label>
                <Input
                  type="date"
                  value={createForm.contract_date || ''}
                  onChange={e => setCreateForm({ ...createForm, contract_date: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">交付日期</Label>
                <Input
                  type="date"
                  value={createForm.delivery_date || ''}
                  onChange={e => setCreateForm({ ...createForm, delivery_date: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">发货日期</Label>
                <Input
                  type="date"
                  value={createForm.shipping_date || ''}
                  onChange={e => setCreateForm({ ...createForm, shipping_date: e.target.value })}
                />
              </div>
            </div>
          </FormSection>

          {/* 其他信息 */}
          <FormSection title="其他" collapsible={false}>
            <div className="space-y-4">
              <div className="flex items-center space-x-2 cursor-pointer">
                <Checkbox
                  id="is_zero_stock"
                  checked={createForm.is_zero_stock || false}
                  onCheckedChange={(checked) => setCreateForm({ ...createForm, is_zero_stock: !!checked })}
                />
                <Label htmlFor="is_zero_stock" className="cursor-pointer">零库存订单</Label>
              </div>
              <div>
                <Label className="mb-1">备注</Label>
                <Textarea
                  rows={3}
                  value={createForm.notes || ''}
                  onChange={e => setCreateForm({ ...createForm, notes: e.target.value })}
                />
              </div>
            </div>
          </FormSection>

          {/* 按钮 */}
          <FormFooter
            onCancel={() => setShowCreate(false)}
            submitText="创建"
            loading={saving}
            disabled={!createForm.customer_id.trim()}
          />
        </form>
      </FormDialog>

      {/* 合同详情弹窗 */}
      <ContractDetailModal
        isOpen={!!viewingContract}
        onClose={() => setViewingContract(null)}
        contract={viewingContract}
        onStatusChange={loadContracts}
      />
    </div>
  );
}
