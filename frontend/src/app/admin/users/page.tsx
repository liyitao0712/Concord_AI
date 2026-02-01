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

// ==================== 模态框组件 ====================

function Modal({
  isOpen,
  onClose,
  title,
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        {/* 背景遮罩 */}
        <div
          className="fixed inset-0 bg-black opacity-50"
          onClick={onClose}
        />

        {/* 模态框内容 */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
          {children}
        </div>
      </div>
    </div>
  );
}

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
      alert(response.error || '操作失败');
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
      alert('密码已重置');
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
          <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
          <p className="mt-1 text-sm text-gray-500">管理系统用户账户</p>
        </div>
        <button
          onClick={() => {
            setFormData({ email: '', password: '', name: '', role: 'user' });
            setFormError('');
            setShowCreateModal(true);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          创建用户
        </button>
      </div>

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="搜索邮箱或名称..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">全部角色</option>
            <option value="admin">管理员</option>
            <option value="user">普通用户</option>
          </select>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 用户表格 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                用户
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                角色
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建时间
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  加载中...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  暂无用户
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {user.name}
                      </div>
                      <div className="text-sm text-gray-500">{user.email}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        user.role === 'admin'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {user.role === 'admin' ? '管理员' : '普通用户'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {user.is_active ? '活跃' : '禁用'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(user.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => openEditModal(user)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleToggleStatus(user)}
                      className={
                        user.is_active
                          ? 'text-yellow-600 hover:text-yellow-900'
                          : 'text-green-600 hover:text-green-900'
                      }
                    >
                      {user.is_active ? '禁用' : '启用'}
                    </button>
                    <button
                      onClick={() => openResetPasswordModal(user)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      重置密码
                    </button>
                    <button
                      onClick={() => openDeleteModal(user)}
                      className="text-red-600 hover:text-red-900"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
            <div className="text-sm text-gray-500">
              共 {total} 条记录，第 {page}/{totalPages} 页
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-50"
              >
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 创建用户模态框 */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="创建用户"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {formError && (
            <div className="text-red-600 text-sm">{formError}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              required
              minLength={6}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              名称
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              角色
            </label>
            <select
              value={formData.role}
              onChange={(e) =>
                setFormData({ ...formData, role: e.target.value })
              }
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => setShowCreateModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </Modal>

      {/* 编辑用户模态框 */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="编辑用户"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          {formError && (
            <div className="text-red-600 text-sm">{formError}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              名称
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              角色
            </label>
            <select
              value={formData.role}
              onChange={(e) =>
                setFormData({ ...formData, role: e.target.value })
              }
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => setShowEditModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </Modal>

      {/* 删除确认模态框 */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="删除用户"
      >
        <div className="space-y-4">
          {formError && (
            <div className="text-red-600 text-sm">{formError}</div>
          )}
          <p className="text-gray-700">
            确定要删除用户 <strong>{selectedUser?.email}</strong> 吗？
          </p>
          <p className="text-sm text-red-600">此操作无法撤销！</p>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => setShowDeleteModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              取消
            </button>
            <button
              onClick={handleDelete}
              disabled={submitting}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {submitting ? '删除中...' : '删除'}
            </button>
          </div>
        </div>
      </Modal>

      {/* 重置密码模态框 */}
      <Modal
        isOpen={showResetPasswordModal}
        onClose={() => setShowResetPasswordModal(false)}
        title="重置密码"
      >
        <form onSubmit={handleResetPassword} className="space-y-4">
          {formError && (
            <div className="text-red-600 text-sm">{formError}</div>
          )}
          <p className="text-gray-700">
            为用户 <strong>{selectedUser?.email}</strong> 设置新密码
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              新密码
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={6}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="至少 6 位"
            />
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => setShowResetPasswordModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? '重置中...' : '重置密码'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
