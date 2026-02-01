// src/app/login/page.tsx
// 登录页面
//
// 功能说明：
// 1. 管理员登录表单
// 2. 验证用户身份
// 3. 登录成功后跳转到管理后台

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isAdmin, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 如果已登录且是管理员，跳转到后台
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      if (isAdmin) {
        router.push('/admin');
      } else {
        setError('您不是管理员，无法访问管理后台');
      }
    }
  }, [isLoading, isAuthenticated, isAdmin, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    const result = await login({ email, password });

    if (result.success) {
      // login 后会自动刷新用户信息，useEffect 会处理跳转
    } else {
      setError(result.error || '登录失败');
    }

    setSubmitting(false);
  };

  // 加载中显示
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Concord AI</h1>
          <p className="text-gray-500 mt-2">管理后台登录</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* 登录表单 */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 邮箱 */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="admin@example.com"
            />
          </div>

          {/* 密码 */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="••••••••"
            />
          </div>

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? '登录中...' : '登录'}
          </button>
        </form>

        {/* 提示 */}
        <div className="mt-6 text-center text-sm text-gray-500">
          仅限系统管理员登录
        </div>
      </div>
    </div>
  );
}
