// src/app/admin/roles/page.tsx
// 角色管理页面（权限矩阵）
//
// 功能说明：
// 1. 左侧：角色列表（创建/编辑/删除角色）
// 2. 右侧：权限矩阵（按资源分组，可勾选 read/create/update/delete）
// 3. 数据范围配置（全部/本部门/个人等）

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  rolesApi,
  permissionsApi,
  RoleListItem,
  RoleDetail,
  RoleCreate,
  RoleUpdate,
  PermissionGroup,
  PermissionItem,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
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
import {
  Plus,
  Pencil,
  Trash2,
  Shield,
  ShieldCheck,
  Users,
  Save,
  Lock,
} from 'lucide-react';

// 动作标签映射
const ACTION_LABELS: Record<string, string> = {
  read: '查看',
  create: '创建',
  update: '编辑',
  delete: '删除',
};

// 动作显示顺序
const ACTION_ORDER = ['read', 'create', 'update', 'delete'];

// ==================== 主页面 ====================

export default function RolesPage() {
  const { can } = usePermission();
  const confirm = useConfirm();
  const canEdit = can('setting', 'update');

  // 角色列表
  const [roles, setRoles] = useState<RoleListItem[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [roleDetailLoading, setRoleDetailLoading] = useState(false);

  // 权限列表
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [permissionsLoading, setPermissionsLoading] = useState(true);

  // 选中的权限 ID
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<string>>(new Set());
  const [permissionsDirty, setPermissionsDirty] = useState(false);
  const [savingPermissions, setSavingPermissions] = useState(false);

  // 模态框状态
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleListItem | null>(null);
  const [formData, setFormData] = useState<RoleCreate>({
    name: '',
    code: '',
    description: '',
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 加载角色列表
  const loadRoles = useCallback(async () => {
    setRolesLoading(true);
    try {
      const data = await rolesApi.list();
      setRoles(data.items);
      // 如果没有选中的角色，选中第一个
      if (!selectedRoleId && data.items.length > 0) {
        setSelectedRoleId(data.items[0].id);
      }
    } catch (err: any) {
      toast.error(err.message || '加载角色列表失败');
    } finally {
      setRolesLoading(false);
    }
  }, [selectedRoleId]);

  // 加载权限列表
  const loadPermissions = useCallback(async () => {
    setPermissionsLoading(true);
    try {
      const data = await permissionsApi.list();
      setPermissionGroups(data);
    } catch (err: any) {
      toast.error(err.message || '加载权限列表失败');
    } finally {
      setPermissionsLoading(false);
    }
  }, []);

  // 加载角色详情
  const loadRoleDetail = useCallback(async (roleId: string) => {
    setRoleDetailLoading(true);
    try {
      const data = await rolesApi.get(roleId);
      setSelectedRole(data);
      setSelectedPermissionIds(new Set(data.permission_ids));
      setPermissionsDirty(false);
    } catch (err: any) {
      toast.error(err.message || '加载角色详情失败');
    } finally {
      setRoleDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoles();
    loadPermissions();
  }, [loadRoles, loadPermissions]);

  useEffect(() => {
    if (selectedRoleId) {
      loadRoleDetail(selectedRoleId);
    }
  }, [selectedRoleId, loadRoleDetail]);

  // 切换权限
  const togglePermission = (permissionId: string) => {
    setSelectedPermissionIds((prev) => {
      const next = new Set(prev);
      if (next.has(permissionId)) {
        next.delete(permissionId);
      } else {
        next.add(permissionId);
      }
      return next;
    });
    setPermissionsDirty(true);
  };

  // 全选/取消一个资源组的所有权限
  const toggleResourceGroup = (group: PermissionGroup) => {
    const groupIds = group.permissions.map((p) => p.id);
    const allSelected = groupIds.every((id) => selectedPermissionIds.has(id));

    setSelectedPermissionIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        groupIds.forEach((id) => next.delete(id));
      } else {
        groupIds.forEach((id) => next.add(id));
      }
      return next;
    });
    setPermissionsDirty(true);
  };

  // 保存权限
  const savePermissions = async () => {
    if (!selectedRoleId) return;
    setSavingPermissions(true);
    try {
      await rolesApi.setPermissions(selectedRoleId, Array.from(selectedPermissionIds));
      toast.success('权限已保存');
      setPermissionsDirty(false);
      // 重新加载角色列表以更新 permission_ids
      loadRoles();
    } catch (err: any) {
      toast.error(err.message || '保存权限失败');
    } finally {
      setSavingPermissions(false);
    }
  };

  // 打开创建模态框
  const openCreateModal = () => {
    setEditingRole(null);
    setFormData({ name: '', code: '', description: '' });
    setFormError('');
    setShowFormModal(true);
  };

  // 打开编辑模态框
  const openEditModal = (role: RoleListItem) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      code: role.code,
      description: role.description || '',
    });
    setFormError('');
    setShowFormModal(true);
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);

    try {
      if (editingRole) {
        const updateData: RoleUpdate = {};
        if (formData.name !== editingRole.name) updateData.name = formData.name;
        if (formData.code !== editingRole.code) updateData.code = formData.code;
        if ((formData.description || '') !== (editingRole.description || ''))
          updateData.description = formData.description;
        await rolesApi.update(editingRole.id, updateData);
        toast.success('角色已更新');
      } else {
        const newRole = await rolesApi.create(formData);
        toast.success('角色已创建');
        setSelectedRoleId(newRole.id);
      }
      setShowFormModal(false);
      loadRoles();
    } catch (err: any) {
      setFormError(err.message || '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 删除角色
  const handleDelete = async (role: RoleListItem) => {
    if (role.is_system) {
      toast.error('系统内置角色不可删除');
      return;
    }

    const confirmed = await confirm({
      title: '删除角色',
      description: `确定要删除角色「${role.name}」吗？此操作无法撤销。该角色下有 ${role.user_count} 个用户。`,
      confirmText: '删除',
      variant: 'destructive',
    });
    if (!confirmed) return;

    try {
      await rolesApi.delete(role.id);
      toast.success('角色已删除');
      if (selectedRoleId === role.id) {
        setSelectedRoleId(null);
        setSelectedRole(null);
      }
      loadRoles();
    } catch (err: any) {
      toast.error(err.message || '删除失败');
    }
  };

  // 按 action 排序后获取权限
  const getPermissionByAction = (group: PermissionGroup, action: string): PermissionItem | undefined => {
    return group.permissions.find((p) => p.action === action);
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">角色管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理角色和权限分配</p>
        </div>
      </div>

      {/* 主体内容：左侧角色列表 + 右侧权限矩阵 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 左侧：角色列表 */}
        <div className="lg:col-span-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="h-4 w-4" />
                角色列表
              </CardTitle>
              {canEdit && (
                <Button size="sm" onClick={openCreateModal}>
                  <Plus className="h-4 w-4 mr-1" />
                  新建
                </Button>
              )}
            </CardHeader>
            <CardContent className="p-0">
              {rolesLoading ? (
                <div className="py-8 text-center">
                  <LoadingSpinner size="sm" text="加载中..." />
                </div>
              ) : roles.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground text-sm">
                  暂无角色
                </div>
              ) : (
                <div className="divide-y">
                  {roles.map((role) => (
                    <div
                      key={role.id}
                      className={`px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                        selectedRoleId === role.id ? 'bg-muted' : ''
                      }`}
                      onClick={() => setSelectedRoleId(role.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          {role.is_system ? (
                            <Lock className="h-4 w-4 text-amber-500 flex-shrink-0" />
                          ) : (
                            <ShieldCheck className="h-4 w-4 text-blue-500 flex-shrink-0" />
                          )}
                          <div className="min-w-0">
                            <div className="font-medium text-sm truncate">{role.name}</div>
                            <div className="text-xs text-muted-foreground truncate">
                              {role.code}
                              {role.description && ` - ${role.description}`}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="h-3 w-3" />
                            {role.user_count}
                          </div>
                          {canEdit && !role.is_system && (
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openEditModal(role);
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-destructive hover:text-destructive"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(role);
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 右侧：权限矩阵 */}
        <div className="lg:col-span-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-base">
                {selectedRole ? (
                  <span className="flex items-center gap-2">
                    权限配置 - {selectedRole.name}
                    {selectedRole.is_system && (
                      <Badge variant="outline" className="text-xs">系统角色</Badge>
                    )}
                  </span>
                ) : (
                  '权限配置'
                )}
              </CardTitle>
              {canEdit && selectedRole && permissionsDirty && (
                <Button
                  size="sm"
                  onClick={savePermissions}
                  disabled={savingPermissions}
                >
                  <Save className="h-4 w-4 mr-1" />
                  {savingPermissions ? '保存中...' : '保存权限'}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {!selectedRoleId ? (
                <div className="py-12 text-center text-muted-foreground text-sm">
                  请从左侧选择一个角色
                </div>
              ) : roleDetailLoading || permissionsLoading ? (
                <div className="py-12 text-center">
                  <LoadingSpinner size="sm" text="加载中..." />
                </div>
              ) : permissionGroups.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground text-sm">
                  暂无权限数据
                </div>
              ) : (
                <div className="space-y-6">
                  {/* 权限矩阵表格 */}
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-muted/50">
                          <th className="text-left px-4 py-3 text-sm font-medium w-48">
                            资源模块
                          </th>
                          {ACTION_ORDER.map((action) => (
                            <th
                              key={action}
                              className="text-center px-4 py-3 text-sm font-medium w-24"
                            >
                              {ACTION_LABELS[action] || action}
                            </th>
                          ))}
                          <th className="text-center px-4 py-3 text-sm font-medium w-24">
                            全选
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {permissionGroups.map((group) => {
                          const groupIds = group.permissions.map((p) => p.id);
                          const allSelected = groupIds.length > 0 && groupIds.every((id) => selectedPermissionIds.has(id));
                          const someSelected = groupIds.some((id) => selectedPermissionIds.has(id));

                          return (
                            <tr key={group.resource} className="border-t hover:bg-muted/30">
                              <td className="px-4 py-3 text-sm font-medium">
                                {group.resource_label}
                              </td>
                              {ACTION_ORDER.map((action) => {
                                const perm = getPermissionByAction(group, action);
                                if (!perm) {
                                  return (
                                    <td key={action} className="text-center px-4 py-3">
                                      <span className="text-muted-foreground/30">-</span>
                                    </td>
                                  );
                                }
                                return (
                                  <td key={action} className="text-center px-4 py-3">
                                    <Checkbox
                                      checked={selectedPermissionIds.has(perm.id)}
                                      onCheckedChange={() => togglePermission(perm.id)}
                                      disabled={!canEdit}
                                    />
                                  </td>
                                );
                              })}
                              <td className="text-center px-4 py-3">
                                <Checkbox
                                  checked={allSelected}
                                  // 部分选中时显示 indeterminate 状态
                                  {...(someSelected && !allSelected ? { 'data-state': 'indeterminate' } : {})}
                                  onCheckedChange={() => toggleResourceGroup(group)}
                                  disabled={!canEdit || groupIds.length === 0}
                                />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* 数据范围配置 */}
                  {selectedRole && selectedRole.data_scopes && selectedRole.data_scopes.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium mb-3">数据范围</h3>
                      <div className="border rounded-lg overflow-hidden">
                        <table className="w-full">
                          <thead>
                            <tr className="bg-muted/50">
                              <th className="text-left px-4 py-2 text-sm font-medium">资源</th>
                              <th className="text-left px-4 py-2 text-sm font-medium">范围类型</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedRole.data_scopes.map((scope, index) => (
                              <tr key={index} className="border-t">
                                <td className="px-4 py-2 text-sm">{scope.resource}</td>
                                <td className="px-4 py-2 text-sm">
                                  <Badge variant="outline">{scope.scope_type}</Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 创建/编辑角色模态框 */}
      <Dialog open={showFormModal} onOpenChange={setShowFormModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingRole ? '编辑角色' : '创建角色'}</DialogTitle>
            <DialogDescription>
              {editingRole ? '修改角色信息' : '填写信息以创建新角色'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <div>
              <Label>角色名称</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder="例如：销售经理"
                className="mt-1"
              />
            </div>
            <div>
              <Label>角色编码</Label>
              <Input
                type="text"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
                placeholder="例如：sales_manager"
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">唯一标识符，建议使用英文下划线格式</p>
            </div>
            <div>
              <Label>描述</Label>
              <Textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="角色描述（选填）"
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
                {submitting ? '保存中...' : editingRole ? '保存' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
