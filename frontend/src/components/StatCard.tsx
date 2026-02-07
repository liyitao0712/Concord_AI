// src/components/StatCard.tsx
// 统计卡片组件
//
// 功能说明：
// 1. 显示统计数据
// 2. 支持 Lucide 图标和颜色定制
// 3. 支持趋势显示（可选）

'use client';

import { type LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  color: string;
  trend?: {
    value: number;
    isUp: boolean;
  };
  description?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  color,
  trend,
  description,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center">
          <div className={`flex-shrink-0 p-3 rounded-lg ${color}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div className="ml-4 flex-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <div className="flex items-baseline">
              <p className="text-2xl font-semibold">{value}</p>
              {trend && (
                <span
                  className={`ml-2 text-sm font-medium ${
                    trend.isUp ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {trend.isUp ? '\u2191' : '\u2193'} {Math.abs(trend.value)}%
                </span>
              )}
            </div>
            {description && (
              <p className="mt-1 text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default StatCard;
