// src/app/admin/products/page.tsx
// 产品管理页面
//
// 功能说明：
// 1. 产品列表（搜索、筛选品类/状态、分页）
// 2. 新建/编辑产品（分区表单）
// 3. 产品详情 + 供应商关联管理
// 4. 供应商关联新增/编辑/删除

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  productsApi,
  categoriesApi,
  suppliersApi,
  Product,
  ProductDetail,
  ProductCreate,
  ProductUpdate,
  ProductSupplierInfo,
  ProductSupplierCreate,
  ProductSupplierUpdate,
  CategoryTreeNode,
  Supplier,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Plus, Pencil, Trash2 } from 'lucide-react';
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

// ==================== 状态配置 ====================

const PRODUCT_STATUSES = [
  { value: 'active', label: '在售', color: 'bg-green-100 text-green-800' },
  { value: 'inactive', label: '停售', color: 'bg-gray-100 text-gray-800' },
  { value: 'discontinued', label: '停产', color: 'bg-red-100 text-red-800' },
];

function getStatusBadge(status: string) {
  const config = PRODUCT_STATUSES.find((s) => s.value === status);
  if (!config) return null;
  return (
    <Badge variant="outline" className={config.color}>
      {config.label}
    </Badge>
  );
}

// ==================== 主页面 ====================

