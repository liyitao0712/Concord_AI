// hooks/useDebouncedSearch.ts
// 搜索防抖 Hook
//
// 功能说明：
// 统一各页面的搜索输入防抖逻辑，避免每次击键都触发 API 请求。

import { useState, useEffect } from 'react';
import { SEARCH_DEBOUNCE_MS } from '@/lib/design-tokens';

export function useDebouncedSearch(delay = SEARCH_DEBOUNCE_MS) {
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), delay);
    return () => clearTimeout(timer);
  }, [searchInput, delay]);

  return { searchInput, setSearchInput, debouncedSearch };
}
