// src/components/ChatBox/ChatSidebar.tsx
// 会话列表侧边栏组件
//
// 功能说明：
// 1. 显示会话列表
// 2. 创建新会话
// 3. 切换会话
// 4. 删除会话

'use client';

import { ChatSession } from '@/lib/api';

interface ChatSidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  loading?: boolean;
}

export function ChatSidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  loading = false,
}: ChatSidebarProps) {
  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* 标题和新建按钮 */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onCreateSession}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>新对话</span>
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto" />
            <p className="mt-2 text-sm">加载中...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <p className="text-sm">暂无会话</p>
            <p className="text-xs mt-1">点击上方按钮开始新对话</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full px-4 py-3 text-left hover:bg-gray-100 transition-colors group ${
                    currentSessionId === session.id
                      ? 'bg-blue-50 border-l-4 border-blue-600'
                      : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium truncate ${
                          currentSessionId === session.id
                            ? 'text-blue-600'
                            : 'text-gray-900'
                        }`}
                      >
                        {session.title || '新对话'}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(session.updated_at).toLocaleDateString('zh-CN', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>

                    {/* 删除按钮 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('确定删除此会话吗？')) {
                          onDeleteSession(session.id);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 transition-all"
                      title="删除会话"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 底部信息 */}
      <div className="p-4 border-t border-gray-200 text-center">
        <p className="text-xs text-gray-400">
          {sessions.length} 个会话
        </p>
      </div>
    </div>
  );
}

export default ChatSidebar;
