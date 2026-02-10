// src/app/admin/suppliers/page.tsx
// 供应商管理页面
//
// 功能说明：
// 1. 供应商列表（搜索、筛选、分页）
// 2. 新建/编辑供应商（分区表单 + AI 检索）
// 3. 供应商详情 + 联系人管理
// 4. 联系人新建/编辑

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  suppliersApi,
  supplierContactsApi,
  tradeTermsApi,
  paymentMethodsApi,
  Supplier,
  SupplierDetail,
  SupplierContact,
  SupplierCreate,
  SupplierUpdate,
  SupplierContactCreate,
  SupplierContactUpdate,
  TradeTerm,
  PaymentMethod,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { Plus, Pencil, Trash2, Loader2, Sparkles } from 'lucide-react';
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
import { TagInput } from '@/components/TagInput';
import { StatusBadge, type StatusConfig } from '@/components/StatusBadge';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { ErrorAlert } from '@/components/ErrorAlert';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';

// ==================== 供应商等级配置 ====================

const SUPPLIER_LEVELS: Record<string, StatusConfig> = {
  potential: { label: '潜在', color: 'potential' },
  normal: { label: '普通', color: 'normal' },
  important: { label: '重要', color: 'important' },
  strategic: { label: '战略', color: 'strategic' },
};

const ACTIVE_STATUS: Record<string, StatusConfig> = {
  active: { label: '活跃', color: 'active' },
  inactive: { label: '停用', color: 'inactive' },
};

const SUPPLIER_SOURCES = [
  { value: 'email', label: '邮件' },
  { value: 'exhibition', label: '展会' },
  { value: 'referral', label: '推荐' },
  { value: 'website', label: '网站' },
  { value: '1688', label: '1688' },
  { value: 'other', label: '其他' },
];

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ==================== 供应商表单 ====================

