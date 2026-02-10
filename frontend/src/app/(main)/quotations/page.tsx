// src/app/admin/quotations/page.tsx
// 报价单管理页面
//
// 功能说明：
// 1. 报价单列表（搜索、状态筛选、分页）
// 2. 新建报价单（简版表单）
// 3. 报价单详情查看 + 状态变更

'use client';

import { useState, useEffect, useCallback } from 'react';
import { quotationsApi, Quotation, QuotationCreate } from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
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
import { ErrorAlert } from '@/components/ErrorAlert';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { FormSection } from '@/components/FormSection';
import { StatusBadge, type StatusConfig } from '@/components/StatusBadge';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { formatDate } from '@/lib/format';
import { usePermission } from '@/hooks/usePermission';

// ==================== 状态配置 ====================

const QUOTATION_STATUSES: Record<string, StatusConfig> = {
  draft: { label: '草稿', color: 'draft' },
  pending_approval: { label: '待审批', color: 'pending' },
  sent: { label: '已发送', color: 'confirmed' },
  accepted: { label: '已接受', color: 'approved' },
  rejected: { label: '已拒绝', color: 'rejected' },
  expired: { label: '已过期', color: 'high' },
  cancelled: { label: '已取消', color: 'cancelled' },
};

// 状态标签映射（用于 handleStatusChange toast 等纯文本场景）
const STATUS_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(QUOTATION_STATUSES).map(([k, v]) => [k, v.label])
);

const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function formatAmount(amount: number, currency?: string): string {
  const formatted = amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return currency ? `${currency} ${formatted}` : formatted;
}

// ==================== 主页面 ====================

