// src/components/StatCard.tsx
// 统计卡片组件
//
// 功能说明：
// 1. 显示统计数据
// 2. 支持图标和颜色定制
// 3. 支持趋势显示（可选）

'use client';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: string;
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
  icon,
  color,
  trend,
  description,
}: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 p-3 rounded-full ${color}`}>
          <span className="text-2xl">{icon}</span>
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold text-gray-900">{value}</p>
            {trend && (
              <span
                className={`ml-2 text-sm font-medium ${
                  trend.isUp ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {trend.isUp ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
            )}
          </div>
          {description && (
            <p className="mt-1 text-xs text-gray-400">{description}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatCard;
