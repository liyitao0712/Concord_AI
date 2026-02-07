// src/app/admin/categories/page.tsx
// 品类管理页面
//
// 功能说明：
// 1. 品类树形展示（缩进 + 展开/折叠）
// 2. 新建/编辑品类弹窗（含编码自动生成 + 图片上传）
// 3. 删除保护提示
// 4. 显示品类编码、中英文名、增值税率、退税率、产品数量

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  categoriesApi,
  uploadApi,
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoryTreeNode,
} from '@/lib/api';
import { ChevronRight, Upload, X } from 'lucide-react';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
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
  DialogFooter,
} from '@/components/ui/dialog';
import { LoadingSpinner } from '@/components/LoadingSpinner';

// ==================== 树节点组件 ====================

function TreeNodeItem({
  node,
  level,
  expandedIds,
  toggleExpand,
  onEdit,
  onDelete,
  onCreateChild,
}: {
  node: CategoryTreeNode;
  level: number;
  expandedIds: Set<string>;
  toggleExpand: (id: string) => void;
  onEdit: (node: CategoryTreeNode) => void;
  onDelete: (node: CategoryTreeNode) => void;
  onCreateChild: (parentId: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);

  return (
    <>
      <TableRow>
        {/* 品类编码 */}
        <TableCell className="text-sm text-muted-foreground font-mono whitespace-nowrap">
          {node.code}
        </TableCell>
        {/* 品类名称（含缩进和展开/折叠） */}
        <TableCell>
          <div className="flex items-center" style={{ paddingLeft: `${level * 24}px` }}>
            {hasChildren ? (
              <button
                onClick={() => toggleExpand(node.id)}
                className="w-5 h-5 mr-2 flex items-center justify-center text-muted-foreground hover:text-foreground"
              >
                <ChevronRight
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                />
              </button>
            ) : (
              <span className="w-5 mr-2" />
            )}
            {node.image_url && (
              <img
                src={node.image_url}
                alt=""
                className="w-6 h-6 rounded object-cover mr-2 flex-shrink-0"
              />
            )}
            <span className="text-sm font-medium">{node.name}</span>
          </div>
        </TableCell>
        {/* 英文名 */}
        <TableCell className="text-sm text-muted-foreground">
          {node.name_en || '-'}
        </TableCell>
        {/* 增值税率 */}
        <TableCell className="text-sm text-muted-foreground text-center">
          {node.vat_rate != null ? `${node.vat_rate}%` : '-'}
        </TableCell>
        {/* 退税率 */}
        <TableCell className="text-sm text-muted-foreground text-center">
          {node.tax_rebate_rate != null ? `${node.tax_rebate_rate}%` : '-'}
        </TableCell>
        {/* 产品数 */}
        <TableCell className="text-sm text-muted-foreground text-center">
          {node.product_count}
        </TableCell>
        {/* 操作 */}
        <TableCell className="text-right text-sm space-x-2">
          <Button variant="ghost" size="sm" onClick={() => onCreateChild(node.id)} className="text-green-600 hover:text-green-800">
            添加子品类
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onEdit(node)}>
            编辑
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onDelete(node)} className="text-destructive hover:text-destructive">
            删除
          </Button>
        </TableCell>
      </TableRow>
      {/* 递归渲染子节点 */}
      {isExpanded &&
        node.children.map((child) => (
          <TreeNodeItem
            key={child.id}
            node={child}
            level={level + 1}
            expandedIds={expandedIds}
            toggleExpand={toggleExpand}
            onEdit={onEdit}
            onDelete={onDelete}
            onCreateChild={onCreateChild}
          />
        ))}
    </>
  );
}

// ==================== 主页面 ====================

