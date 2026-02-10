// components/StatusBadge.tsx
// 统一状态徽章组件
//
// 功能说明：
// 根据状态 key 查找颜色和标签并渲染 Badge，
// 替代各页面自定义的 CUSTOMER_LEVELS、PRODUCT_STATUSES 等颜色映射。

import { Badge } from '@/components/ui/badge';
import { STATUS_COLORS, type StatusColorKey } from '@/lib/design-tokens';

export interface StatusConfig {
  label: string;
  color: StatusColorKey;
}

interface StatusBadgeProps {
  /** 状态值（如 'active', 'vip'） */
  status: string;
  /** 状态值 -> 标签 + 颜色 key 的映射表 */
  statusMap: Record<string, StatusConfig>;
  /** 未匹配时的 fallback 标签 */
  fallbackLabel?: string;
  className?: string;
}

export function StatusBadge({
  status,
  statusMap,
  fallbackLabel,
  className,
}: StatusBadgeProps) {
  const config = statusMap[status];
  if (!config) {
    if (fallbackLabel) {
      return (
        <Badge variant="secondary" className={className}>
          {fallbackLabel}
        </Badge>
      );
    }
    return null;
  }

  const colorClass = STATUS_COLORS[config.color] || '';

  return (
    <Badge className={`border-0 ${colorClass} ${className || ''}`}>
      {config.label}
    </Badge>
  );
}
