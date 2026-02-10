// src/app/admin/trade-terms/page.tsx
// 贸易术语（Incoterms）页面（只读）
//
// 功能说明：
// 1. Incoterms 列表展示（表格 + 可展开详情）
// 2. 版本筛选 Tab（全部 / 2020 / 历史）
// 3. 搜索
// 4. 系统预置数据，无增删改操作

'use client';

import { useState, useEffect, useCallback } from 'react';
import { tradeTermsApi, TradeTerm, TradeTermListResponse } from '@/lib/api';
import { ChevronDown, Ship, Truck } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { SearchFilterBar } from '@/components/DataTable/SearchFilterBar';
import { DataTableShell } from '@/components/DataTable/DataTableShell';
import { ErrorAlert } from '@/components/ErrorAlert';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';

// 版本筛选选项
const VERSION_TABS = [
  { label: '全部', value: '' },
  { label: 'Incoterms 2020', value: '2020' },
  { label: '历史版本', value: 'history' },
] as const;

const PAGE_SIZE = 50;

// 运输方式显示
function TransportBadge({ mode }: { mode: string }) {
  if (mode === 'sea') {
    return (
      <Badge variant="outline" className="text-xs gap-1">
        <Ship className="h-3 w-3" />
        海运
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="text-xs gap-1">
      <Truck className="h-3 w-3" />
      任何
    </Badge>
  );
}

export default function TradeTermsPage() {
  const [terms, setTerms] = useState<TradeTerm[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [versionTab, setVersionTab] = useState('');
  const [page, setPage] = useState(1);

  // 展开的行
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // ==================== 数据加载 ====================

  const loadTerms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof tradeTermsApi.list>[0] = {
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
      };

      if (versionTab === '2020') {
        params.version = '2020';
      } else if (versionTab === 'history') {
        params.is_current = false;
      }

      const resp: TradeTermListResponse = await tradeTermsApi.list(params);
      setTerms(resp.items);
      setTotal(resp.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, versionTab]);

  useEffect(() => {
    loadTerms();
  }, [loadTerms]);

  // 搜索/筛选变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, versionTab]);

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

  // ==================== 分页 ====================

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 版本筛选 Tab */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex gap-1 bg-muted p-1 rounded-lg">
          {VERSION_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setVersionTab(tab.value)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                versionTab === tab.value
                  ? 'bg-background text-foreground shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="ml-auto text-sm text-muted-foreground">
          共 {total} 个术语
        </div>
      </div>

      {/* 搜索栏 */}
      <SearchFilterBar
        searchPlaceholder="搜索术语代码或名称..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
      />

      {/* 错误信息 */}
      {error && <ErrorAlert message={error} onRetry={loadTerms} />}

      {/* 数据表格 */}
      <DataTableShell
        loading={loading}
        itemCount={terms.length}
        columns={8}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle={debouncedSearch ? '未找到匹配的贸易术语' : '暂无数据'}
      >
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]"></TableHead>
            <TableHead className="w-[80px]">代码</TableHead>
            <TableHead>中文名称</TableHead>
            <TableHead>英文全称</TableHead>
            <TableHead className="text-center w-[100px]">版本</TableHead>
            <TableHead className="text-center w-[100px]">运输方式</TableHead>
            <TableHead>风险转移点</TableHead>
            <TableHead className="text-center w-[80px]">状态</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {terms.map((term) => {
            const isExpanded = expandedIds.has(term.id);
            return (
              <>
                <TableRow
                  key={term.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => toggleExpand(term.id)}
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
                      {term.code}
                    </Badge>
                  </TableCell>
                  {/* 中文名 */}
                  <TableCell className="text-sm font-medium">
                    {term.name_zh}
                  </TableCell>
                  {/* 英文全称 */}
                  <TableCell className="text-sm text-muted-foreground">
                    {term.name_en}
                  </TableCell>
                  {/* 版本 */}
                  <TableCell className="text-center">
                    <span className="text-xs text-muted-foreground">{term.version}</span>
                  </TableCell>
                  {/* 运输方式 */}
                  <TableCell className="text-center">
                    <TransportBadge mode={term.transport_mode} />
                  </TableCell>
                  {/* 风险转移点 */}
                  <TableCell className="text-sm text-muted-foreground max-w-[300px] truncate">
                    {term.risk_transfer || '-'}
                  </TableCell>
                  {/* 状态 */}
                  <TableCell className="text-center">
                    {term.is_current ? (
                      <Badge className="text-xs bg-green-100 text-green-800 hover:bg-green-100">
                        当前
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs">
                        历史
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
                {/* 展开详情 */}
                {isExpanded && (
                  <TableRow key={`${term.id}-detail`}>
                    <TableCell colSpan={8} className="bg-muted/30 px-8 py-4">
                      <div className="space-y-3 text-sm">
                        {term.description_zh && (
                          <div>
                            <span className="font-medium text-foreground">中文说明：</span>
                            <p className="mt-1 text-muted-foreground leading-relaxed">
                              {term.description_zh}
                            </p>
                          </div>
                        )}
                        {term.description_en && (
                          <div>
                            <span className="font-medium text-foreground">English Description:</span>
                            <p className="mt-1 text-muted-foreground leading-relaxed">
                              {term.description_en}
                            </p>
                          </div>
                        )}
                        {term.risk_transfer && (
                          <div>
                            <span className="font-medium text-foreground">风险转移点：</span>
                            <p className="mt-1 text-muted-foreground">
                              {term.risk_transfer}
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
      </DataTableShell>
    </div>
  );
}