export default function CategoriesPage() {
  // 树数据
  const [treeData, setTreeData] = useState<CategoryTreeNode[]>([]);
  const [flatCategories, setFlatCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 展开状态
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // 表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<CategoryCreate>({ code: '', name: '' });
  const [formLoading, setFormLoading] = useState(false);

  // 图片上传
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [existingImageUrl, setExistingImageUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const confirm = useConfirm();

  // ==================== 数据加载 ====================

  const loadTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [treeResp, listResp] = await Promise.all([
        categoriesApi.tree(),
        categoriesApi.list({ page: 1, page_size: 100 }),
      ]);
      setTreeData(treeResp.items);
      setFlatCategories(listResp.items);
      // 默认展开所有
      const allIds = new Set<string>();
      const collectIds = (nodes: CategoryTreeNode[]) => {
        nodes.forEach((n) => {
          if (n.children.length > 0) {
            allIds.add(n.id);
            collectIds(n.children);
          }
        });
      };
      collectIds(treeResp.items);
      setExpandedIds(allIds);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  // ==================== 展开/折叠 ====================

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // ==================== 图片处理 ====================

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证类型
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('仅支持 JPEG/PNG/GIF/WebP 格式');
      return;
    }
    // 验证大小（5MB）
    if (file.size > 5 * 1024 * 1024) {
      toast.error('图片大小不能超过 5MB');
      return;
    }

    setImageFile(file);
    setExistingImageUrl(null);
    // 生成本地预览
    const reader = new FileReader();
    reader.onload = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setImageFile(null);
    setImagePreview(null);
    setExistingImageUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // ==================== 表单操作 ====================

  const openCreateForm = async (parentId?: string) => {
    setEditingId(null);
    setImageFile(null);
    setImagePreview(null);
    setExistingImageUrl(null);
    try {
      const { code } = await categoriesApi.nextCode(parentId);
      setFormData({
        code,
        name: '',
        parent_id: parentId || undefined,
      });
      setShowForm(true);
    } catch {
      setFormData({
        code: '',
        name: '',
        parent_id: parentId || undefined,
      });
      setShowForm(true);
    }
  };

  const openEditForm = async (node: CategoryTreeNode) => {
    try {
      const category = await categoriesApi.get(node.id);
      setEditingId(node.id);
      setImageFile(null);
      setImagePreview(null);
      setExistingImageUrl(category.image_url || null);
      setFormData({
        code: category.code,
        name: category.name,
        name_en: category.name_en || undefined,
        parent_id: category.parent_id || undefined,
        description: category.description || undefined,
        vat_rate: category.vat_rate ?? undefined,
        tax_rebate_rate: category.tax_rebate_rate ?? undefined,
      });
      setShowForm(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载失败');
    }
  };

  const handleSubmit = async () => {
    if (!formData.code.trim() || !formData.name.trim()) return;
    setFormLoading(true);
    try {
      let submitData: CategoryCreate | CategoryUpdate = { ...formData };

      // 如果有新图片，先上传
      if (imageFile) {
        const uploadResult = await uploadApi.uploadImage(imageFile, 'images/categories');
        submitData.image_key = uploadResult.key;
        submitData.image_storage_type = uploadResult.storage_type;
      } else if (!existingImageUrl && editingId) {
        // 编辑时，如果没有新图也没有已有图（已删除），清空图片字段
        (submitData as CategoryUpdate).image_key = null;
        (submitData as CategoryUpdate).image_storage_type = null;
      }

      if (editingId) {
        await categoriesApi.update(editingId, submitData as CategoryUpdate);
      } else {
        await categoriesApi.create(submitData as CategoryCreate);
      }
      setShowForm(false);
      loadTree();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (node: CategoryTreeNode) => {
    if (node.children.length > 0) {
      toast.error(`品类「${node.name}」下有子品类，无法删除。请先删除或移动子品类。`);
      return;
    }
    if (node.product_count > 0) {
      toast.error(`品类「${node.name}」下有 ${node.product_count} 个产品，无法删除。请先删除或移动产品。`);
      return;
    }
    const confirmed = await confirm({
      title: '确认删除',
      description: `确定删除品类「${node.name}」？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await categoriesApi.delete(node.id);
      loadTree();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  // 当前显示的图片 URL（新选择的预览 > 已有图片）
  const displayImageUrl = imagePreview || existingImageUrl;

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">品类管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理产品品类的树形结构，支持多级分类</p>
        </div>
        <Button onClick={() => openCreateForm()}>
          新增根品类
        </Button>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 品类树 */}
      <Card className="py-0 overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : treeData.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无品类数据，点击上方按钮新增</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>编码</TableHead>
                <TableHead>品类名称</TableHead>
                <TableHead>英文名</TableHead>
                <TableHead className="text-center">增值税率</TableHead>
                <TableHead className="text-center">退税率</TableHead>
                <TableHead className="text-center">产品数</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {treeData.map((node) => (
                <TreeNodeItem
                  key={node.id}
                  node={node}
                  level={0}
                  expandedIds={expandedIds}
                  toggleExpand={toggleExpand}
                  onEdit={openEditForm}
                  onDelete={handleDelete}
                  onCreateChild={(parentId) => openCreateForm(parentId)}
                />
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* ==================== 品类表单弹窗 ==================== */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {editingId ? '编辑品类' : '新增品类'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* 品类编码 + 父品类 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">品类编码 *</Label>
                <Input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="如 01、01-01"
                />
              </div>
              <div>
                <Label className="mb-1">父品类</Label>
                <select
                  value={formData.parent_id || ''}
                  onChange={(e) => setFormData({ ...formData, parent_id: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">无（作为根品类）</option>
                  {flatCategories
                    .filter((c) => c.id !== editingId)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} - {c.parent_name ? `${c.parent_name} / ${c.name}` : c.name}
                      </option>
                    ))}
                </select>
              </div>
            </div>

            {/* 中文名（独占一行） */}
            <div>
              <Label className="mb-1">品类名称（中文） *</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="请输入品类中文名"
              />
            </div>

            {/* 英文名（独占一行） */}
            <div>
              <Label className="mb-1">品类名称（英文）</Label>
              <Input
                type="text"
                value={formData.name_en || ''}
                onChange={(e) => setFormData({ ...formData, name_en: e.target.value || undefined })}
                placeholder="请输入品类英文名（可选）"
              />
            </div>

            {/* 品类图片 */}
            <div>
              <Label className="mb-1">品类图片</Label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                onChange={handleImageSelect}
                className="hidden"
              />
              {displayImageUrl ? (
                <div className="relative inline-block">
                  <img
                    src={displayImageUrl}
                    alt="品类图片"
                    className="w-32 h-32 rounded-lg object-cover border border-border"
                  />
                  <button
                    type="button"
                    onClick={clearImage}
                    className="absolute -top-2 -right-2 w-6 h-6 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center hover:bg-destructive/90"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-32 h-32 rounded-lg border-2 border-dashed border-muted-foreground/30 hover:border-muted-foreground/60 flex flex-col items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Upload className="w-6 h-6 mb-1" />
                  <span className="text-xs">点击上传</span>
                </button>
              )}
            </div>

            {/* 增值税率 + 退税率 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">增值税率（%）</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.vat_rate ?? ''}
                  onChange={(e) => setFormData({ ...formData, vat_rate: e.target.value ? parseFloat(e.target.value) : undefined })}
                  placeholder="如 13.00"
                />
              </div>
              <div>
                <Label className="mb-1">退税率（%）</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.tax_rebate_rate ?? ''}
                  onChange={(e) => setFormData({ ...formData, tax_rebate_rate: e.target.value ? parseFloat(e.target.value) : undefined })}
                  placeholder="如 13.00"
                />
              </div>
            </div>

            {/* 描述 */}
            <div>
              <Label className="mb-1">描述</Label>
              <Textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value || undefined })}
                rows={2}
                placeholder="品类描述（可选）"
              />
            </div>
          </div>

          {/* 按钮 */}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={formLoading || !formData.code.trim() || !formData.name.trim()}
            >
              {formLoading ? '提交中...' : editingId ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