export default function QuotationsPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState<QuotationCreate>({
    customer_id: '',
    currency: 'USD',
    trade_term: '',
    payment_method: '',
    port_of_loading: '',
    port_of_discharge: '',
    destination: '',
    quotation_date: '',
    valid_until: '',
    notes: '',
  });

  const [showDetail, setShowDetail] = useState(false);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const PAGE_SIZE = 20;

  // 搜索防抖
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const loadQuotations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await quotationsApi.list({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
      });
      setQuotations(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, statusFilter]);

  useEffect(() => {
    loadQuotations();
  }, [loadQuotations]);

  const openCreateForm = () => {
    setCreateForm({
      customer_id: '',
      currency: 'USD',
      trade_term: '',
      payment_method: '',
      port_of_loading: '',
      port_of_discharge: '',
      destination: '',
      quotation_date: '',
      valid_until: '',
      notes: '',
    });
    setShowCreateForm(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.customer_id?.trim()) {
      toast.error('请填写客户 ID');
      return;
    }
    setCreateLoading(true);
    try {
      const cleaned: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(createForm)) {
        if (value !== '' && value !== null && value !== undefined) {
          cleaned[key] = value;
        }
      }
      cleaned.customer_id = createForm.customer_id;
      await quotationsApi.create(cleaned as unknown as QuotationCreate);
      toast.success('报价单创建成功');
      setShowCreateForm(false);
      loadQuotations();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDelete = async (quotation: Quotation) => {
    const confirmed = await confirm({
      title: '删除报价单',
      description: `确定删除报价单「${quotation.quotation_no}」？此操作不可撤销。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await quotationsApi.delete(quotation.id);
      toast.success('报价单已删除');
      loadQuotations();
      if (detailData?.id === quotation.id) {
        setShowDetail(false);
        setDetailData(null);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const loadDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const detail = await quotationsApi.get(id);
      setDetailData(detail);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const openDetail = (quotation: Quotation) => {
    setShowDetail(true);
    loadDetail(quotation.id);
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!detailData) return;
    try {
      await quotationsApi.updateStatus(detailData.id, newStatus);
      toast.success(`状态已更新为「${STATUS_LABELS[newStatus] || newStatus}」`);
      loadDetail(detailData.id);
      loadQuotations();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '状态更新失败');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <PageHeader
        title="报价单管理"
        actions={can('quotation', 'create') ? (
          <Button onClick={openCreateForm}>
            <Plus />
            新建报价单
          </Button>
        ) : undefined}
      />

      <SearchFilterBar
        searchPlaceholder="搜索报价单编号..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'status',
            placeholder: '全部状态',
            options: Object.entries(QUOTATION_STATUSES).map(([value, { label }]) => ({ value, label })),
          },
        ]}
        filterValues={{ status: statusFilter }}
        onFilterChange={(key, value) => {
          if (key === 'status') { setStatusFilter(value); setPage(1); }
        }}
      />

      {error && <ErrorAlert message={error} onRetry={loadQuotations} />}

      <DataTableShell
        loading={loading}
        itemCount={quotations.length}
        columns={8}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle="暂无报价单数据"
      >
        <TableHeader>
          <TableRow>
            <TableHead className="px-6">报价单编号</TableHead>
            <TableHead className="px-6">客户</TableHead>
            <TableHead className="px-6">币种</TableHead>
            <TableHead className="px-6 text-right">金额</TableHead>
            <TableHead className="px-6 text-center">行数</TableHead>
            <TableHead className="px-6">报价日期</TableHead>
            <TableHead className="px-6">状态</TableHead>
            <TableHead className="px-6 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {quotations.map((q) => (
            <TableRow key={q.id}>
              <TableCell className="px-6 py-4">
                <button
                  onClick={() => openDetail(q)}
                  className="text-sm font-medium text-primary hover:text-primary/80"
                >
                  {q.quotation_no}
                </button>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {q.customer_name || '-'}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {q.currency}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-right font-mono">
                {formatAmount(q.total_amount)}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-center text-muted-foreground">
                {q.line_count}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {q.quotation_date ? formatDate(q.quotation_date) : '-'}
              </TableCell>
              <TableCell className="px-6 py-4">
                <StatusBadge status={q.status} statusMap={QUOTATION_STATUSES} fallbackLabel={q.status} />
              </TableCell>
              <TableCell className="px-6 py-4 text-right space-x-1">
                <Button variant="ghost" size="sm" onClick={() => openDetail(q)}>
                  <Eye className="size-3.5" />
                  查看
                </Button>
                {can('quotation', 'delete') && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDelete(q)}
                >
                  <Trash2 className="size-3.5" />
                  删除
                </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </DataTableShell>

      {/* 新建报价单弹窗 */}
      <FormDialog
        open={showCreateForm}
        onOpenChange={(open) => !open && setShowCreateForm(false)}
        title="新建报价单"
        size="md"
      >
        <form onSubmit={handleCreate} className="space-y-6">
          <FormSection title="基本信息" collapsible={false}>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="mb-1">客户 ID *</Label>
                <Input type="text" required placeholder="请输入客户 ID" value={createForm.customer_id} onChange={(e) => setCreateForm({ ...createForm, customer_id: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">币种</Label>
                <select className={`w-full ${selectClass}`} value={createForm.currency || 'USD'} onChange={(e) => setCreateForm({ ...createForm, currency: e.target.value })}>
                  <option value="USD">USD - 美元</option>
                  <option value="CNY">CNY - 人民币</option>
                  <option value="EUR">EUR - 欧元</option>
                  <option value="GBP">GBP - 英镑</option>
                  <option value="JPY">JPY - 日元</option>
                  <option value="HKD">HKD - 港币</option>
                </select>
              </div>
              <div>
                <Label className="mb-1">贸易术语</Label>
                <Input type="text" placeholder="如 FOB, CIF, EXW" value={createForm.trade_term || ''} onChange={(e) => setCreateForm({ ...createForm, trade_term: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">付款方式</Label>
                <Input type="text" placeholder="如 T/T, L/C" value={createForm.payment_method || ''} onChange={(e) => setCreateForm({ ...createForm, payment_method: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">报价日期</Label>
                <Input type="date" value={createForm.quotation_date || ''} onChange={(e) => setCreateForm({ ...createForm, quotation_date: e.target.value })} />
              </div>
            </div>
          </FormSection>

          <FormSection title="物流信息" collapsible={false}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">装货港</Label>
                <Input type="text" placeholder="Port of Loading" value={createForm.port_of_loading || ''} onChange={(e) => setCreateForm({ ...createForm, port_of_loading: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">卸货港</Label>
                <Input type="text" placeholder="Port of Discharge" value={createForm.port_of_discharge || ''} onChange={(e) => setCreateForm({ ...createForm, port_of_discharge: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">最终目的地</Label>
                <Input type="text" placeholder="Destination" value={createForm.destination || ''} onChange={(e) => setCreateForm({ ...createForm, destination: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">有效期至</Label>
                <Input type="date" value={createForm.valid_until || ''} onChange={(e) => setCreateForm({ ...createForm, valid_until: e.target.value })} />
              </div>
            </div>
          </FormSection>

          <FormSection title="其他" collapsible={false}>
            <div>
              <Label className="mb-1">备注</Label>
              <Textarea rows={3} value={createForm.notes || ''} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} placeholder="报价单相关备注信息" />
            </div>
          </FormSection>

          <FormFooter
            onCancel={() => setShowCreateForm(false)}
            submitText="创建报价单"
            loading={createLoading}
            disabled={!createForm.customer_id?.trim()}
          />
        </form>
      </FormDialog>

      {/* 报价单详情弹窗 */}
      <Dialog open={showDetail} onOpenChange={(open) => !open && setShowDetail(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          {detailLoading || !detailData ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl">
                  报价单 {detailData.quotation_no}
                </DialogTitle>
                <div className="flex items-center gap-3 mt-2">
                  <StatusBadge status={detailData.status} statusMap={QUOTATION_STATUSES} fallbackLabel={detailData.status} />
                  {detailData.customer_name && (
                    <span className="text-sm text-muted-foreground">客户：{detailData.customer_name}</span>
                  )}
                </div>
              </DialogHeader>

              <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">状态变更</h4>
                <Separator className="mb-3" />
                <div className="flex flex-wrap gap-2">
                  {Object.entries(QUOTATION_STATUSES).map(([statusKey, { label }]) => (
                    <Button key={statusKey} variant={detailData.status === statusKey ? 'default' : 'outline'} size="sm" disabled={detailData.status === statusKey} onClick={() => handleStatusChange(statusKey)}>
                      {label}
                    </Button>
                  ))}
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">报价单编号：</span>
                  <span className="font-medium">{detailData.quotation_no}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">客户：</span>
                  <span>{detailData.customer_name || detailData.customer_id}</span>
                </div>
                {detailData.linked_client_rfq_no && (
                  <div>
                    <span className="text-muted-foreground">来源询价单：</span>
                    <span>{detailData.linked_client_rfq_no}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">币种：</span>
                  <span>{detailData.currency}</span>
                </div>
                {detailData.exchange_rate && (
                  <div>
                    <span className="text-muted-foreground">汇率：</span>
                    <span>{detailData.exchange_rate}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">小计：</span>
                  <span className="font-mono">{formatAmount(detailData.subtotal, detailData.currency)}</span>
                </div>
                {detailData.discount_amount > 0 && (
                  <div>
                    <span className="text-muted-foreground">折扣：</span>
                    <span className="font-mono text-orange-600">-{formatAmount(detailData.discount_amount, detailData.currency)}</span>
                  </div>
                )}
                {detailData.tax_amount > 0 && (
                  <div>
                    <span className="text-muted-foreground">税额：</span>
                    <span className="font-mono">{formatAmount(detailData.tax_amount, detailData.currency)}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">总金额：</span>
                  <span className="font-mono font-semibold">{formatAmount(detailData.total_amount, detailData.currency)}</span>
                </div>
                {detailData.commission_rate != null && (
                  <div>
                    <span className="text-muted-foreground">佣金率：</span>
                    <span>{detailData.commission_rate}%</span>
                  </div>
                )}
                {detailData.commission_amount != null && (
                  <div>
                    <span className="text-muted-foreground">佣金：</span>
                    <span className="font-mono">{formatAmount(detailData.commission_amount, detailData.currency)}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">行项目数：</span>
                  <span>{detailData.line_count}</span>
                </div>
                {detailData.trade_term && (
                  <div>
                    <span className="text-muted-foreground">贸易术语：</span>
                    <span>{detailData.trade_term}</span>
                  </div>
                )}
                {detailData.payment_method && (
                  <div>
                    <span className="text-muted-foreground">付款方式：</span>
                    <span>{detailData.payment_method}</span>
                  </div>
                )}
                {detailData.port_of_loading && (
                  <div>
                    <span className="text-muted-foreground">装货港：</span>
                    <span>{detailData.port_of_loading}</span>
                  </div>
                )}
                {detailData.port_of_discharge && (
                  <div>
                    <span className="text-muted-foreground">卸货港：</span>
                    <span>{detailData.port_of_discharge}</span>
                  </div>
                )}
                {detailData.destination && (
                  <div>
                    <span className="text-muted-foreground">最终目的地：</span>
                    <span>{detailData.destination}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">报价日期：</span>
                  <span>{detailData.quotation_date ? formatDate(detailData.quotation_date) : '-'}</span>
                </div>
                {detailData.valid_until && (
                  <div>
                    <span className="text-muted-foreground">有效期至：</span>
                    <span>{formatDate(detailData.valid_until)}</span>
                  </div>
                )}
                {detailData.created_by && (
                  <div>
                    <span className="text-muted-foreground">创建人：</span>
                    <span>{detailData.created_by}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">创建时间：</span>
                  <span>{detailData.created_at ? formatDate(detailData.created_at) : '-'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">更新时间：</span>
                  <span>{detailData.updated_at ? formatDate(detailData.updated_at) : '-'}</span>
                </div>
                {detailData.tags && detailData.tags.length > 0 && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">标签：</span>
                    {detailData.tags.map((tag: string) => (
                      <Badge key={tag} variant="secondary" className="mr-1">{tag}</Badge>
                    ))}
                  </div>
                )}
                {detailData.notes && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">备注：</span>
                    <span>{detailData.notes}</span>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
