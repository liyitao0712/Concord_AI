// components/PageHeader.tsx
// 统一页面标题组件
//
// 功能说明：
// 统一所有管理页面的标题区域样式（标题 + 描述 + 操作按钮）。

import type { ReactNode } from 'react';

interface PageHeaderProps {
  title?: string;
  description?: string;
  /** 右侧操作区域（如新增按钮） */
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        {title && <h1 className="text-2xl font-semibold">{title}</h1>}
        {description && (
          <p className={`text-sm text-muted-foreground${title ? ' mt-1' : ''}`}>{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
