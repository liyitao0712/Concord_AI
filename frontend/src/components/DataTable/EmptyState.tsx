// components/DataTable/EmptyState.tsx
// 空状态组件
//
// 功能说明：
// 统一列表/表格的空状态展示，支持图标、文字和操作按钮。

import { Inbox, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  /** 可选的操作按钮（如"新增"） */
  action?: ReactNode;
}

export function EmptyState({
  icon: Icon = Inbox,
  title = '暂无数据',
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="py-16 text-center">
      <Icon className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
      <p className="text-muted-foreground">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
