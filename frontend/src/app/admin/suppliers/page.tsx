// src/app/admin/suppliers/page.tsx
// 供应商管理页面
//
// 功能说明：
// 1. 供应商列表（搜索、筛选、分页）
// 2. 新建/编辑供应商
// 3. 供应商详情 + 联系人管理
// 4. 联系人新建/编辑

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  suppliersApi,
  supplierContactsApi,
  Supplier,
  SupplierDetail,
  SupplierContact,
  SupplierCreate,
  SupplierUpdate,
  SupplierContactCreate,
  SupplierContactUpdate,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
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

// ==================== 供应商等级配置 ====================

const SUPPLIER_LEVELS = [
  { value: 'potential', label: '潜在', color: 'bg-gray-100 text-gray-800' },
  { value: 'normal', label: '普通', color: 'bg-blue-100 text-blue-800' },
  { value: 'important', label: '重要', color: 'bg-orange-100 text-orange-800' },
  { value: 'strategic', label: '战略', color: 'bg-red-100 text-red-800' },
];

const SUPPLIER_SOURCES = [
  { value: 'email', label: '邮件' },
  { value: 'exhibition', label: '展会' },
  { value: 'referral', label: '推荐' },
  { value: 'website', label: '网站' },
  { value: '1688', label: '1688' },
  { value: 'other', label: '其他' },
];

function getLevelBadge(level: string) {
  const config = SUPPLIER_LEVELS.find((l) => l.value === level);
  if (!config) return null;
  return (
    <Badge variant="outline" className={config.color}>
      {config.label}
    </Badge>
  );
}

// ==================== 主页面 ====================

