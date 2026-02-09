// components/MobileNav.tsx
// 移动端导航抽屉
//
// 功能说明：
// 汉堡菜单按钮 + Sheet 侧边抽屉，复用桌面端导航配置。
// 点击链接后自动关闭抽屉。

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Menu, ChevronDown } from 'lucide-react';
import type { NavEntry } from '@/lib/navigation';

interface MobileNavProps {
  navigation: NavEntry[];
}

export function MobileNav({ navigation }: MobileNavProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    'AI 设置': true,
    '基础数据': true,
    '系统设置': true,
  });

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const isItemActive = (href: string) =>
    pathname === href || (href !== '/admin' && pathname.startsWith(href));

  const isGroupActive = (items: { href: string }[]) =>
    items.some((item) => isItemActive(item.href));

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px] p-0 bg-slate-950 border-slate-800">
        <SheetHeader className="px-4 py-5 border-b border-slate-800">
          <SheetTitle className="text-xl font-bold text-white">Concord AI</SheetTitle>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-5rem)]">
          <nav className="px-3 py-4 space-y-1">
            {navigation.map((entry) => {
              // 顶级导航项
              if ('topLevel' in entry) {
                const active = isItemActive(entry.href);
                const Icon = entry.icon;
                return (
                  <Link
                    key={entry.name}
                    href={entry.href}
                    onClick={() => setOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                      active
                        ? 'bg-slate-800 text-white'
                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                    }`}
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    {entry.name}
                  </Link>
                );
              }

              // 可折叠分组
              const group = entry;
              const expanded = expandedGroups[group.label] ?? true;
              const groupActive = isGroupActive(group.items);
              const GroupIcon = group.icon;

              return (
                <div key={group.label} className="pt-2">
                  <Separator className="mb-2 bg-slate-800" />
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
                      className={`h-3.5 w-3.5 transition-transform duration-200 ${
                        expanded ? 'rotate-180' : ''
                      }`}
                    />
                  </button>

                  {expanded && (
                    <div className="mt-1 space-y-0.5">
                      {group.items.map((item) => {
                        const active = isItemActive(item.href);
                        const Icon = item.icon;
                        return (
                          <Link
                            key={item.name}
                            href={item.href}
                            onClick={() => setOpen(false)}
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
      </SheetContent>
    </Sheet>
  );
}
