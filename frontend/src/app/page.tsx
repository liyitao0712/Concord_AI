// src/app/page.tsx
// 首页 - 自动重定向
//
// 功能说明：
// 1. 已登录用户 -> 重定向到管理后台
// 2. 未登录用户 -> 重定向到登录页

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export default function Home() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (user) {
      router.replace('/admin');
    } else {
      router.replace('/login');
    }
  }, [user, isLoading, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40">
      <LoadingSpinner
        size="lg"
        text={isLoading ? '正在检查登录状态...' : '正在跳转...'}
      />
    </div>
  );
}
