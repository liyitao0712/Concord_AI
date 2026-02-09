// src/app/admin/purchase-contracts/page.tsx
// 采购合同管理页面
//
// 功能说明：
// 1. 采购合同列表（搜索、状态筛选、分页）
// 2. 新建采购合同（简版表单）
// 3. 合同详情查看 + 状态变更

'use client';

import { useState, useEffect, useCallback } from 'react';
import { purchaseContractsApi, PurchaseContract, PurchaseContractCreate } from '@/lib/api';
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

// ==================== 合同状态配置 ====================

const CONTRACT_STATUSES: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-800' },
  pending_approval: { label: '待审批', color: 'bg-yellow-100 text-yellow-800' },
  approved: { label: '已审批', color: 'bg-blue-100 text-blue-800' },
  signed: { label: '已签订', color: 'bg-indigo-100 text-indigo-800' },
  in_progress: { label: '执行中', color: 'bg-cyan-100 text-cyan-800' },
  partial_received: { label: '部分到货', color: 'bg-orange-100 text-orange-800' },
  received: { label: '已到货', color: 'bg-green-100 text-green-800' },
  completed: { label: '已完成', color: 'bg-emerald-100 text-emerald-800' },
  cancelled: { label: '已取消', color: 'bg-red-100 text-red-800' },
};

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function getStatusBadge(status: string) {
  const config = CONTRACT_STATUSES[status];
  if (!config) return <Badge variant="outline">{status}</Badge>;
  return (
    <Badge variant="outline" className={config.color}>
      {config.label}
    </Badge>
  );
}

// ==================== 日期格式化 ====================

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  } catch {
    return dateStr;
  }
}

function formatAmount(amount: number, currency?: string): string {
  const formatted = amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return currency ? `${currency} ${formatted}` : formatted;
}

// ==================== 主页面 ====================

