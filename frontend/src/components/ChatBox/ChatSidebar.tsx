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
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Plus, Trash2 } from 'lucide-react';

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
  const confirm = useConfirm();

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    const confirmed = await confirm({
      title: '删除会话',
      description: '确定删除此会话吗？删除后无法恢复。',
      variant: 'destructive',
      confirmText: '删除',
    });
    if (confirmed) {
      onDeleteSession(sessionId);
    }
  };

  return (
    <div className="w-64 bg-muted/30 border-r flex flex-col h-full">
      {/* 标题和新建按钮 */}
      <div className="p-4 border-b">
        <Button onClick={onCreateSession} className="w-full">
          <Plus className="h-4 w-4 mr-2" />
          新对话
        </Button>
      </div>

      {/* 会话列表 */}
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="p-4">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            <p className="text-sm">暂无会话</p>
            <p className="text-xs mt-1">点击上方按钮开始新对话</p>
          </div>
        ) : (
          <ul className="divide-y">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full px-4 py-3 text-left hover:bg-muted/50 transition-colors group ${
                    currentSessionId === session.id
                      ? 'bg-primary/5 border-l-2 border-primary'
                      : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium truncate ${
                          currentSessionId === session.id
                            ? 'text-primary'
                            : ''
                        }`}
                      >
                        {session.title || '新对话'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
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
                      onClick={(e) => handleDelete(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-destructive transition-all"
                      title="删除会话"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>

      {/* 底部信息 */}
      <div className="p-4 border-t text-center">
        <p className="text-xs text-muted-foreground">
          {sessions.length} 个会话
        </p>
      </div>
    </div>
  );
}

export default ChatSidebar;
