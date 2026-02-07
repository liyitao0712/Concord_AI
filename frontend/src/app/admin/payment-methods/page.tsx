// src/app/admin/payment-methods/page.tsx
// 付款方式页面（只读）
//
// 功能说明：
// 1. 付款方式列表展示（表格 + 可展开详情）
// 2. 分类筛选 Tab（全部 / 汇款 / 信用证 / 托收 / 其他）
// 3. 搜索
// 4. 系统预置数据，无增删改操作

'use client';

import { useState, useEffect, useCallback } from 'react';
import { paymentMethodsApi, PaymentMethod, PaymentMethodListResponse } from '@/lib/api';
import { Search, ChevronDown, Star } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { LoadingSpinner } from '@/components/LoadingSpinner';

// 分类筛选选项
const CATEGORY_TABS = [
  { label: '全部', value: '' },
  { label: '汇款类', value: 'remittance' },
  { label: '信用证类', value: 'credit' },
  { label: '托收类', value: 'collection' },
  { label: '其他', value: 'other' },
] as const;

// 分类中文映射
const CATEGORY_LABELS: Record<string, string> = {
  remittance: '汇款',
  credit: '信用证',
  collection: '托收',
  other: '其他',
};

// 分类颜色映射
function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    remittance: 'bg-blue-100 text-blue-800',
    credit: 'bg-purple-100 text-purple-800',
    collection: 'bg-amber-100 text-amber-800',
    other: 'bg-gray-100 text-gray-800',
  };
  return (
    <Badge className={`text-xs ${colors[category] || colors.other} hover:${colors[category] || colors.other}`}>
      {CATEGORY_LABELS[category] || category}
    </Badge>
  );
}

export default function PaymentMethodsPage() {
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [categoryTab, setCategoryTab] = useState('');

  // 展开的行
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // ==================== 数据加载 ====================

  const loadMethods = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof paymentMethodsApi.list>[0] = {
        page: 1,
        page_size: 50,
        search: search || undefined,
        category: categoryTab || undefined,
      };

      const resp: PaymentMethodListResponse = await paymentMethodsApi.list(params);
      setMethods(resp.items);
      setTotal(resp.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [search, categoryTab]);

  useEffect(() => {
    loadMethods();
  }, [loadMethods]);

  // ==================== 搜索处理 ====================

  const handleSearch = () => {
    setSearch(searchInput);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearch('');
  };

  // ==================== 展开/折叠 ====================

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-2xl font-bold">付款方式</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          国际贸易常用付款方式，包含汇款、信用证、托收及其他方式
        </p>
      </div>

      {/* 分类筛选 Tab + 搜索 */}
      <div className="flex items-center gap-4 flex-wrap">
        {/* 分类 Tab */}
        <div className="flex gap-1 bg-muted p-1 rounded-lg">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setCategoryTab(tab.value)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                categoryTab === tab.value
                  ? 'bg-background text-foreground shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 搜索 */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索代码或名称..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-9"
          />
        </div>
        <Button onClick={handleSearch} variant="secondary" size="sm">
          搜索
        </Button>
        {search && (
          <Button onClick={handleClearSearch} variant="ghost" size="sm">
            清除
          </Button>
        )}
        <div className="ml-auto text-sm text-muted-foreground">
          共 {total} 种付款方式
        </div>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {/* 数据表格 */}
      <Card className="py-0 overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : methods.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            {search ? '未找到匹配的付款方式' : '暂无数据'}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                <TableHead className="w-[100px]">代码</TableHead>
                <TableHead>中文名称</TableHead>
                <TableHead>英文全称</TableHead>
                <TableHead className="text-center w-[100px]">分类</TableHead>
                <TableHead className="text-center w-[80px]">常用</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {methods.map((method) => {
                const isExpanded = expandedIds.has(method.id);
                return (
                  <>
                    <TableRow
                      key={method.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleExpand(method.id)}
                    >
                      {/* 展开图标 */}
                      <TableCell className="w-[50px]">
                        <ChevronDown
                          className={`h-4 w-4 text-muted-foreground transition-transform ${
                            isExpanded ? 'rotate-180' : ''
                          }`}
                        />
                      </TableCell>
                      {/* 代码 */}
                      <TableCell>
                        <Badge variant="outline" className="font-mono text-sm font-bold">
                          {method.code}
                        </Badge>
                      </TableCell>
                      {/* 中文名 */}
                      <TableCell className="text-sm font-medium">
                        {method.name_zh}
                      </TableCell>
                      {/* 英文全称 */}
                      <TableCell className="text-sm text-muted-foreground">
                        {method.name_en}
                      </TableCell>
                      {/* 分类 */}
                      <TableCell className="text-center">
                        <CategoryBadge category={method.category} />
                      </TableCell>
                      {/* 常用 */}
                      <TableCell className="text-center">
                        {method.is_common && (
                          <Star className="h-4 w-4 text-amber-500 fill-amber-500 mx-auto" />
                        )}
                      </TableCell>
                    </TableRow>
                    {/* 展开详情 */}
                    {isExpanded && (
                      <TableRow key={`${method.id}-detail`}>
                        <TableCell colSpan={6} className="bg-muted/30 px-8 py-4">
                          <div className="space-y-3 text-sm">
                            {method.description_zh && (
                              <div>
                                <span className="font-medium text-foreground">中文说明：</span>
                                <p className="mt-1 text-muted-foreground leading-relaxed">
                                  {method.description_zh}
                                </p>
                              </div>
                            )}
                            {method.description_en && (
                              <div>
                                <span className="font-medium text-foreground">English Description:</span>
                                <p className="mt-1 text-muted-foreground leading-relaxed">
                                  {method.description_en}
                                </p>
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