export default function ProductsPage() {
  const confirm = useConfirm();

  // 列表状态
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // 品类树（用于筛选和表单中的品类选择）
  const [categoryTree, setCategoryTree] = useState<CategoryTreeNode[]>([]);

  // 产品表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState<ProductCreate>({ name: '' });
  const [formLoading, setFormLoading] = useState(false);
  const [tagsText, setTagsText] = useState('');
  const [imagesText, setImagesText] = useState('');

  // 详情弹窗
  const [showDetail, setShowDetail] = useState(false);
  const [detailData, setDetailData] = useState<ProductDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 供应商关联弹窗
  const [showSupplierForm, setShowSupplierForm] = useState(false);
  const [editingSupplierLink, setEditingSupplierLink] = useState<ProductSupplierInfo | null>(null);
  const [supplierFormData, setSupplierFormData] = useState<ProductSupplierCreate>({
    supplier_id: '',
  });
  const [supplierFormLoading, setSupplierFormLoading] = useState(false);

  // 供应商列表（用于选择）
  const [suppliersList, setSuppliersList] = useState<Supplier[]>([]);

  const PAGE_SIZE = 20;

  // ==================== 数据加载 ====================

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await productsApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        category_id: categoryFilter || undefined,
        status: statusFilter || undefined,
      });
      setProducts(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter, statusFilter]);

  const loadCategoryTree = useCallback(async () => {
    try {
      const resp = await categoriesApi.tree({ is_active: true });
      setCategoryTree(resp.items);
    } catch {
      // 品类加载失败不阻断主流程
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    loadCategoryTree();
  }, [loadCategoryTree]);

  // ==================== 品类选项扁平化（用于 select） ====================

  function flattenCategories(nodes: CategoryTreeNode[], prefix = ''): { id: string; label: string }[] {
    const result: { id: string; label: string }[] = [];
    for (const node of nodes) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name;
      result.push({ id: node.id, label });
      if (node.children.length > 0) {
        result.push(...flattenCategories(node.children, label));
      }
    }
    return result;
  }

  const flatCategoryOptions = flattenCategories(categoryTree);

  // ==================== 产品操作 ====================

  const openCreateForm = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      category_id: undefined,
      status: 'active',
      currency: 'USD',
    });
    setTagsText('');
    setImagesText('');
    setShowForm(true);
  };

  const openEditForm = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      category_id: product.category_id || undefined,
      model_number: product.model_number || undefined,
      specifications: product.specifications || undefined,
      unit: product.unit || undefined,
      moq: product.moq || undefined,
      reference_price: product.reference_price || undefined,
      currency: product.currency,
      hs_code: product.hs_code || undefined,
      origin: product.origin || undefined,
      material: product.material || undefined,
      packaging: product.packaging || undefined,
      images: product.images,
      description: product.description || undefined,
      tags: product.tags,
      status: product.status,
      notes: product.notes || undefined,
    });
    setTagsText(product.tags.join(', '));
    setImagesText(product.images.join('\n'));
    setShowForm(true);
  };

  const handleSubmitProduct = async () => {
    if (!formData.name.trim()) return;
    setFormLoading(true);
    try {
      const data = {
        ...formData,
        tags: tagsText ? tagsText.split(',').map((t) => t.trim()).filter(Boolean) : [],
        images: imagesText ? imagesText.split('\n').map((u) => u.trim()).filter(Boolean) : [],
      };
      if (editingProduct) {
        await productsApi.update(editingProduct.id, data as ProductUpdate);
      } else {
        await productsApi.create(data);
      }
      setShowForm(false);
      loadProducts();
      if (detailData && editingProduct && detailData.id === editingProduct.id) {
        loadDetail(editingProduct.id);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteProduct = async (product: Product) => {
    const confirmed = await confirm({
      title: '删除产品',
      description: `确定删除产品「${product.name}」？将同时删除其供应商关联。`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await productsApi.delete(product.id);
      loadProducts();
      if (detailData?.id === product.id) {
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
      const detail = await productsApi.get(id);
      setDetailData(detail);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const openDetail = (product: Product) => {
    setShowDetail(true);
    loadDetail(product.id);
  };

  // ==================== 供应商关联操作 ====================

  const openAddSupplier = async () => {
    if (!detailData) return;
    // 加载供应商列表
    try {
      const resp = await suppliersApi.list({ page: 1, page_size: 100, is_active: true });
      setSuppliersList(resp.items);
    } catch {
      // ignore
    }
    setEditingSupplierLink(null);
    setSupplierFormData({
      supplier_id: '',
      currency: 'USD',
      is_primary: false,
    });
    setShowSupplierForm(true);
  };

  const openEditSupplierLink = async (link: ProductSupplierInfo) => {
    try {
      const resp = await suppliersApi.list({ page: 1, page_size: 100, is_active: true });
      setSuppliersList(resp.items);
    } catch {
      // ignore
    }
    setEditingSupplierLink(link);
    setSupplierFormData({
      supplier_id: link.supplier_id,
      supply_price: link.supply_price || undefined,
      currency: link.currency,
      moq: link.moq || undefined,
      lead_time: link.lead_time || undefined,
      is_primary: link.is_primary,
      notes: link.notes || undefined,
    });
    setShowSupplierForm(true);
  };

  const handleSubmitSupplierLink = async () => {
    if (!detailData) return;
    if (!editingSupplierLink && !supplierFormData.supplier_id) return;
    setSupplierFormLoading(true);
    try {
      if (editingSupplierLink) {
        const { supplier_id, ...updateData } = supplierFormData;
        await productsApi.updateSupplier(detailData.id, editingSupplierLink.supplier_id, updateData as ProductSupplierUpdate);
      } else {
        await productsApi.addSupplier(detailData.id, supplierFormData);
      }
      setShowSupplierForm(false);
      loadDetail(detailData.id);
      loadProducts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setSupplierFormLoading(false);
    }
  };

  const handleRemoveSupplier = async (link: ProductSupplierInfo) => {
    if (!detailData) return;
    const confirmed = await confirm({
      title: '移除供应商',
      description: `确定移除供应商「${link.supplier_name}」的关联？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await productsApi.removeSupplier(detailData.id, link.supplier_id);
      loadDetail(detailData.id);
      loadProducts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '移除失败');
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
          <h1 className="text-2xl font-bold">产品管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理外贸产品信息和供应商关联</p>
        </div>
        <Button onClick={openCreateForm}>
          <Plus />
          新增产品
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <Input
          type="text"
          placeholder="搜索品名/型号/HS编码..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1"
        />
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">全部品类</option>
          {flatCategoryOptions.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">全部状态</option>
          {PRODUCT_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 产品列表 */}
      <Card className="py-0">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : products.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无产品数据</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">品名</TableHead>
                <TableHead className="px-6">型号</TableHead>
                <TableHead className="px-6">品类</TableHead>
                <TableHead className="px-6">参考价</TableHead>
                <TableHead className="px-6">供应商</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="px-6 py-4">
                    <button
                      onClick={() => openDetail(product)}
                      className="text-sm font-medium text-primary hover:text-primary/80"
                    >
                      {product.name}
                    </button>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{product.model_number || '-'}</TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{product.category_name || '-'}</TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {product.reference_price != null
                      ? `${product.currency} ${product.reference_price}`
                      : '-'}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{product.supplier_count}</TableCell>
                  <TableCell className="px-6 py-4">{getStatusBadge(product.status)}</TableCell>
                  <TableCell className="px-6 py-4 text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEditForm(product)}>
                      <Pencil className="size-3.5" />
                      编辑
                    </Button>
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteProduct(product)}>
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

      {/* ==================== 产品表单弹窗 ==================== */}
      <Dialog open={showForm} onOpenChange={(open) => !open && setShowForm(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-4xl">
          <DialogHeader>
            <DialogTitle>{editingProduct ? '编辑产品' : '新增产品'}</DialogTitle>
          </DialogHeader>

          {/* 基本信息 */}
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground mb-3">基本信息</h3>
            <Separator className="mb-4" />
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>品名 *</Label>
                <Input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="请输入产品品名"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>型号</Label>
                <Input
                  type="text"
                  value={formData.model_number || ''}
                  onChange={(e) => setFormData({ ...formData, model_number: e.target.value || undefined })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>品类</Label>
                <select
                  value={formData.category_id || ''}
                  onChange={(e) => setFormData({ ...formData, category_id: e.target.value || undefined })}
                  className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">请选择品类</option>
                  {flatCategoryOptions.map((c) => (
                    <option key={c.id} value={c.id}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <Label>规格</Label>
                <Textarea
                  value={formData.specifications || ''}
                  onChange={(e) => setFormData({ ...formData, specifications: e.target.value || undefined })}
                  rows={2}
                  placeholder="产品规格描述"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>单位</Label>
                <Input
                  type="text"
                  value={formData.unit || ''}
                  onChange={(e) => setFormData({ ...formData, unit: e.target.value || undefined })}
                  placeholder="如 PCS/SET/KG"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>状态</Label>
                <select
                  value={formData.status || 'active'}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {PRODUCT_STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* 价格贸易信息 */}
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground mb-3">价格与贸易</h3>
            <Separator className="mb-4" />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>参考价格</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.reference_price ?? ''}
                  onChange={(e) => setFormData({ ...formData, reference_price: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>币种</Label>
                <select
                  value={formData.currency || 'USD'}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="CNY">CNY</option>
                  <option value="JPY">JPY</option>
                </select>
              </div>
              <div>
                <Label>最小起订量 (MOQ)</Label>
                <Input
                  type="number"
                  value={formData.moq ?? ''}
                  onChange={(e) => setFormData({ ...formData, moq: e.target.value ? parseInt(e.target.value) : undefined })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>HS 编码</Label>
                <Input
                  type="text"
                  value={formData.hs_code || ''}
                  onChange={(e) => setFormData({ ...formData, hs_code: e.target.value || undefined })}
                  placeholder="如 8471.30.0000"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>产地</Label>
                <Input
                  type="text"
                  value={formData.origin || ''}
                  onChange={(e) => setFormData({ ...formData, origin: e.target.value || undefined })}
                  placeholder="如 China"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>材质</Label>
                <Input
                  type="text"
                  value={formData.material || ''}
                  onChange={(e) => setFormData({ ...formData, material: e.target.value || undefined })}
                  className="mt-1"
                />
              </div>
              <div className="col-span-2">
                <Label>包装方式</Label>
                <Input
                  type="text"
                  value={formData.packaging || ''}
                  onChange={(e) => setFormData({ ...formData, packaging: e.target.value || undefined })}
                  placeholder="如 Carton / Pallet"
                  className="mt-1"
                />
              </div>
            </div>
          </div>

          {/* 详细信息 */}
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground mb-3">详细信息</h3>
            <Separator className="mb-4" />
            <div className="space-y-4">
              <div>
                <Label>产品描述</Label>
                <Textarea
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value || undefined })}
                  rows={3}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>标签（逗号分隔）</Label>
                <Input
                  type="text"
                  value={tagsText}
                  onChange={(e) => setTagsText(e.target.value)}
                  placeholder="如 五金, 工具, 不锈钢"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>图片 URL（每行一个）</Label>
                <Textarea
                  value={imagesText}
                  onChange={(e) => setImagesText(e.target.value)}
                  rows={2}
                  placeholder="每行输入一个图片 URL"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>备注</Label>
                <Textarea
                  value={formData.notes || ''}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value || undefined })}
                  rows={2}
                  className="mt-1"
                />
              </div>
            </div>
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setShowForm(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmitProduct}
              disabled={formLoading || !formData.name.trim()}
            >
              {formLoading ? '提交中...' : editingProduct ? '保存' : '创建'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ==================== 产品详情弹窗 ==================== */}
      <Dialog open={showDetail} onOpenChange={(open) => !open && setShowDetail(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-4xl">
          {detailLoading || !detailData ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : (
            <>
              {/* 产品基本信息 */}
              <DialogHeader>
                <DialogTitle className="text-xl">{detailData.name}</DialogTitle>
                <div className="flex items-center gap-3 mt-2">
                  {getStatusBadge(detailData.status)}
                  {detailData.model_number && (
                    <span className="text-sm text-muted-foreground">型号: {detailData.model_number}</span>
                  )}
                  {detailData.category_name && (
                    <span className="text-sm text-muted-foreground">品类: {detailData.category_name}</span>
                  )}
                </div>
              </DialogHeader>

              {/* 详情网格 */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                {detailData.specifications && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">规格：</span>
                    <span>{detailData.specifications}</span>
                  </div>
                )}
                {detailData.unit && (
                  <div><span className="text-muted-foreground">单位：</span>{detailData.unit}</div>
                )}
                {detailData.reference_price != null && (
                  <div>
                    <span className="text-muted-foreground">参考价：</span>
                    {detailData.currency} {detailData.reference_price}
                  </div>
                )}
                {detailData.moq != null && (
                  <div><span className="text-muted-foreground">MOQ：</span>{detailData.moq}</div>
                )}
                {detailData.hs_code && (
                  <div><span className="text-muted-foreground">HS 编码：</span>{detailData.hs_code}</div>
                )}
                {detailData.origin && (
                  <div><span className="text-muted-foreground">产地：</span>{detailData.origin}</div>
                )}
                {detailData.material && (
                  <div><span className="text-muted-foreground">材质：</span>{detailData.material}</div>
                )}
                {detailData.packaging && (
                  <div><span className="text-muted-foreground">包装：</span>{detailData.packaging}</div>
                )}
                {detailData.description && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">描述：</span>
                    <span>{detailData.description}</span>
                  </div>
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
                  <div className="col-span-2">
                    <span className="text-muted-foreground">备注：</span>{detailData.notes}
                  </div>
                )}
              </div>

              {/* 供应商列表 */}
              <Separator />
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">关联供应商 ({detailData.suppliers.length})</h3>
                  <Button size="sm" onClick={openAddSupplier}>
                    <Plus className="size-3.5" />
                    添加供应商
                  </Button>
                </div>

                {detailData.suppliers.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground text-sm">暂无关联供应商</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="px-4">供应商</TableHead>
                        <TableHead className="px-4">供应价</TableHead>
                        <TableHead className="px-4">MOQ</TableHead>
                        <TableHead className="px-4">交期</TableHead>
                        <TableHead className="px-4">首选</TableHead>
                        <TableHead className="px-4 text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailData.suppliers.map((link) => (
                        <TableRow key={link.id}>
                          <TableCell className="px-4 py-2 text-sm font-medium">{link.supplier_name}</TableCell>
                          <TableCell className="px-4 py-2 text-sm text-muted-foreground">
                            {link.supply_price != null ? `${link.currency} ${link.supply_price}` : '-'}
                          </TableCell>
                          <TableCell className="px-4 py-2 text-sm text-muted-foreground">{link.moq ?? '-'}</TableCell>
                          <TableCell className="px-4 py-2 text-sm text-muted-foreground">
                            {link.lead_time != null ? `${link.lead_time} 天` : '-'}
                          </TableCell>
                          <TableCell className="px-4 py-2 text-sm">
                            {link.is_primary && (
                              <Badge variant="outline" className="bg-blue-100 text-blue-800">首选</Badge>
                            )}
                          </TableCell>
                          <TableCell className="px-4 py-2 text-right space-x-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditSupplierLink(link)}>
                              <Pencil className="size-3.5" />
                              编辑
                            </Button>
                            <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleRemoveSupplier(link)}>
                              <Trash2 className="size-3.5" />
                              移除
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* ==================== 供应商关联弹窗 ==================== */}
      <Dialog open={showSupplierForm} onOpenChange={(open) => !open && setShowSupplierForm(false)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingSupplierLink ? '编辑供应商关联' : '添加供应商'}
            </DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4">
            {/* 选择供应商 */}
            {!editingSupplierLink && (
              <div className="col-span-2">
                <Label>供应商 *</Label>
                <select
                  value={supplierFormData.supplier_id}
                  onChange={(e) => setSupplierFormData({ ...supplierFormData, supplier_id: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">请选择供应商</option>
                  {suppliersList
                    .filter((s) => !detailData?.suppliers.some((ds) => ds.supplier_id === s.id))
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {s.short_name ? ` (${s.short_name})` : ''}
                      </option>
                    ))}
                </select>
              </div>
            )}
            {editingSupplierLink && (
              <div className="col-span-2">
                <Label>供应商</Label>
                <div className="mt-1 px-3 py-2 bg-muted border rounded-md text-sm text-muted-foreground">
                  {editingSupplierLink.supplier_name}
                </div>
              </div>
            )}

            <div>
              <Label>供应价格</Label>
              <Input
                type="number"
                step="0.01"
                value={supplierFormData.supply_price ?? ''}
                onChange={(e) => setSupplierFormData({ ...supplierFormData, supply_price: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>币种</Label>
              <select
                value={supplierFormData.currency || 'USD'}
                onChange={(e) => setSupplierFormData({ ...supplierFormData, currency: e.target.value })}
                className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="CNY">CNY</option>
                <option value="JPY">JPY</option>
              </select>
            </div>
            <div>
              <Label>最小起订量</Label>
              <Input
                type="number"
                value={supplierFormData.moq ?? ''}
                onChange={(e) => setSupplierFormData({ ...supplierFormData, moq: e.target.value ? parseInt(e.target.value) : undefined })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>交期（天）</Label>
              <Input
                type="number"
                value={supplierFormData.lead_time ?? ''}
                onChange={(e) => setSupplierFormData({ ...supplierFormData, lead_time: e.target.value ? parseInt(e.target.value) : undefined })}
                className="mt-1"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="is_primary_supplier"
                checked={supplierFormData.is_primary || false}
                onCheckedChange={(checked) => setSupplierFormData({ ...supplierFormData, is_primary: checked === true })}
              />
              <Label htmlFor="is_primary_supplier" className="font-normal">设为首选供应商</Label>
            </div>
            <div className="col-span-2">
              <Label>备注</Label>
              <Textarea
                value={supplierFormData.notes || ''}
                onChange={(e) => setSupplierFormData({ ...supplierFormData, notes: e.target.value || undefined })}
                rows={2}
                className="mt-1"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-2">
            <Button variant="outline" onClick={() => setShowSupplierForm(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmitSupplierLink}
              disabled={supplierFormLoading || (!editingSupplierLink && !supplierFormData.supplier_id)}
            >
              {supplierFormLoading ? '提交中...' : editingSupplierLink ? '保存' : '添加'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
