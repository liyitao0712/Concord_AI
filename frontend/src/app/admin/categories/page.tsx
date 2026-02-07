// src/app/admin/categories/page.tsx
// 品类管理页面
//
// 功能说明：
// 1. 品类树形展示（缩进 + 展开/折叠）
// 2. 新建/编辑品类弹窗（含编码自动生成）
// 3. 删除保护提示
// 4. 显示品类编码、中英文名、增值税率、退税率、产品数量

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  categoriesApi,
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoryTreeNode,
} from '@/lib/api';
import { ChevronRight } from 'lucide-react';
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

  // ==================== 表单操作 ====================

  const openCreateForm = async (parentId?: string) => {
    setEditingId(null);
    try {
      // 自动获取下一个编码
      const { code } = await categoriesApi.nextCode(parentId);
      setFormData({
        code,
        name: '',
        parent_id: parentId || undefined,
      });
      setShowForm(true);
    } catch {
      // 如果获取编码失败，让用户手动填
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
      if (editingId) {
        await categoriesApi.update(editingId, formData as CategoryUpdate);
      } else {
        await categoriesApi.create(formData);
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
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingId ? '编辑品类' : '新增品类'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* 品类编码 + 品类名称 */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="mb-1">品类编码 *</Label>
                <Input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="如 01、01-01"
                />
              </div>
              <div className="col-span-2">
                <Label className="mb-1">品类名称（中文） *</Label>
                <Input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="请输入品类中文名"
                />
              </div>
            </div>

            {/* 英文名 */}
            <div>
              <Label className="mb-1">品类名称（英文）</Label>
              <Input
                type="text"
                value={formData.name_en || ''}
                onChange={(e) => setFormData({ ...formData, name_en: e.target.value || undefined })}
                placeholder="请输入品类英文名（可选）"
              />
            </div>

            {/* 父品类 */}
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
