// hooks/usePagination.ts
// 分页状态 Hook
//
// 功能说明：
// 封装分页相关状态（当前页、总数、总页数），避免各页面重复声明。

import { useState, useCallback } from 'react';
import { DEFAULT_PAGE_SIZE } from '@/lib/design-tokens';

export function usePagination(pageSize = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const resetPage = useCallback(() => setPage(1), []);

  return { page, setPage, total, setTotal, totalPages, pageSize, resetPage };
}
