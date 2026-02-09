// src/app/admin/warehouses/page.tsx
// 仓库管理页面
//
// 功能说明：
// 1. 仓库列表（搜索、类型筛选、分页）
// 2. 新建/编辑仓库（表单弹窗）
// 3. 删除仓库

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  warehousesApi,
  Warehouse,
  WarehouseCreate,
  WarehouseUpdate,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
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

// ==================== 仓库类型配置 ====================

const WAREHOUSE_TYPES: Record<string, { label: string; color: string }> = {
  own: { label: '自有', color: 'bg-blue-100 text-blue-800' },
  rented: { label: '租赁', color: 'bg-orange-100 text-orange-800' },
  bonded: { label: '保税', color: 'bg-purple-100 text-purple-800' },
  virtual: { label: '虚拟', color: 'bg-gray-100 text-gray-800' },
};

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function getTypeBadge(type: string) {
  const config = WAREHOUSE_TYPES[type];
  if (!config) return <Badge variant="outline">{type}</Badge>;
  return (
    <Badge variant="outline" className={config.color}>
      {config.label}
    </Badge>
  );
}

// ==================== 仓库表单 ====================

function WarehouseForm({
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  initial?: Partial<Warehouse>;
  onSubmit: (data: WarehouseCreate | WarehouseUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<WarehouseCreate>({
    code: initial?.code || '',
    name: initial?.name || '',
    address: initial?.address || '',
    contact_person: initial?.contact_person || '',
    contact_phone: initial?.contact_phone || '',
    warehouse_type: initial?.warehouse_type || 'own',
    is_active: initial?.is_active ?? true,
    notes: initial?.notes || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 清理空字符串为 undefined（用于 update）
    const cleaned: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(form)) {
      if (value === '' || value === null) {
        if (key === 'code' || key === 'name' || key === 'is_active' || key === 'warehouse_type') {
          cleaned[key] = value;
        }
      } else {
        cleaned[key] = value;
      }
    }
    onSubmit(cleaned as unknown as WarehouseCreate);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本信息 */}
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-3">基本信息</h4>
        <Separator className="mb-3" />
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">仓库编码 *</Label>
            <Input
              type="text"
              required
              value={form.code}
              onChange={e => setForm({ ...form, code: e.target.value })}
              placeholder="如 WH001"
            />
          </div>
          <div>
            <Label className="mb-1">仓库名称 *</Label>
            <Input
              type="text"
              required
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="如 上海主仓"
            />
          </div>
          <div>
            <Label className="mb-1">仓库类型</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.warehouse_type}
              onChange={e => setForm({ ...form, warehouse_type: e.target.value })}
            >
              {Object.entries(WAREHOUSE_TYPES).map(([value, { label }]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <div className="flex items-center space-x-2 cursor-pointer">
              <Checkbox
                id="is_active"
                checked={form.is_active}
                onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })}
              />
              <Label htmlFor="is_active" className="cursor-pointer">启用状态</Label>
            </div>
          </div>
          <div className="col-span-2">
            <Label className="mb-1">地址</Label>
            <Input
              type="text"
              value={form.address || ''}
              onChange={e => setForm({ ...form, address: e.target.value })}
              placeholder="仓库详细地址"
            />
          </div>
        </div>
      </div>

      {/* 联系信息 */}
      <div>
        <h4 className="text-sm font-semibold text-foreground mb-3">联系信息</h4>
        <Separator className="mb-3" />
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">联系人</Label>
            <Input
              type="text"
              value={form.contact_person || ''}
              onChange={e => setForm({ ...form, contact_person: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">联系电话</Label>
            <Input
              type="text"
              value={form.contact_phone || ''}
              onChange={e => setForm({ ...form, contact_phone: e.target.value })}
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
            value={form.notes || ''}
            onChange={e => setForm({ ...form, notes: e.target.value })}
          />
        </div>
      </div>

      {/* 按钮 */}
      <Separator />
      <div className="flex justify-end space-x-3 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="submit"
          disabled={loading || !form.code.trim() || !form.name.trim()}
        >
          {loading ? '保存中...' : '保存'}
        </Button>
      </div>
    </form>
  );
}

// ==================== 主页面 ====================

export default function WarehousesPage() {
  const confirm = useConfirm();
  const { can } = usePermission();

  // 列表状态
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // 仓库表单弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const PAGE_SIZE = 20;

  // ==================== 数据加载 ====================

  const loadWarehouses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await warehousesApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        warehouse_type: typeFilter || undefined,
      });
      setWarehouses(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, search, typeFilter]);

  useEffect(() => {
    loadWarehouses();
  }, [loadWarehouses]);

  // ==================== 仓库操作 ====================

  const openCreateForm = () => {
    setEditingWarehouse(null);
    setShowForm(true);
  };

  const openEditForm = (warehouse: Warehouse) => {
    setEditingWarehouse(warehouse);
    setShowForm(true);
  };

  const handleSubmitWarehouse = async (data: WarehouseCreate | WarehouseUpdate) => {
    setFormLoading(true);
    try {
      if (editingWarehouse) {
        await warehousesApi.update(editingWarehouse.id, data as WarehouseUpdate);
        toast.success('仓库更新成功');
      } else {
        await warehousesApi.create(data as WarehouseCreate);
        toast.success('仓库创建成功');
      }
      setShowForm(false);
      loadWarehouses();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteWarehouse = async (warehouse: Warehouse) => {
    const confirmed = await confirm({
      title: '删除仓库',
      description: `确定删除仓库「${warehouse.name}」（${warehouse.code}）？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await warehousesApi.delete(warehouse.id);
      toast.success('仓库删除成功');
      loadWarehouses();
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
          <h1 className="text-2xl font-bold">仓库管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理仓库信息</p>
        </div>
        {can('warehouse', 'create') && (
        <Button onClick={openCreateForm}>
          <Plus />
          新增仓库
        </Button>
        )}
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <Input
          type="text"
          placeholder="搜索仓库编码/名称..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1"
        />
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className={selectClass}
        >
          <option value="">全部类型</option>
          {Object.entries(WAREHOUSE_TYPES).map(([value, { label }]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 仓库列表 */}
      <Card className="py-0">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : warehouses.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无仓库数据</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">仓库编码</TableHead>
                <TableHead className="px-6">仓库名称</TableHead>
                <TableHead className="px-6">类型</TableHead>
                <TableHead className="px-6">联系人</TableHead>
                <TableHead className="px-6">联系电话</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {warehouses.map((warehouse) => (
                <TableRow key={warehouse.id}>
                  <TableCell className="px-6 py-4 text-sm font-medium">{warehouse.code}</TableCell>
                  <TableCell className="px-6 py-4 text-sm">{warehouse.name}</TableCell>
                  <TableCell className="px-6 py-4">{getTypeBadge(warehouse.warehouse_type)}</TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{warehouse.contact_person || '-'}</TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">{warehouse.contact_phone || '-'}</TableCell>
                  <TableCell className="px-6 py-4">
                    <Badge variant="outline" className={warehouse.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                      {warehouse.is_active ? '启用' : '停用'}
                    </Badge>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-right space-x-1">
                    {can('warehouse', 'update') && (
                    <Button variant="ghost" size="sm" onClick={() => openEditForm(warehouse)}>
                      <Pencil className="size-3.5" />
                      编辑
                    </Button>
                    )}
                    {can('warehouse', 'delete') && (
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteWarehouse(warehouse)}>
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

      {/* ==================== 仓库表单弹窗 ==================== */}
      <Dialog open={showForm} onOpenChange={(open) => !open && setShowForm(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingWarehouse ? '编辑仓库' : '新增仓库'}</DialogTitle>
          </DialogHeader>
          <WarehouseForm
            initial={editingWarehouse || undefined}
            onSubmit={handleSubmitWarehouse}
            onCancel={() => setShowForm(false)}
            loading={formLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