function SupplierForm({
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  initial?: Partial<Supplier>;
  onSubmit: (data: SupplierCreate | SupplierUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const isCreateMode = !initial;
  const [form, setForm] = useState<SupplierCreate>({
    name: initial?.name || '',
    short_name: initial?.short_name || '',
    country: initial?.country || '',
    region: initial?.region || '',
    industry: initial?.industry || '',
    company_size: initial?.company_size || '',
    main_products: initial?.main_products || '',
    supplier_level: initial?.supplier_level || 'normal',
    email: initial?.email || '',
    phone: initial?.phone || '',
    website: initial?.website || '',
    address: initial?.address || '',
    payment_terms: initial?.payment_terms || '',
    shipping_terms: initial?.shipping_terms || '',
    is_active: initial?.is_active ?? true,
    source: initial?.source || '',
    notes: initial?.notes || '',
    tags: initial?.tags || [],
  });
  const [tradeTerms, setTradeTerms] = useState<TradeTerm[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [aiQuery, setAiQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');

  // 加载贸易术语和付款方式
  useEffect(() => {
    tradeTermsApi.list({ page_size: 50, is_current: true }).then(resp => {
      setTradeTerms(resp.items);
    }).catch(() => {});
    paymentMethodsApi.list({ page_size: 50 }).then(resp => {
      setPaymentMethods(resp.items);
    }).catch(() => {});
  }, []);

  // AI 检索自动填充
  const handleAiLookup = async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiError('');
    try {
      const result = await suppliersApi.aiLookup(aiQuery.trim());
      if (result.error) {
        setAiError(result.error);
        return;
      }
      setForm(prev => ({
        ...prev,
        name: result.name || aiQuery.trim(),
        short_name: result.short_name || '',
        country: result.country || '',
        region: result.region || '',
        industry: result.industry || '',
        company_size: result.company_size || '',
        main_products: result.main_products || '',
        email: result.email || '',
        phone: result.phone || '',
        website: result.website || '',
        address: result.address || '',
        notes: result.notes || '',
        tags: result.tags || [],
      }));
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'AI 检索失败');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 清理空字符串为 undefined（用于 update）
    const cleaned: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(form)) {
      if (value === '' || value === null) {
        if (key === 'name' || key === 'is_active' || key === 'supplier_level') {
          cleaned[key] = value;
        }
      } else {
        cleaned[key] = value;
      }
    }
    onSubmit(cleaned as unknown as SupplierCreate);
  };

  const handleTagsChange = (tags: string[]) => {
    setForm({ ...form, tags });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* AI 供应商检索 */}
      {isCreateMode && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <Label className="mb-1">AI 供应商检索</Label>
          <div className="flex items-center gap-2">
            <Input
              type="text"
              className="flex-1"
              placeholder="输入公司名称、关键词等，AI 将自动检索并填充所有字段"
              value={aiQuery}
              onChange={e => setAiQuery(e.target.value)}
            />
            <Button
              type="button"
              onClick={handleAiLookup}
              disabled={aiLoading || !aiQuery.trim()}
              className="bg-purple-600 hover:bg-purple-700 whitespace-nowrap"
            >
              {aiLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  AI 检索中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  AI 填充
                </>
              )}
            </Button>
          </div>
          {aiError && (
            <p className="mt-1 text-xs text-destructive">{aiError}</p>
          )}
        </div>
      )}

      {/* 基本信息 */}
      <FormSection title="基本信息" collapsible={false}>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Label className="mb-1">公司全称 *</Label>
            <Input
              type="text"
              required
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">简称/别名</Label>
            <Input
              type="text"
              value={form.short_name || ''}
              onChange={e => setForm({ ...form, short_name: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">国家</Label>
            <Input
              type="text"
              value={form.country || ''}
              onChange={e => setForm({ ...form, country: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">地区/洲</Label>
            <Input
              type="text"
              value={form.region || ''}
              onChange={e => setForm({ ...form, region: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">行业</Label>
            <Input
              type="text"
              value={form.industry || ''}
              onChange={e => setForm({ ...form, industry: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">供应商等级</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.supplier_level}
              onChange={e => setForm({ ...form, supplier_level: e.target.value })}
            >
              {Object.entries(SUPPLIER_LEVELS).map(([value, { label }]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      </FormSection>

      {/* 业务信息 */}
      <FormSection title="业务信息" collapsible={false}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">公司规模</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.company_size || ''}
              onChange={e => setForm({ ...form, company_size: e.target.value })}
            >
              <option value="">未设置</option>
              <option value="small">小型</option>
              <option value="medium">中型</option>
              <option value="large">大型</option>
              <option value="enterprise">企业级</option>
            </select>
          </div>
          <div>
            <Label className="mb-1">供应商来源</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.source || ''}
              onChange={e => setForm({ ...form, source: e.target.value })}
            >
              <option value="">未设置</option>
              {SUPPLIER_SOURCES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <Label className="mb-1">主营产品</Label>
            <Textarea
              rows={2}
              value={form.main_products || ''}
              onChange={e => setForm({ ...form, main_products: e.target.value })}
              placeholder="描述供应商的主要产品线"
            />
          </div>
          <div className="flex items-end">
            <div className="flex items-center space-x-2 cursor-pointer">
              <Checkbox
                id="is_active"
                checked={form.is_active}
                onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })}
              />
              <Label htmlFor="is_active" className="cursor-pointer">活跃供应商</Label>
            </div>
          </div>
        </div>
      </FormSection>

      {/* 联系信息 */}
      <FormSection title="联系信息" collapsible={false}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">公司邮箱</Label>
            <Input
              type="email"
              value={form.email || ''}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司电话</Label>
            <Input
              type="text"
              value={form.phone || ''}
              onChange={e => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司网站</Label>
            <Input
              type="text"
              value={form.website || ''}
              onChange={e => setForm({ ...form, website: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司地址</Label>
            <Input
              type="text"
              value={form.address || ''}
              onChange={e => setForm({ ...form, address: e.target.value })}
            />
          </div>
        </div>
      </FormSection>

      {/* 贸易信息 */}
      <FormSection title="贸易信息" collapsible={false}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">付款条款</Label>
            <select
              className={selectClass}
              value={form.payment_terms || ''}
              onChange={e => setForm({ ...form, payment_terms: e.target.value })}
            >
              <option value="">请选择付款方式</option>
              {paymentMethods.map(pm => (
                <option key={pm.id} value={pm.code}>{pm.code} - {pm.name_zh}</option>
              ))}
            </select>
          </div>
          <div>
            <Label className="mb-1">贸易术语 (Incoterms)</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.shipping_terms || ''}
              onChange={e => setForm({ ...form, shipping_terms: e.target.value })}
            >
              <option value="">未设置</option>
              {tradeTerms.map(t => (
                <option key={t.id} value={t.code}>
                  {t.code} - {t.name_zh}
                </option>
              ))}
            </select>
          </div>
        </div>
      </FormSection>

      {/* 标签和备注 */}
      <FormSection title="其他" collapsible={false}>
        <div className="space-y-4">
          <TagInput tags={form.tags || []} onChange={handleTagsChange} />
          <div>
            <Label className="mb-1">备注</Label>
            <Textarea
              rows={3}
              value={form.notes || ''}
              onChange={e => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </FormSection>

      {/* 按钮 */}
      <FormFooter onCancel={onCancel} loading={loading} disabled={!form.name.trim()} />
    </form>
  );
}

// ==================== 主页面 ====================

export default function SuppliersPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 列表状态
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [levelFilter, setLevelFilter] = useState('');

  // 供应商表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  // 详情弹窗
  const [showDetail, setShowDetail] = useState(false);
  const [detailData, setDetailData] = useState<SupplierDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 联系人表单弹窗
  const [showContactForm, setShowContactForm] = useState(false);
  const [editingContact, setEditingContact] = useState<SupplierContact | null>(null);
  const [contactFormData, setContactFormData] = useState<SupplierContactCreate>({
    supplier_id: '',
    name: '',
  });
  const [contactFormLoading, setContactFormLoading] = useState(false);

  const PAGE_SIZE = 20;

  // ==================== 数据加载 ====================

  const loadSuppliers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await suppliersApi.list({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
        supplier_level: levelFilter || undefined,
      });
      setSuppliers(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, levelFilter]);

  useEffect(() => {
    loadSuppliers();
  }, [loadSuppliers]);

  // 搜索/筛选变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, levelFilter]);

  // ==================== 供应商操作 ====================

  const openCreateForm = () => {
    setEditingSupplier(null);
    setShowForm(true);
  };

  const openEditForm = (supplier: Supplier) => {
    setEditingSupplier(supplier);
    setShowForm(true);
  };

  const handleSubmitSupplier = async (data: SupplierCreate | SupplierUpdate) => {
    setFormLoading(true);
    try {
      if (editingSupplier) {
        await suppliersApi.update(editingSupplier.id, data as SupplierUpdate);
      } else {
        await suppliersApi.create(data as SupplierCreate);
      }
      setShowForm(false);
      loadSuppliers();
      // 如果正在查看详情，也刷新
      if (detailData && editingSupplier && detailData.id === editingSupplier.id) {
        loadDetail(editingSupplier.id);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteSupplier = async (supplier: Supplier) => {
    const confirmed = await confirm({
      title: '删除供应商',
      description: `确定删除供应商「${supplier.name}」？将同时删除其所有联系人。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await suppliersApi.delete(supplier.id);
      loadSuppliers();
      if (detailData?.id === supplier.id) {
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
      const detail = await suppliersApi.get(id);
      setDetailData(detail);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const openDetail = (supplier: Supplier) => {
    setShowDetail(true);
    loadDetail(supplier.id);
  };

  // ==================== 联系人操作 ====================

  const openCreateContact = () => {
    if (!detailData) return;
    setEditingContact(null);
    setContactFormData({ supplier_id: detailData.id, name: '' });
    setShowContactForm(true);
  };

  const openEditContact = (contact: SupplierContact) => {
    setEditingContact(contact);
    setContactFormData({
      supplier_id: contact.supplier_id,
      name: contact.name,
      title: contact.title || undefined,
      department: contact.department || undefined,
      email: contact.email || undefined,
      phone: contact.phone || undefined,
      mobile: contact.mobile || undefined,
      is_primary: contact.is_primary,
      notes: contact.notes || undefined,
    });
    setShowContactForm(true);
  };

  const handleSubmitContact = async () => {
    if (!contactFormData.name.trim()) return;
    setContactFormLoading(true);
    try {
      if (editingContact) {
        const { supplier_id, ...updateData } = contactFormData;
        await supplierContactsApi.update(editingContact.id, updateData as SupplierContactUpdate);
      } else {
        await supplierContactsApi.create(contactFormData);
      }
      setShowContactForm(false);
      if (detailData) loadDetail(detailData.id);
      loadSuppliers();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setContactFormLoading(false);
    }
  };

  const handleDeleteContact = async (contact: SupplierContact) => {
    const confirmed = await confirm({
      title: '删除联系人',
      description: `确定删除联系人「${contact.name}」？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await supplierContactsApi.delete(contact.id);
      if (detailData) loadDetail(detailData.id);
      loadSuppliers();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  // ==================== 分页 ====================

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <PageHeader
        title="供应商管理"
        description="管理供应商信息和联系人"
        actions={
          can('supplier', 'create') ? (
            <Button onClick={openCreateForm}>
              <Plus />
              新增供应商
            </Button>
          ) : undefined
        }
      />

      {/* 搜索和筛选 */}
      <SearchFilterBar
        searchPlaceholder="搜索公司名/简称/邮箱..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'level',
            placeholder: '全部等级',
            options: Object.entries(SUPPLIER_LEVELS).map(([value, { label }]) => ({
              value,
              label,
            })),
          },
        ]}
        filterValues={{ level: levelFilter }}
        onFilterChange={(key, value) => {
          if (key === 'level') setLevelFilter(value);
        }}
      />

      {/* 错误信息 */}
      {error && <ErrorAlert message={error} onRetry={loadSuppliers} />}

      {/* 供应商列表 */}
      <DataTableShell
        loading={loading}
        itemCount={suppliers.length}
        columns={7}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle="暂无供应商数据"
      >
        <TableHeader>
          <TableRow>
            <TableHead className="px-6">公司名称</TableHead>
            <TableHead className="px-6">国家</TableHead>
            <TableHead className="px-6">主营产品</TableHead>
            <TableHead className="px-6">等级</TableHead>
            <TableHead className="px-6">联系人</TableHead>
            <TableHead className="px-6">状态</TableHead>
            <TableHead className="px-6 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {suppliers.map((supplier) => (
            <TableRow key={supplier.id}>
              <TableCell className="px-6 py-4">
                <button
                  onClick={() => openDetail(supplier)}
                  className="text-sm font-medium text-primary hover:text-primary/80"
                >
                  {supplier.name}
                </button>
                {supplier.short_name && (
                  <span className="ml-2 text-xs text-muted-foreground">({supplier.short_name})</span>
                )}
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">{supplier.country || '-'}</TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground max-w-xs truncate">{supplier.main_products || '-'}</TableCell>
              <TableCell className="px-6 py-4">
                <StatusBadge status={supplier.supplier_level} statusMap={SUPPLIER_LEVELS} />
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">{supplier.contact_count}</TableCell>
              <TableCell className="px-6 py-4">
                <StatusBadge status={supplier.is_active ? 'active' : 'inactive'} statusMap={ACTIVE_STATUS} />
              </TableCell>
              <TableCell className="px-6 py-4 text-right space-x-1">
                {can('supplier', 'update') && (
                <Button variant="ghost" size="sm" onClick={() => openEditForm(supplier)}>
                  <Pencil className="size-3.5" />
                  编辑
                </Button>
                )}
                {can('supplier', 'delete') && (
                <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteSupplier(supplier)}>
                  <Trash2 className="size-3.5" />
                  删除
                </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </DataTableShell>

      {/* ==================== 供应商表单弹窗 ==================== */}
      <FormDialog
        open={showForm}
        onOpenChange={(open) => !open && setShowForm(false)}
        title={editingSupplier ? '编辑供应商' : '新增供应商'}
        size="lg"
      >
        <SupplierForm
          initial={editingSupplier || undefined}
          onSubmit={handleSubmitSupplier}
          onCancel={() => setShowForm(false)}
          loading={formLoading}
        />
      </FormDialog>

      {/* ==================== 供应商详情弹窗 ==================== */}
      <Dialog open={showDetail} onOpenChange={(open) => !open && setShowDetail(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
          {detailLoading || !detailData ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : (
            <>
              {/* 供应商基本信息 */}
              <DialogHeader>
                <DialogTitle className="text-xl">
                  {detailData.name}
                  {detailData.short_name && (
                    <span className="ml-2 text-sm text-muted-foreground font-normal">({detailData.short_name})</span>
                  )}
                </DialogTitle>
                <div className="flex items-center gap-3 mt-2">
                  <StatusBadge status={detailData.supplier_level} statusMap={SUPPLIER_LEVELS} />
                  {detailData.country && <span className="text-sm text-muted-foreground">{detailData.country}</span>}
                  {detailData.industry && <span className="text-sm text-muted-foreground">{detailData.industry}</span>}
                </div>
              </DialogHeader>

              {/* 详情网格 */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                {detailData.main_products && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">主营产品：</span>
                    <span>{detailData.main_products}</span>
                  </div>
                )}
                {detailData.email && (
                  <div><span className="text-muted-foreground">邮箱：</span>{detailData.email}</div>
                )}
                {detailData.phone && (
                  <div><span className="text-muted-foreground">电话：</span>{detailData.phone}</div>
                )}
                {detailData.website && (
                  <div><span className="text-muted-foreground">网站：</span>{detailData.website}</div>
                )}
                {detailData.payment_terms && (
                  <div><span className="text-muted-foreground">付款条款：</span>{detailData.payment_terms}</div>
                )}
                {detailData.shipping_terms && (
                  <div><span className="text-muted-foreground">贸易术语：</span>{detailData.shipping_terms}</div>
                )}
                {detailData.source && (
                  <div><span className="text-muted-foreground">来源：</span>{SUPPLIER_SOURCES.find((s) => s.value === detailData.source)?.label || detailData.source}</div>
                )}
                {detailData.address && (
                  <div className="col-span-2"><span className="text-muted-foreground">地址：</span>{detailData.address}</div>
                )}
                {detailData.tags.length > 0 && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">标签：</span>
                    {detailData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="mr-1">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
                {detailData.notes && (
                  <div className="col-span-2"><span className="text-muted-foreground">备注：</span>{detailData.notes}</div>
                )}
              </div>

              {/* 联系人列表 */}
              <Separator />
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">联系人 ({detailData.contacts.length})</h3>
                  {can('supplier', 'create') && (
                  <Button size="sm" onClick={openCreateContact}>
                    <Plus className="size-3.5" />
                    添加联系人
                  </Button>
                  )}
                </div>

                {detailData.contacts.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground text-sm">暂无联系人</div>
                ) : (
                  <div className="space-y-3">
                    {detailData.contacts.map((contact) => (
                      <div key={contact.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm">{contact.name}</span>
                            {contact.is_primary && (
                              <Badge variant="outline" className="bg-blue-100 text-blue-800">主联系人</Badge>
                            )}
                            {!contact.is_active && (
                              <Badge variant="secondary">停用</Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {[contact.title, contact.department].filter(Boolean).join(' / ') || ''}
                            {contact.email && <span className="ml-2">{contact.email}</span>}
                            {contact.mobile && <span className="ml-2">{contact.mobile}</span>}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          {can('supplier', 'update') && (
                          <Button variant="ghost" size="sm" onClick={() => openEditContact(contact)}>
                            <Pencil className="size-3.5" />
                            编辑
                          </Button>
                          )}
                          {can('supplier', 'delete') && (
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteContact(contact)}>
                            <Trash2 className="size-3.5" />
                            删除
                          </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* ==================== 联系人表单弹窗 ==================== */}
      <FormDialog
        open={showContactForm}
        onOpenChange={(open) => !open && setShowContactForm(false)}
        title={editingContact ? '编辑联系人' : '添加联系人'}
        size="sm"
      >
        <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label>姓名 *</Label>
              <Input
                type="text"
                value={contactFormData.name}
                onChange={(e) => setContactFormData({ ...contactFormData, name: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>职位</Label>
              <Input
                type="text"
                value={contactFormData.title || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, title: e.target.value || undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>部门</Label>
              <Input
                type="text"
                value={contactFormData.department || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, department: e.target.value || undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>邮箱</Label>
              <Input
                type="email"
                value={contactFormData.email || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, email: e.target.value || undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>手机</Label>
              <Input
                type="text"
                value={contactFormData.mobile || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, mobile: e.target.value || undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>座机</Label>
              <Input
                type="text"
                value={contactFormData.phone || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, phone: e.target.value || undefined })}
                className="mt-1"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="is_primary"
                checked={contactFormData.is_primary || false}
                onCheckedChange={(checked) => setContactFormData({ ...contactFormData, is_primary: checked === true })}
              />
              <Label htmlFor="is_primary" className="font-normal">设为主联系人</Label>
            </div>
            <div className="col-span-2">
              <Label>备注</Label>
              <Textarea
                value={contactFormData.notes || ''}
                onChange={(e) => setContactFormData({ ...contactFormData, notes: e.target.value || undefined })}
                rows={2}
                className="mt-1"
              />
            </div>
          </div>

        <FormFooter
          onCancel={() => setShowContactForm(false)}
          onSubmit={handleSubmitContact}
          type="button"
          submitText={editingContact ? '保存' : '添加'}
          loading={contactFormLoading}
          disabled={!contactFormData.name.trim()}
        />
      </FormDialog>
    </div>
  );
}