export default function SuppliersPage() {
  const confirm = useConfirm();

  // 列表状态
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('');

  // 供应商表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [formData, setFormData] = useState<SupplierCreate>({ name: '' });
  const [formLoading, setFormLoading] = useState(false);
  const [tagsText, setTagsText] = useState('');

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
        search: search || undefined,
        supplier_level: levelFilter || undefined,
      });
      setSuppliers(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, search, levelFilter]);

  useEffect(() => {
    loadSuppliers();
  }, [loadSuppliers]);

  // ==================== 供应商操作 ====================

  const openCreateForm = () => {
    setEditingSupplier(null);
    setFormData({ name: '', supplier_level: 'normal' });
    setTagsText('');
    setShowForm(true);
  };

  const openEditForm = (supplier: Supplier) => {
    setEditingSupplier(supplier);
    setFormData({
      name: supplier.name,
      short_name: supplier.short_name || undefined,
      country: supplier.country || undefined,
      region: supplier.region || undefined,
      industry: supplier.industry || undefined,
      company_size: supplier.company_size || undefined,
      main_products: supplier.main_products || undefined,
      supplier_level: supplier.supplier_level,
      email: supplier.email || undefined,
      phone: supplier.phone || undefined,
      website: supplier.website || undefined,
      address: supplier.address || undefined,
      payment_terms: supplier.payment_terms || undefined,
      shipping_terms: supplier.shipping_terms || undefined,
      source: supplier.source || undefined,
      notes: supplier.notes || undefined,
      tags: supplier.tags,
    });
    setTagsText(supplier.tags.join(', '));
    setShowForm(true);
  };

  const handleSubmitSupplier = async () => {
    if (!formData.name.trim()) return;
    setFormLoading(true);
    try {
      const data = { ...formData, tags: tagsText ? tagsText.split(',').map((t) => t.trim()).filter(Boolean) : [] };
      if (editingSupplier) {
        await suppliersApi.update(editingSupplier.id, data as SupplierUpdate);
      } else {
        await suppliersApi.create(data);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">供应商管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理供应商信息和联系人</p>
        </div>
        <Button onClick={openCreateForm}>
          <Plus />
          新增供应商
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <Input
          type="text"
          placeholder="搜索公司名/简称/邮箱..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1"
        />
        <select
          value={levelFilter}
          onChange={(e) => { setLevelFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">全部等级</option>
          {SUPPLIER_LEVELS.map((l) => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 供应商列表 */}
      <Card className="py-0">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : suppliers.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无供应商数据</div>
        ) : (
          <Table>
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
                  <TableCell className="px-6 py-4">{getLevelBadge(supplier.supplier_level)}</TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{supplier.contact_count}</TableCell>
                  <TableCell className="px-6 py-4">
                    <Badge variant="outline" className={supplier.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                      {supplier.is_active ? '活跃' : '停用'}
                    </Badge>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEditForm(supplier)}>
                      <Pencil className="size-3.5" />
                      编辑
                    </Button>
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteSupplier(supplier)}>
                      <Trash2 className="size-3.5" />
                      删除
                    </Button>
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
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ==================== 供应商表单弹窗 ==================== */}
      <Dialog open={showForm} onOpenChange={(open) => !open && setShowForm(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingSupplier ? '编辑供应商' : '新增供应商'}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4">
            {/* 公司全称 */}
            <div className="col-span-2">
              <Label>公司全称 *</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="请输入公司全称"
                className="mt-1"
              />
            </div>

            {/* 简称 */}
            <div>
              <Label>简称</Label>
              <Input
                type="text"
                value={formData.short_name || ''}
                onChange={(e) => setFormData({ ...formData, short_name: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            {/* 等级 */}
            <div>
              <Label>供应商等级</Label>
              <select
                value={formData.supplier_level || 'normal'}
                onChange={(e) => setFormData({ ...formData, supplier_level: e.target.value })}
                className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {SUPPLIER_LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>

            {/* 国家 */}
            <div>
              <Label>国家</Label>
              <Input
                type="text"
                value={formData.country || ''}
                onChange={(e) => setFormData({ ...formData, country: e.target.value || undefined })}
                placeholder="如 China"
                className="mt-1"
              />
            </div>

            {/* 地区 */}
            <div>
              <Label>地区</Label>
              <Input
                type="text"
                value={formData.region || ''}
                onChange={(e) => setFormData({ ...formData, region: e.target.value || undefined })}
                placeholder="如 East Asia"
                className="mt-1"
              />
            </div>

            {/* 行业 */}
            <div>
              <Label>行业</Label>
              <Input
                type="text"
                value={formData.industry || ''}
                onChange={(e) => setFormData({ ...formData, industry: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            {/* 来源 */}
            <div>
              <Label>来源</Label>
              <select
                value={formData.source || ''}
                onChange={(e) => setFormData({ ...formData, source: e.target.value || undefined })}
                className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">请选择</option>
                {SUPPLIER_SOURCES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>

            {/* 主营产品 */}
            <div className="col-span-2">
              <Label>主营产品</Label>
              <Textarea
                value={formData.main_products || ''}
                onChange={(e) => setFormData({ ...formData, main_products: e.target.value || undefined })}
                rows={2}
                placeholder="描述供应商的主要产品"
                className="mt-1"
              />
            </div>

            <Separator className="col-span-2" />

            {/* 邮箱 */}
            <div>
              <Label>邮箱</Label>
              <Input
                type="email"
                value={formData.email || ''}
                onChange={(e) => setFormData({ ...formData, email: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            {/* 电话 */}
            <div>
              <Label>电话</Label>
              <Input
                type="text"
                value={formData.phone || ''}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            {/* 网站 */}
            <div>
              <Label>网站</Label>
              <Input
                type="text"
                value={formData.website || ''}
                onChange={(e) => setFormData({ ...formData, website: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            {/* 付款条款 */}
            <div>
              <Label>付款条款</Label>
              <Input
                type="text"
                value={formData.payment_terms || ''}
                onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value || undefined })}
                placeholder="如 T/T 30 days"
                className="mt-1"
              />
            </div>

            {/* 贸易术语 */}
            <div>
              <Label>贸易术语</Label>
              <Input
                type="text"
                value={formData.shipping_terms || ''}
                onChange={(e) => setFormData({ ...formData, shipping_terms: e.target.value || undefined })}
                placeholder="如 FOB, CIF"
                className="mt-1"
              />
            </div>

            {/* 地址 */}
            <div className="col-span-2">
              <Label>地址</Label>
              <Input
                type="text"
                value={formData.address || ''}
                onChange={(e) => setFormData({ ...formData, address: e.target.value || undefined })}
                className="mt-1"
              />
            </div>

            <Separator className="col-span-2" />

            {/* 标签 */}
            <div className="col-span-2">
              <Label>标签（逗号分隔）</Label>
              <Input
                type="text"
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                placeholder="如 五金, 工具, 刀具"
                className="mt-1"
              />
            </div>

            {/* 备注 */}
            <div className="col-span-2">
              <Label>备注</Label>
              <Textarea
                value={formData.notes || ''}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value || undefined })}
                rows={2}
                className="mt-1"
              />
            </div>
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-3 mt-2">
            <Button variant="outline" onClick={() => setShowForm(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmitSupplier}
              disabled={formLoading || !formData.name.trim()}
            >
              {formLoading ? '提交中...' : editingSupplier ? '保存' : '创建'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ==================== 供应商详情弹窗 ==================== */}
      <Dialog open={showDetail} onOpenChange={(open) => !open && setShowDetail(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-4xl">
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
                  {getLevelBadge(detailData.supplier_level)}
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
                  <Button size="sm" onClick={openCreateContact}>
                    <Plus className="size-3.5" />
                    添加联系人
                  </Button>
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
                          <Button variant="ghost" size="sm" onClick={() => openEditContact(contact)}>
                            <Pencil className="size-3.5" />
                            编辑
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteContact(contact)}>
                            <Trash2 className="size-3.5" />
                            删除
                          </Button>
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
      <Dialog open={showContactForm} onOpenChange={(open) => !open && setShowContactForm(false)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingContact ? '编辑联系人' : '添加联系人'}</DialogTitle>
          </DialogHeader>

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

          <div className="flex justify-end gap-3 mt-2">
            <Button variant="outline" onClick={() => setShowContactForm(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmitContact}
              disabled={contactFormLoading || !contactFormData.name.trim()}
            >
              {contactFormLoading ? '提交中...' : editingContact ? '保存' : '添加'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
