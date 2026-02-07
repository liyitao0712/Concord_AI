// src/app/chat/layout.tsx
// 聊天页面布局
//
// 功能说明：
// 1. 全屏聊天布局
// 2. 认证检查

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { PageLoading } from '@/components/LoadingSpinner';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/40">
        <PageLoading />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-muted/40">
      {children}
    </div>
  );
}
