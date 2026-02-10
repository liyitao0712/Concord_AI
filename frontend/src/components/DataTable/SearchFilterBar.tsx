// components/DataTable/SearchFilterBar.tsx
// 搜索筛选栏组件
//
// 功能说明：
// 统一搜索输入框 + 筛选下拉（使用 shadcn Select 替代原生 select）的布局。

'use client';

import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import { Search } from 'lucide-react';
import type { ReactNode } from 'react';

export interface FilterConfig {
  key: string;
  placeholder: string;
  options: Array<{ value: string; label: string }>;
}

interface SearchFilterBarProps {
  searchPlaceholder?: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  filters?: FilterConfig[];
  filterValues?: Record<string, string>;
  onFilterChange?: (key: string, value: string) => void;
  /** 右侧额外操作区域 */
  actions?: ReactNode;
  /** 是否用 Card 包裹（默认 true） */
  wrapped?: boolean;
}

// Radix Select 不支持空字符串 value，用哨兵值表示"全部"
const ALL_VALUE = '__all__';

export function SearchFilterBar({
  searchPlaceholder = '搜索...',
  searchValue,
  onSearchChange,
  filters,
  filterValues = {},
  onFilterChange,
  actions,
  wrapped = true,
}: SearchFilterBarProps) {
  const content = (
    <div className="flex flex-col md:flex-row gap-3 md:gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder={searchPlaceholder}
          className="pl-9"
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      {filters && filters.length > 0 && (
        <div className="flex gap-3">
          {filters.map((filter) => {
            const currentValue = filterValues[filter.key] || '';
            return (
              <Select
                key={filter.key}
                value={currentValue || ALL_VALUE}
                onValueChange={(val) =>
                  onFilterChange?.(filter.key, val === ALL_VALUE ? '' : val)
                }
              >
                <SelectTrigger className="w-auto min-w-[120px]">
                  <SelectValue placeholder={filter.placeholder} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>{filter.placeholder}</SelectItem>
                  {filter.options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            );
          })}
        </div>
      )}
      {actions}
    </div>
  );

  if (!wrapped) return content;

  return <Card className="p-4 mb-4">{content}</Card>;
}
