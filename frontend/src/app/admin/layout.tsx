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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { PageLoading } from '@/components/LoadingSpinner';
import {
  Mail,
  Building2,
  Factory,
  FolderTree,
  Package,
  Bot,
  Cpu,
  Brain,
  Tags,
  Plug,
  Database,
  Globe,
  FileText,
  CreditCard,
  Settings,
  LayoutDashboard,
  Users,
  ScrollText,
  MailCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LogOut,
  type LucideIcon,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// 导航项
interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

// 导航分组
interface NavGroup {
  label: string;
  icon: LucideIcon;
  items: NavItem[];
}

// 顶级导航项（不在分组内）
interface NavTopLevel {
  topLevel: true;
  name: string;
  href: string;
  icon: LucideIcon;
}

type NavEntry = NavGroup | NavTopLevel;

// 导航菜单配置
const navigation: NavEntry[] = [
  { topLevel: true, name: '邮件记录', href: '/admin/emails', icon: Mail },
  { topLevel: true, name: '客户管理', href: '/admin/customers', icon: Building2 },
  { topLevel: true, name: '供应商管理', href: '/admin/suppliers', icon: Factory },
  { topLevel: true, name: '品类管理', href: '/admin/categories', icon: FolderTree },
  { topLevel: true, name: '产品管理', href: '/admin/products', icon: Package },
  {
    label: 'AI 设置',
    icon: Bot,
    items: [
      { name: 'LLM 配置', href: '/admin/llm', icon: Cpu },
      { name: 'Agent 管理', href: '/admin/agents', icon: Brain },
      { name: '工作类型', href: '/admin/work-types', icon: Tags },
      { name: 'Worker 管理', href: '/admin/workers', icon: Plug },
    ],
  },
  {
    label: '基础数据',
    icon: Database,
    items: [
      { name: '国家数据库', href: '/admin/countries', icon: Globe },
      { name: '贸易术语', href: '/admin/trade-terms', icon: FileText },
      { name: '付款方式', href: '/admin/payment-methods', icon: CreditCard },
    ],
  },
  {
    label: '系统设置',
    icon: Settings,
    items: [
      { name: '系统仪表板', href: '/admin', icon: LayoutDashboard },
      { name: '用户管理', href: '/admin/users', icon: Users },
      { name: '系统日志', href: '/admin/logs', icon: ScrollText },
      { name: '邮箱管理', href: '/admin/settings', icon: MailCheck },
    ],
  },
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
    pathname === href || (href !== '/admin' && pathname.startsWith(href));

  // 判断分组是否有激活项
  const isGroupActive = (items: NavItem[]) =>
    items.some((item) => isItemActive(item.href));

  // 加载中或无权限时显示空白
  if (isLoading || !isAuthenticated || !isAdmin) {
    return <PageLoading />;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-muted/40">
        {/* 侧边栏 */}
        <aside className={`fixed inset-y-0 left-0 bg-slate-950 border-r border-slate-800 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
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
              {navigation.map((entry) => {
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
            className="absolute -right-3 top-20 z-40 flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        </aside>

        {/* 主内容区域 */}
        <div className={`transition-all duration-300 ${collapsed ? 'pl-16' : 'pl-64'}`}>
          {/* 顶部栏 */}
          <header className="sticky top-0 z-30 bg-background border-b">
            <div className="flex items-center justify-between h-14 px-6">
              <div className="text-lg font-semibold">
                管理后台
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  {user?.name}
                </span>
                <Badge variant="secondary">管理员</Badge>
                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground">
                  <LogOut className="h-4 w-4 mr-1" />
                  退出
                </Button>
              </div>
            </div>
          </header>

          {/* 页面内容 */}
          <main className="p-6">
            {children}
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
