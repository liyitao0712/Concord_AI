// src/app/admin/countries/page.tsx
// 国家数据库页面（只读）
//
// 功能说明：
// 1. 国家/地区数据展示（表格）
// 2. 搜索（按名称、ISO 代码、区号、货币）
// 3. 分页浏览
// 4. 系统预置数据，无增删改操作

'use client';

import { useState, useEffect, useCallback } from 'react';
import { countriesApi, Country, CountryListResponse } from '@/lib/api';
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

export default function CountriesPage() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和分页
  const { searchInput, setSearchInput, debouncedSearch } = useDebouncedSearch();
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // ==================== 数据加载 ====================

  const loadCountries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp: CountryListResponse = await countriesApi.list({
        page,
        page_size: pageSize,
        search: debouncedSearch || undefined,
      });
      setCountries(resp.items);
      setTotal(resp.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch]);

  useEffect(() => {
    loadCountries();
  }, [loadCountries]);

  // 搜索变化时重置页码
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // ==================== 分页 ====================

  const totalPages = Math.ceil(total / pageSize);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 搜索栏 */}
      <SearchFilterBar
        searchPlaceholder="搜索国家名称、ISO 代码、区号、货币..."
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        wrapped={false}
      />

      {/* 错误信息 */}
      {error && <ErrorAlert message={error} onRetry={loadCountries} />}

      {/* 数据表格 */}
      <DataTableShell
        loading={loading}
        itemCount={countries.length}
        columns={8}
        total={total}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        emptyTitle="暂无数据"
      >
        <TableHeader>
          <TableRow>
            <TableHead className="w-[60px]">ISO</TableHead>
            <TableHead>中文简称</TableHead>
            <TableHead>英文简称</TableHead>
            <TableHead className="hidden xl:table-cell">中文全称</TableHead>
            <TableHead className="hidden xl:table-cell">英文全称</TableHead>
            <TableHead className="text-center w-[80px]">Alpha-3</TableHead>
            <TableHead className="text-center w-[80px]">区号</TableHead>
            <TableHead className="text-center">货币</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {countries.map((country) => (
            <TableRow key={country.id}>
              {/* ISO Alpha-2 */}
              <TableCell>
                <Badge variant="outline" className="font-mono text-xs">
                  {country.iso_code_2}
                </Badge>
              </TableCell>
              {/* 中文简称 */}
              <TableCell className="text-sm font-medium">
                {country.name_zh}
              </TableCell>
              {/* 英文简称 */}
              <TableCell className="text-sm text-muted-foreground">
                {country.name_en}
              </TableCell>
              {/* 中文全称 */}
              <TableCell className="text-sm text-muted-foreground hidden xl:table-cell">
                {country.full_name_zh || '-'}
              </TableCell>
              {/* 英文全称 */}
              <TableCell className="text-sm text-muted-foreground hidden xl:table-cell max-w-[300px] truncate">
                {country.full_name_en || '-'}
              </TableCell>
              {/* Alpha-3 */}
              <TableCell className="text-center">
                <span className="text-xs font-mono text-muted-foreground">
                  {country.iso_code_3 || '-'}
                </span>
              </TableCell>
              {/* 区号 */}
              <TableCell className="text-center text-sm text-muted-foreground">
                {country.phone_code || '-'}
              </TableCell>
              {/* 货币 */}
              <TableCell className="text-center">
                {country.currency_code ? (
                  <span className="text-xs" title={`${country.currency_name_zh} / ${country.currency_name_en}`}>
                    <Badge variant="secondary" className="font-mono text-xs">
                      {country.currency_code}
                    </Badge>
                    <span className="ml-1.5 text-muted-foreground hidden lg:inline">
                      {country.currency_name_zh}
                    </span>
                  </span>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </DataTableShell>
    </div>
  );
}