export default function PurchaseContractsPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 列表状态
  const [contracts, setContracts] = useState<PurchaseContract[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // 新建合同弹窗
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState<PurchaseContractCreate>({
    supplier_id: '',
    currency: 'CNY',
    trade_term: '',
    payment_method: '',
    port_of_loading: '',
    port_of_discharge: '',
    contract_date: '',
    delivery_date: '',
    notes: '',
  });

  // 详情弹窗
  const [showDetail, setShowDetail] = useState(false);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const PAGE_SIZE = 20;

  // ==================== 数据加载 ====================

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await purchaseContractsApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setContracts(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // ==================== 合同操作 ====================

  const openCreateForm = () => {
    setCreateForm({
      supplier_id: '',
      currency: 'CNY',
      trade_term: '',
      payment_method: '',
      port_of_loading: '',
      port_of_discharge: '',
      contract_date: '',
      delivery_date: '',
      notes: '',
    });
    setShowCreateForm(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.supplier_id.trim()) {
      toast.error('请填写供应商 ID');
      return;
    }
    setCreateLoading(true);
    try {
      // 清理空字符串字段
      const cleaned: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(createForm)) {
        if (value !== '' && value !== null && value !== undefined) {
          cleaned[key] = value;
        }
      }
      // supplier_id 是必填项，确保保留
      cleaned.supplier_id = createForm.supplier_id;
      await purchaseContractsApi.create(cleaned as unknown as PurchaseContractCreate);
      toast.success('合同创建成功');
      setShowCreateForm(false);
      loadContracts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDelete = async (contract: PurchaseContract) => {
    const confirmed = await confirm({
      title: '删除合同',
      description: `确定删除合同「${contract.contract_no}」？此操作不可撤销。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await purchaseContractsApi.delete(contract.id);
      toast.success('合同已删除');
      loadContracts();
      if (detailData?.id === contract.id) {
        setShowDetail(false);
        setDetailData(null);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  // ==================== 详情操作 ====================

  const loadDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const detail = await purchaseContractsApi.get(id);
      setDetailData(detail);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const openDetail = (contract: PurchaseContract) => {
    setShowDetail(true);
    loadDetail(contract.id);
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!detailData) return;
    try {
      await purchaseContractsApi.updateStatus(detailData.id, newStatus);
      toast.success(`状态已更新为「${CONTRACT_STATUSES[newStatus]?.label || newStatus}」`);
      loadDetail(detailData.id);
      loadContracts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '状态更新失败');
    }
  };

  // ==================== 分页 ====================

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">采购合同</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理采购合同</p>
        </div>
        {can('purchase_contract', 'create') && (
        <Button onClick={openCreateForm}>
          <Plus />
          新建合同
        </Button>
        )}
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <Input
          type="text"
          placeholder="搜索合同编号/供应商名称..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className={selectClass}
        >
          <option value="">全部状态</option>
          {Object.entries(CONTRACT_STATUSES).map(([value, { label }]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 合同列表 */}
      <Card className="py-0">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : contracts.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无采购合同数据</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">合同编号</TableHead>
                <TableHead className="px-6">供应商</TableHead>
                <TableHead className="px-6">币种</TableHead>
                <TableHead className="px-6 text-right">金额</TableHead>
                <TableHead className="px-6 text-center">行数</TableHead>
                <TableHead className="px-6">合同日期</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contracts.map((contract) => (
                <TableRow key={contract.id}>
                  <TableCell className="px-6 py-4">
                    <button
                      onClick={() => openDetail(contract)}
                      className="text-sm font-medium text-primary hover:text-primary/80"
                    >
                      {contract.contract_no}
                    </button>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {contract.supplier_name || '-'}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {contract.currency}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-right font-mono">
                    {formatAmount(contract.total_amount)}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-center text-muted-foreground">
                    {contract.line_count}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {formatDate(contract.contract_date)}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    {getStatusBadge(contract.status)}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openDetail(contract)}>
                      <Eye className="size-3.5" />
                      查看
                    </Button>
                    {can('purchase_contract', 'delete') && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleDelete(contract)}
                    >
                      <Trash2 className="size-3.5" />
                      删除
                    </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="px-6 py-3 flex items-center justify-between border-t">
            <span className="text-sm text-muted-foreground">共 {total} 条</span>
            <div className="flex gap-2 items-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="size-4" />
                上一页
              </Button>
              <span className="px-3 py-1 text-sm">{page} / {totalPages}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                下一页
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ==================== 新建合同弹窗 ==================== */}
      <Dialog open={showCreateForm} onOpenChange={(open) => !open && setShowCreateForm(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>新建采购合同</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-6">
            {/* 基本信息 */}
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-3">基本信息</h4>
              <Separator className="mb-3" />
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label className="mb-1">供应商 ID *</Label>
                  <Input
                    type="text"
                    required
                    placeholder="请输入供应商 ID"
                    value={createForm.supplier_id}
                    onChange={(e) => setCreateForm({ ...createForm, supplier_id: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="mb-1">币种</Label>
                  <select
                    className={`w-full ${selectClass}`}
                    value={createForm.currency || 'CNY'}
                    onChange={(e) => setCreateForm({ ...createForm, currency: e.target.value })}
                  >
                    <option value="CNY">CNY - 人民币</option>
                    <option value="USD">USD - 美元</option>
                    <option value="EUR">EUR - 欧元</option>
                    <option value="GBP">GBP - 英镑</option>
                    <option value="JPY">JPY - 日元</option>
                    <option value="HKD">HKD - 港币</option>
                  </select>
                </div>
                <div>
                  <Label className="mb-1">贸易术语</Label>
                  <Input
                    type="text"
                    placeholder="如 FOB, CIF, EXW"
                    value={createForm.trade_term || ''}
                    onChange={(e) => setCreateForm({ ...createForm, trade_term: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="mb-1">付款方式</Label>
                  <Input
                    type="text"
                    placeholder="如 T/T, L/C"
                    value={createForm.payment_method || ''}
                    onChange={(e) => setCreateForm({ ...createForm, payment_method: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="mb-1">合同日期</Label>
                  <Input
                    type="date"
                    value={createForm.contract_date || ''}
                    onChange={(e) => setCreateForm({ ...createForm, contract_date: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* 物流信息 */}
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-3">物流信息</h4>
              <Separator className="mb-3" />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="mb-1">装货港</Label>
                  <Input
                    type="text"
                    placeholder="Port of Loading"
                    value={createForm.port_of_loading || ''}
                    onChange={(e) => setCreateForm({ ...createForm, port_of_loading: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="mb-1">卸货港</Label>
                  <Input
                    type="text"
                    placeholder="Port of Discharge"
                    value={createForm.port_of_discharge || ''}
                    onChange={(e) => setCreateForm({ ...createForm, port_of_discharge: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="mb-1">交货日期</Label>
                  <Input
                    type="date"
                    value={createForm.delivery_date || ''}
                    onChange={(e) => setCreateForm({ ...createForm, delivery_date: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* 备注 */}
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-3">其他</h4>
              <Separator className="mb-3" />
              <div>
                <Label className="mb-1">备注</Label>
                <Textarea
                  rows={3}
                  value={createForm.notes || ''}
                  onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                  placeholder="合同相关备注信息"
                />
              </div>
            </div>

            {/* 按钮 */}
            <Separator />
            <div className="flex justify-end space-x-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateForm(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={createLoading || !createForm.supplier_id.trim()}
              >
                {createLoading ? '创建中...' : '创建合同'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* ==================== 合同详情弹窗 ==================== */}
      <Dialog open={showDetail} onOpenChange={(open) => !open && setShowDetail(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          {detailLoading || !detailData ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : (
            <>
              {/* 合同头部信息 */}
              <DialogHeader>
                <DialogTitle className="text-xl">
                  合同 {detailData.contract_no}
                </DialogTitle>
                <div className="flex items-center gap-3 mt-2">
                  {getStatusBadge(detailData.status)}
                  {detailData.supplier_name && (
                    <span className="text-sm text-muted-foreground">供应商：{detailData.supplier_name}</span>
                  )}
                </div>
              </DialogHeader>

              {/* 状态变更按钮 */}
              <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">状态变更</h4>
                <Separator className="mb-3" />
                <div className="flex flex-wrap gap-2">
                  {Object.entries(CONTRACT_STATUSES).map(([statusKey, { label }]) => (
                    <Button
                      key={statusKey}
                      variant={detailData.status === statusKey ? 'default' : 'outline'}
                      size="sm"
                      disabled={detailData.status === statusKey}
                      onClick={() => handleStatusChange(statusKey)}
                    >
                      {label}
                    </Button>
                  ))}
                </div>
              </div>

              <Separator />

              {/* 合同详情网格 */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">合同编号：</span>
                  <span className="font-medium">{detailData.contract_no}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">供应商：</span>
                  <span>{detailData.supplier_name || detailData.supplier_id}</span>
                </div>
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
                {detailData.payment_terms && (
                  <div>
                    <span className="text-muted-foreground">付款条款：</span>
                    <span>{detailData.payment_terms}</span>
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
                <div>
                  <span className="text-muted-foreground">合同日期：</span>
                  <span>{formatDate(detailData.contract_date)}</span>
                </div>
                {detailData.delivery_date && (
                  <div>
                    <span className="text-muted-foreground">交货日期：</span>
                    <span>{formatDate(detailData.delivery_date)}</span>
                  </div>
                )}
                {detailData.expected_arrival_date && (
                  <div>
                    <span className="text-muted-foreground">预计到货：</span>
                    <span>{formatDate(detailData.expected_arrival_date)}</span>
                  </div>
                )}
                {detailData.expiry_date && (
                  <div>
                    <span className="text-muted-foreground">到期日：</span>
                    <span>{formatDate(detailData.expiry_date)}</span>
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
                  <span>{formatDate(detailData.created_at)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">更新时间：</span>
                  <span>{formatDate(detailData.updated_at)}</span>
                </div>
                {detailData.tags && detailData.tags.length > 0 && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">标签：</span>
                    {detailData.tags.map((tag: string) => (
                      <Badge key={tag} variant="secondary" className="mr-1">
                        {tag}
                      </Badge>
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
