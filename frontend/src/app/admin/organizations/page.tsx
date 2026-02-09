// src/app/admin/organizations/page.tsx
// 组织管理页面（超级管理员专属）
//
// 功能说明：
// 1. 组织列表展示（分页、搜索）
// 2. 创建/编辑/删除组织
// 3. 显示部门数量和用户数量

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  organizationsApi,
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
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
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { toast } from 'sonner';
import { Plus, Pencil, Trash2, Building2, Users, Network } from 'lucide-react';

// ==================== 工具函数 ====================

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

// ==================== 主页面 ====================

export default function OrganizationsPage() {
  const { isSuperAdmin } = usePermission();
  const confirm = useConfirm();

  // 列表状态
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 模态框状态
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);

  // 表单状态
  const [formData, setFormData] = useState<OrganizationCreate>({
    name: '',
    code: '',
    description: '',
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 搜索防抖
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // 加载列表
  const loadOrganizations = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await organizationsApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
      });
      setOrganizations(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || '加载组织列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    if (isSuperAdmin) {
      loadOrganizations();
    }
  }, [isSuperAdmin, loadOrganizations]);

  // 权限检查
  if (!isSuperAdmin) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-muted-foreground">无权限访问</h2>
          <p className="mt-2 text-sm text-muted-foreground">此页面仅超级管理员可访问</p>
        </div>
      </div>
    );
  }

  // 打开创建模态框
  const openCreateModal = () => {
    setEditingOrg(null);
    setFormData({ name: '', code: '', description: '' });
    setFormError('');
    setShowFormModal(true);
  };

  // 打开编辑模态框
  const openEditModal = (org: Organization) => {
    setEditingOrg(org);
    setFormData({
      name: org.name,
      code: org.code,
      description: org.description || '',
    });
    setFormError('');
    setShowFormModal(true);
  };

  // 提交表单（创建或更新）
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);

    try {
      if (editingOrg) {
        // 更新
        const updateData: OrganizationUpdate = {};
        if (formData.name !== editingOrg.name) updateData.name = formData.name;
        if (formData.code !== editingOrg.code) updateData.code = formData.code;
        if ((formData.description || '') !== (editingOrg.description || ''))
          updateData.description = formData.description;
        await organizationsApi.update(editingOrg.id, updateData);
        toast.success('组织已更新');
      } else {
        // 创建
        await organizationsApi.create(formData);
        toast.success('组织已创建');
      }
      setShowFormModal(false);
      loadOrganizations();
    } catch (err: any) {
      setFormError(err.message || '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 删除组织
  const handleDelete = async (org: Organization) => {
    const confirmed = await confirm({
      title: '删除组织',
      description: `确定要删除组织「${org.name}」吗？此操作无法撤销。`,
      confirmText: '删除',
      variant: 'destructive',
    });
    if (!confirmed) return;

    try {
      await organizationsApi.delete(org.id);
      toast.success('组织已删除');
      loadOrganizations();
    } catch (err: any) {
      toast.error(err.message || '删除失败');
    }
  };

  // 切换状态
  const handleToggleStatus = async (org: Organization) => {
    try {
      await organizationsApi.update(org.id, { is_active: !org.is_active });
      toast.success(org.is_active ? '已禁用' : '已启用');
      loadOrganizations();
    } catch (err: any) {
      toast.error(err.message || '操作失败');
    }
  };

  // 分页
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">组织管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理系统中的组织机构</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-1" />
          创建组织
        </Button>
      </div>

      {/* 搜索 */}
      <Card>
        <CardContent>
          <Input
            type="text"
            placeholder="搜索组织名称或编码..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="max-w-md"
          />
        </CardContent>
      </Card>

      {/* 错误提示 */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 text-destructive px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 组织表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">组织名称</TableHead>
                <TableHead className="px-6">编码</TableHead>
                <TableHead className="px-6">部门数</TableHead>
                <TableHead className="px-6">用户数</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6">创建时间</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="px-6 py-4 text-center">
                    <LoadingSpinner size="sm" text="加载中..." />
                  </TableCell>
                </TableRow>
              ) : organizations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="px-6 py-4 text-center text-muted-foreground">
                    暂无组织
                  </TableCell>
                </TableRow>
              ) : (
                organizations.map((org) => (
                  <TableRow key={org.id}>
                    <TableCell className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{org.name}</span>
                      </div>
                      {org.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                          {org.description}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <code className="text-sm bg-muted px-2 py-0.5 rounded">{org.code}</code>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Network className="h-3.5 w-3.5" />
                        {org.department_count ?? 0}
                      </div>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Users className="h-3.5 w-3.5" />
                        {org.user_count ?? 0}
                      </div>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <Badge
                        variant={org.is_active ? 'default' : 'destructive'}
                        className={`cursor-pointer ${org.is_active ? 'bg-green-600' : ''}`}
                        onClick={() => handleToggleStatus(org)}
                      >
                        {org.is_active ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {formatDate(org.created_at)}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditModal(org)}
                      >
                        <Pencil className="h-4 w-4 mr-1" />
                        编辑
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(org)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        删除
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="px-4 py-3 flex items-center justify-between border-t">
              <div className="text-sm text-muted-foreground">
                共 {total} 条记录，第 {page}/{totalPages} 页
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
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
        </CardContent>
      </Card>

      {/* 创建/编辑组织模态框 */}
      <Dialog open={showFormModal} onOpenChange={setShowFormModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingOrg ? '编辑组织' : '创建组织'}</DialogTitle>
            <DialogDescription>
              {editingOrg ? '修改组织信息' : '填写信息以创建新组织'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <div>
              <Label>组织名称</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder="例如：XX贸易有限公司"
                className="mt-1"
              />
            </div>
            <div>
              <Label>组织编码</Label>
              <Input
                type="text"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
                placeholder="例如：ORG001"
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">唯一标识符，创建后不建议修改</p>
            </div>
            <div>
              <Label>描述</Label>
              <Textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="组织描述（选填）"
                className="mt-1"
                rows={3}
              />
            </div>
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowFormModal(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? '保存中...' : editingOrg ? '保存' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
