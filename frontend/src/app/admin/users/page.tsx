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
  User,
  UserListResponse,
  CreateUserRequest,
  UpdateUserRequest,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { toast } from 'sonner';
import { Plus, Pencil, KeyRound, Trash2, ShieldAlert, ShieldCheck } from 'lucide-react';

// ==================== 主页面 ====================

export default function UsersPage() {
  // 用户列表状态
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState('');
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

  // 加载用户列表
  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');

    const response = await getUsers({
      page,
      page_size: pageSize,
      search: search || undefined,
      role: roleFilter || undefined,
    });

    if (response.data) {
      setUsers(response.data.users);
      setTotal(response.data.total);
    } else {
      setError(response.error || '加载用户列表失败');
    }

    setLoading(false);
  }, [page, pageSize, search, roleFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // 搜索防抖
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

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

    const updateData: UpdateUserRequest = {};
    if (formData.email !== selectedUser.email) updateData.email = formData.email;
    if (formData.name !== selectedUser.name) updateData.name = formData.name;
    if (formData.role !== selectedUser.role) updateData.role = formData.role;

    const response = await updateUser(selectedUser.id, updateData);

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
    });
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">用户管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理系统用户账户</p>
        </div>
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
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Input
              type="text"
              placeholder="搜索邮箱或名称..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="flex-1 min-w-[200px]"
            />
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">全部角色</option>
              <option value="admin">管理员</option>
              <option value="user">普通用户</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* 错误提示 */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 text-destructive px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 用户表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">用户</TableHead>
                <TableHead className="px-6">角色</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6">创建时间</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="px-6 py-4 text-center">
                    <LoadingSpinner size="sm" text="加载中..." />
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="px-6 py-4 text-center text-muted-foreground">
                    暂无用户
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
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
                      <Badge
                        variant={user.role === 'admin' ? 'default' : 'secondary'}
                        className={user.role === 'admin' ? 'bg-purple-600' : ''}
                      >
                        {user.role === 'admin' ? '管理员' : '普通用户'}
                      </Badge>
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
                      {new Date(user.created_at).toLocaleDateString('zh-CN')}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditModal(user)}
                      >
                        <Pencil className="h-4 w-4 mr-1" />
                        编辑
                      </Button>
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
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openResetPasswordModal(user)}
                      >
                        <KeyRound className="h-4 w-4 mr-1" />
                        重置密码
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openDeleteModal(user)}
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

      {/* 创建用户模态框 */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-md">
          <DialogHeader>
            <DialogTitle>创建用户</DialogTitle>
            <DialogDescription>填写用户信息以创建新账户</DialogDescription>
          </DialogHeader>
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
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateModal(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={submitting}
              >
                {submitting ? '创建中...' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 编辑用户模态框 */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-md">
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
            <DialogDescription>修改用户信息</DialogDescription>
          </DialogHeader>
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
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowEditModal(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={submitting}
              >
                {submitting ? '保存中...' : '保存'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 删除确认模态框 */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="max-w-md">
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
      <Dialog open={showResetPasswordModal} onOpenChange={setShowResetPasswordModal}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-md">
          <DialogHeader>
            <DialogTitle>重置密码</DialogTitle>
            <DialogDescription>
              为用户 <strong>{selectedUser?.email}</strong> 设置新密码
            </DialogDescription>
          </DialogHeader>
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
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowResetPasswordModal(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={submitting}
              >
                {submitting ? '重置中...' : '重置密码'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
