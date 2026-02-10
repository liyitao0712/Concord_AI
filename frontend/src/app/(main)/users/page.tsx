// src/app/admin/users/page.tsx
// 用户管理页面
//
// 功能说明：
// 1. 用户列表展示（分页、搜索、筛选）
// 2. 创建新用户
// 3. 编辑用户信息
// 4. 删除用户
// 5. 启用/禁用用户
// 6. 重置密码

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  toggleUserStatus,
  resetUserPassword,
  rolesApi,
  departmentsApi,
  User,
  UserListResponse,
  CreateUserRequest,
  UpdateUserRequest,
  RoleListItem,
  Department,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Pencil, KeyRound, Trash2, ShieldAlert, ShieldCheck } from 'lucide-react';
import { usePermission } from '@/hooks/usePermission';
import { PageHeader } from '@/components/PageHeader';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { ErrorAlert } from '@/components/ErrorAlert';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { formatDateTime } from '@/lib/format';

// ==================== 主页面 ====================

export default function UsersPage() {
  const { can } = usePermission();
  // 用户列表状态
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [roleFilter, setRoleFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 模态框状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'user',
  });
  const [newPassword, setNewPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 角色和部门下拉数据
  const [roleOptions, setRoleOptions] = useState<RoleListItem[]>([]);
  const [departmentOptions, setDepartmentOptions] = useState<Department[]>([]);

  // 加载角色和部门列表
  useEffect(() => {
    rolesApi.list().then((data) => setRoleOptions(data.items)).catch(() => {});
    departmentsApi.list().then((data) => setDepartmentOptions(data)).catch(() => {});
  }, []);

  // 加载用户列表
  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');

    const response = await getUsers({
      page,
      page_size: pageSize,
      search: debouncedSearch || undefined,
      role: roleFilter || undefined,
    });

    if (response.data) {
      setUsers(response.data.users);
      setTotal(response.data.total);
    } else {
      setError(response.error || '加载用户列表失败');
    }

    setLoading(false);
  }, [page, pageSize, debouncedSearch, roleFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // 搜索/筛选变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, roleFilter]);

  // 创建用户
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);

    const response = await createUser(formData as CreateUserRequest);

    if (response.data) {
      setShowCreateModal(false);
      setFormData({ email: '', password: '', name: '', role: 'user' });
      loadUsers();
    } else {
      setFormError(response.error || '创建失败');
    }

    setSubmitting(false);
  };

  // 更新用户
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    setFormError('');
    setSubmitting(true);

    const updateData: UpdateUserRequest & { role_id?: string; department_id?: string } = {};
    if (formData.email !== selectedUser.email) updateData.email = formData.email;
    if (formData.name !== selectedUser.name) updateData.name = formData.name;
    if (formData.role !== selectedUser.role) updateData.role = formData.role;
    const currentRoleId = (formData as any).role_id || '';
    const currentDeptId = (formData as any).department_id || '';
    if (currentRoleId !== (selectedUser.role_id || '')) updateData.role_id = currentRoleId || undefined;
    if (currentDeptId !== (selectedUser.department_id || '')) updateData.department_id = currentDeptId || undefined;

    const response = await updateUser(selectedUser.id, updateData as any);

    if (response.data) {
      setShowEditModal(false);
      setSelectedUser(null);
      loadUsers();
    } else {
      setFormError(response.error || '更新失败');
    }

    setSubmitting(false);
  };

  // 删除用户
  const handleDelete = async () => {
    if (!selectedUser) return;

    setSubmitting(true);
    const response = await deleteUser(selectedUser.id);

    if (response.data) {
      setShowDeleteModal(false);
      setSelectedUser(null);
      loadUsers();
    } else {
      setFormError(response.error || '删除失败');
    }

    setSubmitting(false);
  };

  // 切换用户状态
  const handleToggleStatus = async (user: User) => {
    const response = await toggleUserStatus(user.id);
    if (response.data) {
      loadUsers();
    } else {
      toast.error(response.error || '操作失败');
    }
  };

  // 重置密码
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    setFormError('');
    setSubmitting(true);

    const response = await resetUserPassword(selectedUser.id, newPassword);

    if (response.data) {
      setShowResetPasswordModal(false);
      setSelectedUser(null);
      setNewPassword('');
      toast.success('密码已重置');
    } else {
      setFormError(response.error || '重置失败');
    }

    setSubmitting(false);
  };

  // 打开编辑模态框
  const openEditModal = (user: User) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      password: '',
      name: user.name,
      role: user.role,
      role_id: user.role_id || '',
      department_id: user.department_id || '',
    } as any);
    setFormError('');
    setShowEditModal(true);
  };

  // 打开删除模态框
  const openDeleteModal = (user: User) => {
    setSelectedUser(user);
    setFormError('');
    setShowDeleteModal(true);
  };

  // 打开重置密码模态框
  const openResetPasswordModal = (user: User) => {
    setSelectedUser(user);
    setNewPassword('');
    setFormError('');
    setShowResetPasswordModal(true);
  };

  // 计算分页
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="用户管理"
        description="管理系统用户账户"
        actions={
          can('user', 'create') ? (
            <Button
              onClick={() => {
                setFormData({ email: '', password: '', name: '', role: 'user' });
                setFormError('');
                setShowCreateModal(true);
              }}
            >
              <Plus className="h-4 w-4 mr-1" />
              创建用户
            </Button>
          ) : undefined
        }
      />

      {/* 搜索和筛选 */}
      <SearchFilterBar
        searchPlaceholder="搜索邮箱或名称..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        filters={[
          {
            key: 'role',
            placeholder: '全部角色',
            options: [
              { value: 'admin', label: '管理员' },
              { value: 'user', label: '普通用户' },
            ],
          },
        ]}
        filterValues={{ role: roleFilter }}
        onFilterChange={(key, value) => {
          if (key === 'role') setRoleFilter(value);
        }}
      />

      {/* 错误提示 */}
      {error && <ErrorAlert message={error} onRetry={loadUsers} />}

      {/* 用户表格 */}
      <DataTableShell
        loading={loading}
        itemCount={users.length}
        columns={6}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle="暂无用户"
      >
        <TableHeader>
          <TableRow>
            <TableHead className="px-6">用户</TableHead>
            <TableHead className="px-6">角色</TableHead>
            <TableHead className="px-6">部门</TableHead>
            <TableHead className="px-6">状态</TableHead>
            <TableHead className="px-6">创建时间</TableHead>
            <TableHead className="px-6 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="px-6 py-4">
                <div>
                  <div className="text-sm font-medium">
                    {user.name}
                  </div>
                  <div className="text-sm text-muted-foreground">{user.email}</div>
                </div>
              </TableCell>
              <TableCell className="px-6 py-4">
                <div className="space-y-1">
                  <Badge
                    variant={user.role === 'admin' ? 'default' : 'secondary'}
                    className={user.role === 'admin' ? 'bg-purple-600' : ''}
                  >
                    {user.role === 'admin' ? '管理员' : '普通用户'}
                  </Badge>
                  {user.role_name && (
                    <div className="text-xs text-muted-foreground">{user.role_name}</div>
                  )}
                </div>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {user.department_name || '-'}
              </TableCell>
              <TableCell className="px-6 py-4">
                <Badge
                  variant={user.is_active ? 'default' : 'destructive'}
                  className={user.is_active ? 'bg-green-600' : ''}
                >
                  {user.is_active ? '活跃' : '禁用'}
                </Badge>
              </TableCell>
              <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                {formatDateTime(user.created_at)}
              </TableCell>
              <TableCell className="px-6 py-4 text-right space-x-2">
                {can('user', 'update') && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEditModal(user)}
                >
                  <Pencil className="h-4 w-4 mr-1" />
                  编辑
                </Button>
                )}
                {can('user', 'update') && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleStatus(user)}
                  className={
                    user.is_active
                      ? 'text-yellow-600 hover:text-yellow-700'
                      : 'text-green-600 hover:text-green-700'
                  }
                >
                  {user.is_active ? (
                    <>
                      <ShieldAlert className="h-4 w-4 mr-1" />
                      禁用
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-4 w-4 mr-1" />
                      启用
                    </>
                  )}
                </Button>
                )}
                {can('user', 'update') && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openResetPasswordModal(user)}
                >
                  <KeyRound className="h-4 w-4 mr-1" />
                  重置密码
                </Button>
                )}
                {can('user', 'delete') && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openDeleteModal(user)}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  删除
                </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </DataTableShell>

      {/* 创建用户模态框 */}
      <FormDialog
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="创建用户"
        description="填写用户信息以创建新账户"
        size="sm"
      >
          <form onSubmit={handleCreate} className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <div>
              <Label>邮箱</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label>密码</Label>
              <Input
                type="password"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                required
                minLength={6}
                className="mt-1"
              />
            </div>
            <div>
              <Label>名称</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label>角色</Label>
              <select
                value={formData.role}
                onChange={(e) =>
                  setFormData({ ...formData, role: e.target.value })
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>
            <div>
              <Label>权限角色</Label>
              <select
                value={(formData as any).role_id || ''}
                onChange={(e) =>
                  setFormData({ ...formData, role_id: e.target.value || undefined } as any)
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">未分配</option>
                {roleOptions.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground mt-1">决定用户的功能权限</p>
            </div>
            <div>
              <Label>部门</Label>
              <select
                value={(formData as any).department_id || ''}
                onChange={(e) =>
                  setFormData({ ...formData, department_id: e.target.value || undefined } as any)
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">未分配</option>
                {departmentOptions.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <FormFooter
              onCancel={() => setShowCreateModal(false)}
              submitText="创建"
              loading={submitting}
            />
          </form>
      </FormDialog>

      {/* 编辑用户模态框 */}
      <FormDialog
        open={showEditModal}
        onOpenChange={setShowEditModal}
        title="编辑用户"
        description="修改用户信息"
        size="sm"
      >
          <form onSubmit={handleUpdate} className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <div>
              <Label>邮箱</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label>名称</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label>角色</Label>
              <select
                value={formData.role}
                onChange={(e) =>
                  setFormData({ ...formData, role: e.target.value })
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>
            <div>
              <Label>权限角色</Label>
              <select
                value={(formData as any).role_id || ''}
                onChange={(e) =>
                  setFormData({ ...formData, role_id: e.target.value || undefined } as any)
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">未分配</option>
                {roleOptions.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground mt-1">决定用户的功能权限</p>
            </div>
            <div>
              <Label>部门</Label>
              <select
                value={(formData as any).department_id || ''}
                onChange={(e) =>
                  setFormData({ ...formData, department_id: e.target.value || undefined } as any)
                }
                className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">未分配</option>
                {departmentOptions.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <FormFooter
              onCancel={() => setShowEditModal(false)}
              loading={submitting}
            />
          </form>
      </FormDialog>

      {/* 删除确认模态框 */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除用户</DialogTitle>
            <DialogDescription>此操作无法撤销</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <p className="text-muted-foreground">
              确定要删除用户 <strong className="text-foreground">{selectedUser?.email}</strong> 吗？
            </p>
            <p className="text-sm text-destructive">此操作无法撤销！</p>
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowDeleteModal(false)}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={submitting}
              >
                {submitting ? '删除中...' : '删除'}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* 重置密码模态框 */}
      <FormDialog
        open={showResetPasswordModal}
        onOpenChange={setShowResetPasswordModal}
        title="重置密码"
        description={`为用户 ${selectedUser?.email} 设置新密码`}
        size="sm"
      >
          <form onSubmit={handleResetPassword} className="space-y-4">
            {formError && (
              <div className="text-destructive text-sm">{formError}</div>
            )}
            <div>
              <Label>新密码</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                className="mt-1"
                placeholder="至少 6 位"
              />
            </div>
            <FormFooter
              onCancel={() => setShowResetPasswordModal(false)}
              submitText="重置密码"
              loading={submitting}
            />
          </form>
      </FormDialog>
    </div>
  );
}
