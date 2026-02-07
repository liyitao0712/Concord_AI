// src/app/admin/layout.tsx
// 管理后台布局
//
// 功能说明：
// 1. 侧边栏分组导航（可折叠）
// 2. 顶部栏（用户信息、登出）
// 3. 权限验证（仅管理员可访问）

'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

// 导航项
interface NavItem {
  name: string;
  href: string;
  icon: string;
}

// 导航分组
interface NavGroup {
  label: string;
  icon: string;
  items: NavItem[];
}

// 顶级导航项（不在分组内）
interface NavTopLevel {
  topLevel: true;
  name: string;
  href: string;
  icon: string;
}

type NavEntry = NavGroup | NavTopLevel;

// 导航菜单配置
const navigation: NavEntry[] = [
  {
    label: '系统设置',
    icon: '⚙️',
    items: [
      { name: '系统仪表板', href: '/admin', icon: '📊' },
      { name: '用户管理', href: '/admin/users', icon: '👥' },
      { name: '系统日志', href: '/admin/logs', icon: '📋' },
      { name: '邮箱管理', href: '/admin/settings', icon: '📧' },
    ],
  },
  {
    label: 'AI 设置',
    icon: '🤖',
    items: [
      { name: 'LLM 配置', href: '/admin/llm', icon: '🤖' },
      { name: 'Agent 管理', href: '/admin/agents', icon: '🧠' },
      { name: '工作类型', href: '/admin/work-types', icon: '🏷️' },
      { name: 'Worker 管理', href: '/admin/workers', icon: '🔌' },
    ],
  },
  {
    label: '业务管理',
    icon: '💼',
    items: [
      { name: '客户管理', href: '/admin/customers', icon: '🏢' },
    ],
  },
  { topLevel: true, name: '邮件记录', href: '/admin/emails', icon: '📬' },
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

  // 分组展开状态（默认全部展开）
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    '系统设置': true,
    'AI 设置': true,
    '业务管理': true,
  });

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  // 判断导航项是否激活
  const isItemActive = (href: string) =>
    pathname === href || (href !== '/admin' && pathname.startsWith(href));

  // 判断分组是否有激活项
  const isGroupActive = (items: NavItem[]) =>
    items.some((item) => isItemActive(item.href));

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
      <aside className="fixed inset-y-0 left-0 w-64 bg-gray-900 overflow-y-auto">
        {/* Logo */}
        <div className="flex items-center justify-center h-16 bg-gray-800">
          <span className="text-white text-xl font-bold">Concord AI</span>
        </div>

        {/* 导航菜单 */}
        <nav className="mt-4 space-y-1">
          {navigation.map((entry) => {
            // 顶级导航项（不在分组内）
            if ('topLevel' in entry) {
              const active = isItemActive(entry.href);
              return (
                <Link
                  key={entry.name}
                  href={entry.href}
                  className={`flex items-center px-6 py-3 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-gray-800 text-white border-l-4 border-blue-500'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <span className="mr-3">{entry.icon}</span>
                  {entry.name}
                </Link>
              );
            }

            // 可折叠分组
            const group = entry;
            const expanded = expandedGroups[group.label] ?? true;
            const groupActive = isGroupActive(group.items);

            return (
              <div key={group.label}>
                {/* 分组标题 */}
                <button
                  onClick={() => toggleGroup(group.label)}
                  className={`w-full flex items-center justify-between px-6 py-3 text-sm font-medium transition-colors ${
                    groupActive
                      ? 'text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <span className="flex items-center">
                    <span className="mr-3">{group.icon}</span>
                    {group.label}
                  </span>
                  <svg
                    className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* 分组子项 */}
                {expanded && (
                  <div>
                    {group.items.map((item) => {
                      const active = isItemActive(item.href);
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={`flex items-center pl-10 pr-6 py-2.5 text-sm transition-colors ${
                            active
                              ? 'bg-gray-800 text-white border-l-4 border-blue-500'
                              : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                          }`}
                        >
                          <span className="mr-3">{item.icon}</span>
                          {item.name}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
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
