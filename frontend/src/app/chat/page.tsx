// src/app/chat/page.tsx
// 聊天页面
//
// 功能说明：
// 1. 全屏聊天界面
// 2. 支持会话管理
// 3. SSE 流式对话

'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { ChatBox } from '@/components/ChatBox';

export default function ChatPage() {
  const { user } = useAuth();
  const router = useRouter();

  return (
    <div className="h-screen flex flex-col">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push('/admin')}
              className="text-gray-500 hover:text-gray-700"
              title="返回管理后台"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-900">
              AI 对话
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">
              {user?.name || user?.email}
            </span>
            <button
              onClick={() => router.push('/admin')}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              管理后台
            </button>
          </div>
        </div>
      </header>

      {/* 聊天区域 */}
      <main className="flex-1 overflow-hidden p-4">
        <ChatBox showSidebar={true} />
      </main>
    </div>
  );
}
