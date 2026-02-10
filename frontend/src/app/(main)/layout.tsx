// src/app/admin/layout.tsx
// 管理后台布局
//
// 功能说明：
// 1. 桌面端：侧边栏分组导航（可折叠）
// 2. 移动端：顶部汉堡菜单 + Sheet 抽屉导航
// 3. 顶部栏（用户信息、登出）
// 4. 权限验证（仅管理员可访问）

'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useDevice } from '@/lib/device';
import { navigation } from '@/lib/navigation';
import type { NavItem, NavEntry } from '@/lib/navigation';
import { hasPermission, hasAnyPermission } from '@/lib/permissions';
import { MobileNav } from '@/components/MobileNav';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { PageLoading } from '@/components/LoadingSpinner';
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading, isAuthenticated, isAdmin, logout } = useAuth();
  const { isMobile } = useDevice();

  // 从导航配置构建路由权限映射（按 href 长度降序，保证最具体的路由优先匹配）
  const routePermissionMap = useMemo(() => {
    const entries: Array<{
      href: string;
      superAdminOnly?: boolean;
      requiredPermission?: { resource: string; action: string };
      requiredPermissions?: Array<{ resource: string; action: string }>;
    }> = [];
    for (const entry of navigation) {
      if ('topLevel' in entry) {
        if (entry.requiredPermission || entry.requiredPermissions || entry.superAdminOnly) {
          entries.push(entry);
        }
      } else {
        for (const item of entry.items) {
          if (item.requiredPermission || item.requiredPermissions || ('superAdminOnly' in item && item.superAdminOnly)) {
            entries.push(item);
          }
        }
      }
    }
    return entries.sort((a, b) => b.href.length - a.href.length);
  }, []);

  // 检查当前路由是否有权限访问
  const checkRoutePermission = useCallback((currentPath: string): boolean => {
    const match = routePermissionMap.find((rp) =>
      rp.href === '/system'
        ? currentPath === '/system'
        : currentPath === rp.href || currentPath.startsWith(rp.href + '/')
    );
    if (!match) return true; // 无匹配权限配置，默认允许
    if (match.superAdminOnly && !user?.is_super_admin) return false;
    if (match.requiredPermission) {
      if (!hasPermission(user, match.requiredPermission.resource, match.requiredPermission.action)) return false;
    }
    if (match.requiredPermissions) {
      if (!hasAnyPermission(user, match.requiredPermissions)) return false;
    }
    return true;
  }, [routePermissionMap, user]);

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

  // 页面级权限守卫：无权限时重定向到牛批工作台
  useEffect(() => {
    if (!isLoading && isAuthenticated && isAdmin && user) {
      if (!checkRoutePermission(pathname)) {
        router.replace('/dashboard');
      }
    }
  }, [pathname, isLoading, isAuthenticated, isAdmin, user, checkRoutePermission, router]);

  // 登出处理
  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  // 侧边栏收起状态
  const [collapsed, setCollapsed] = useState(false);

  // 分组展开状态（默认全部展开）
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    'AI 设置': true,
    '基础数据': true,
    '系统设置': true,
  });

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  // 判断导航项是否激活
  const isItemActive = (href: string) =>
    pathname === href || (href !== '/system' && pathname.startsWith(href));

  // 判断分组是否有激活项
  const isGroupActive = (items: NavItem[]) =>
    items.some((item) => isItemActive(item.href));

  // 按权限过滤导航菜单
  const filteredNavigation = useMemo(() => {
    return navigation
      .map((entry) => {
        if ('topLevel' in entry) {
          // 超管限定项
          if ('superAdminOnly' in entry && entry.superAdminOnly && !user?.is_super_admin) return null;
          // 权限检查
          if (entry.requiredPermission) {
            if (!hasPermission(user, entry.requiredPermission.resource, entry.requiredPermission.action)) return null;
          }
          if (entry.requiredPermissions) {
            if (!hasAnyPermission(user, entry.requiredPermissions)) return null;
          }
          return entry;
        }
        // 分组：过滤子项，空组隐藏
        const filteredItems = entry.items.filter((item) => {
          if ('superAdminOnly' in item && item.superAdminOnly && !user?.is_super_admin) return false;
          if (item.requiredPermission) {
            return hasPermission(user, item.requiredPermission.resource, item.requiredPermission.action);
          }
          if (item.requiredPermissions) {
            return hasAnyPermission(user, item.requiredPermissions);
          }
          return true;
        });
        if (filteredItems.length === 0) return null;
        return { ...entry, items: filteredItems };
      })
      .filter(Boolean) as NavEntry[];
  }, [user]);

  // 根据当前路径计算顶级菜单名称
  const currentTitle = useMemo(() => {
    for (const entry of filteredNavigation) {
      if ('topLevel' in entry) {
        if (pathname === entry.href || (entry.href !== '/system' && pathname.startsWith(entry.href))) {
          return entry.name;
        }
      } else {
        for (const item of entry.items) {
          if (pathname === item.href || (item.href !== '/system' && pathname.startsWith(item.href))) {
            return item.name;
          }
        }
      }
    }
    return '';
  }, [pathname, filteredNavigation]);

  // 加载中或无权限时显示空白
  if (isLoading || !isAuthenticated || !isAdmin) {
    return <PageLoading />;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-muted/40">
        {/* 桌面端侧边栏（移动端隐藏） */}
        <aside className={`hidden md:block fixed inset-y-0 left-0 bg-slate-950 border-r border-slate-800 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
          {/* Logo */}
          <div className="flex items-center justify-center h-16 border-b border-slate-800">
            {collapsed ? (
              <span className="text-white text-lg font-bold">C</span>
            ) : (
              <span className="text-white text-xl font-bold tracking-tight">Concord AI</span>
            )}
          </div>

          {/* 导航菜单 */}
          <ScrollArea className="h-[calc(100vh-4rem)]">
            <nav className={`mt-2 space-y-1 ${collapsed ? 'px-2' : 'px-3'}`}>
              {filteredNavigation.map((entry) => {
                // 顶级导航项
                if ('topLevel' in entry) {
                  const active = isItemActive(entry.href);
                  const Icon = entry.icon;
                  const link = (
                    <Link
                      key={entry.name}
                      href={entry.href}
                      className={`flex items-center gap-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                        collapsed ? 'justify-center px-0' : 'px-3'
                      } ${
                        active
                          ? 'bg-slate-800 text-white'
                          : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                      }`}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      {!collapsed && entry.name}
                    </Link>
                  );

                  if (collapsed) {
                    return (
                      <Tooltip key={entry.name}>
                        <TooltipTrigger asChild>{link}</TooltipTrigger>
                        <TooltipContent side="right">{entry.name}</TooltipContent>
                      </Tooltip>
                    );
                  }
                  return link;
                }

                // 可折叠分组
                const group = entry;
                const expanded = expandedGroups[group.label] ?? true;
                const groupActive = isGroupActive(group.items);
                const GroupIcon = group.icon;

                // 收起状态：只显示分组图标和子项图标
                if (collapsed) {
                  return (
                    <div key={group.label} className="pt-2">
                      <Separator className="mb-2 bg-slate-800" />
                      {group.items.map((item) => {
                        const active = isItemActive(item.href);
                        const Icon = item.icon;
                        return (
                          <Tooltip key={item.name}>
                            <TooltipTrigger asChild>
                              <Link
                                href={item.href}
                                className={`flex items-center justify-center py-2.5 rounded-md transition-colors ${
                                  active
                                    ? 'bg-slate-800 text-white'
                                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                                }`}
                              >
                                <Icon className="h-4 w-4" />
                              </Link>
                            </TooltipTrigger>
                            <TooltipContent side="right">{item.name}</TooltipContent>
                          </Tooltip>
                        );
                      })}
                    </div>
                  );
                }

                return (
                  <div key={group.label} className="pt-2">
                    <Separator className="mb-2 bg-slate-800" />
                    {/* 分组标题 */}
                    <button
                      onClick={() => toggleGroup(group.label)}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
                        groupActive
                          ? 'text-slate-200'
                          : 'text-slate-500 hover:text-slate-300'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <GroupIcon className="h-3.5 w-3.5" />
                        {group.label}
                      </span>
                      <ChevronDown
                        className={`h-3.5 w-3.5 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
                      />
                    </button>

                    {/* 分组子项 */}
                    {expanded && (
                      <div className="mt-1 space-y-0.5">
                        {group.items.map((item) => {
                          const active = isItemActive(item.href);
                          const Icon = item.icon;
                          return (
                            <Link
                              key={item.name}
                              href={item.href}
                              className={`flex items-center gap-3 pl-6 pr-3 py-2 text-sm transition-colors rounded-md ${
                                active
                                  ? 'bg-slate-800 text-white'
                                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                              }`}
                            >
                              <Icon className="h-4 w-4 flex-shrink-0" />
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
          </ScrollArea>

          {/* 收起/展开按钮 */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="absolute -right-3 top-20 z-40 hidden md:flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        </aside>

        {/* 主内容区域 */}
        <div className={`transition-all duration-300 ${isMobile ? 'pl-0' : (collapsed ? 'pl-16' : 'pl-64')}`}>
          {/* 顶部栏 */}
          <header className="sticky top-0 z-30 bg-background border-b">
            <div className="flex items-center justify-between h-14 px-4 md:px-6">
              <div className="flex items-center gap-3">
                {/* 移动端汉堡菜单 */}
                <MobileNav navigation={filteredNavigation} />
                {currentTitle && (
                  <div className="text-2xl font-bold">
                    {currentTitle}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground hidden sm:inline">
                  {user?.name}
                </span>
                <Badge variant="secondary" className="hidden sm:inline-flex">
                  {user?.role_name || (user?.is_super_admin ? '超级管理员' : '管理员')}
                </Badge>
                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground">
                  <LogOut className="h-4 w-4 md:mr-1" />
                  <span className="hidden md:inline">退出</span>
                </Button>
              </div>
            </div>
          </header>

          {/* 页面内容 */}
          <main className="p-4 md:p-6">
            {children}
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
