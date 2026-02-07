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
import { Search } from 'lucide-react';
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

export default function CountriesPage() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和分页
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
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
        search: search || undefined,
      });
      setCountries(resp.items);
      setTotal(resp.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    loadCountries();
  }, [loadCountries]);

  // ==================== 搜索处理 ====================

  const handleSearch = () => {
    setPage(1);
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
    setPage(1);
  };

  // ==================== 分页 ====================

  const totalPages = Math.ceil(total / pageSize);

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-2xl font-bold">国家数据库</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          系统预置的国家/地区基础数据，包含 ISO 标准代码、国际区号和货币信息
        </p>
      </div>

      {/* 搜索栏 */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索国家名称、ISO 代码、区号、货币..."
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
          共 {total} 个国家/地区
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
        ) : countries.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            {search ? '未找到匹配的国家/地区' : '暂无数据'}
          </div>
        ) : (
          <Table>
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
          </Table>
        )}
      </Card>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            第 {page} / {totalPages} 页
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page >= totalPages}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
