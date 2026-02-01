// src/app/page.tsx
// 首页 - 自动重定向
//
// 功能说明：
// 1. 已登录用户 → 重定向到管理后台
// 2. 未登录用户 → 重定向到登录页
//
// 这个页面不显示任何内容，只负责判断登录状态并重定向

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function Home() {
  // 获取路由对象，用于页面跳转
  const router = useRouter();

  // 获取认证状态
  // user: 当前登录的用户信息，未登录时为 null
  // isLoading: 是否正在检查登录状态
  const { user, isLoading } = useAuth();

  // 当组件加载或登录状态变化时，执行重定向
  useEffect(() => {
    // 如果正在检查登录状态，不做任何操作
    // 等待检查完成后再决定跳转
    if (isLoading) {
      return;
    }

    // 根据登录状态重定向
    if (user) {
      // 已登录：跳转到管理后台
      router.replace('/admin');
    } else {
      // 未登录：跳转到登录页
      router.replace('/login');
    }
  }, [user, isLoading, router]);

  // 显示加载状态
  // 在检查登录状态时显示，防止页面闪烁
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {/* 加载动画 */}
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>

        {/* 提示文字 */}
        <p className="text-gray-500">
          {isLoading ? '正在检查登录状态...' : '正在跳转...'}
        </p>
      </div>
    </div>
  );
}
