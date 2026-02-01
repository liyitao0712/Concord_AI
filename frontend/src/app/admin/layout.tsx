// src/app/admin/layout.tsx
// 管理后台布局
//
// 功能说明：
// 1. 侧边栏导航
// 2. 顶部栏（用户信息、登出）
// 3. 权限验证（仅管理员可访问）

'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

// 导航菜单配置
const navigation = [
  { name: '仪表盘', href: '/admin', icon: '📊' },
  { name: '用户管理', href: '/admin/users', icon: '👥' },
  { name: 'LLM 配置', href: '/admin/llm', icon: '🤖' },
  { name: 'Agent 管理', href: '/admin/agents', icon: '🧠' },
  { name: '意图管理', href: '/admin/intents', icon: '🎯' },
  { name: '系统日志', href: '/admin/logs', icon: '📋' },
  { name: 'Worker 管理', href: '/admin/workers', icon: '🔌' },
  { name: '邮箱管理', href: '/admin/settings', icon: '📧' },
  { name: '邮件记录', href: '/admin/emails', icon: '📬' },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading, isAuthenticated, isAdmin, logout } = useAuth();

  // 权限验证：未登录或非管理员跳转到登录页
  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login');
      } else if (!isAdmin) {
        router.push('/login');
      }
    }
  }, [isLoading, isAuthenticated, isAdmin, router]);

  // 登出处理
  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  // 加载中或无权限时显示空白
  if (isLoading || !isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 侧边栏 */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-gray-900">
        {/* Logo */}
        <div className="flex items-center justify-center h-16 bg-gray-800">
          <span className="text-white text-xl font-bold">Concord AI</span>
        </div>

        {/* 导航菜单 */}
        <nav className="mt-8">
          {navigation.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/admin' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white border-l-4 border-blue-500'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <span className="mr-3">{item.icon}</span>
                {item.name}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* 主内容区域 */}
      <div className="pl-64">
        {/* 顶部栏 */}
        <header className="bg-white shadow-sm">
          <div className="flex items-center justify-between h-16 px-6">
            {/* 面包屑或标题 */}
            <div className="text-lg font-medium text-gray-900">
              管理后台
            </div>

            {/* 用户信息 */}
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user?.name}
                <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                  管理员
                </span>
              </span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                退出登录
              </button>
            </div>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
