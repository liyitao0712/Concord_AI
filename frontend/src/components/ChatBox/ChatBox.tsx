// src/components/ChatBox/ChatBox.tsx
// 聊天主组件
//
// 功能说明：
// 1. 整合会话列表、消息显示、输入框
// 2. 管理聊天状态
// 3. 处理 SSE 流式响应

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { chatApi, ChatSession, ChatMessage as ChatMessageType } from '@/lib/api';
import { useSSE } from './hooks/useSSE';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';

interface ChatBoxProps {
  showSidebar?: boolean;
  defaultSessionId?: string;
}

export function ChatBox({ showSidebar = true, defaultSessionId }: ChatBoxProps) {
  // 会话状态
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    defaultSessionId || null
  );
  const [sessionsLoading, setSessionsLoading] = useState(true);

  // 消息状态
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // 流式响应状态
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // SSE Hook
  const { sendMessage, isStreaming, abort } = useSSE({
    onToken: (token) => {
      setStreamingContent((prev) => prev + token);
    },
    onDone: ({ sessionId, messageId }) => {
      // 流式结束，将内容添加到消息列表
      setMessages((prev) => [
        ...prev,
        {
          id: messageId,
          session_id: sessionId,
          role: 'assistant',
          content: streamingContent,
          tool_calls: null,
          tool_results: null,
          status: 'completed',
          model: null,
          tokens_used: null,
          external_message_id: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setStreamingContent('');

      // 如果是新会话，更新会话 ID 并刷新列表
      if (sessionId !== currentSessionId) {
        setCurrentSessionId(sessionId);
        loadSessions();
      }
    },
    onError: (error) => {
      console.error('SSE 错误:', error);
      setStreamingContent('');
      // 添加错误消息
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          session_id: currentSessionId || '',
          role: 'system',
          content: `错误: ${error}`,
          tool_calls: null,
          tool_results: null,
          status: 'error',
          model: null,
          tokens_used: null,
          external_message_id: null,
          created_at: new Date().toISOString(),
        },
      ]);
    },
  });

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    try {
      const response = await chatApi.getSessions({ page_size: 50 });
      setSessions(response.sessions);
    } catch (error) {
      console.error('加载会话列表失败:', error);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  // 加载消息历史
  const loadMessages = useCallback(async (sessionId: string) => {
    setMessagesLoading(true);
    try {
      const response = await chatApi.getMessages(sessionId, 100);
      setMessages(response.messages);
    } catch (error) {
      console.error('加载消息历史失败:', error);
      setMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 切换会话时加载消息
  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, loadMessages]);

  // 消息更新时滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  // 创建新会话
  const handleCreateSession = useCallback(async () => {
    // 清空当前会话，让后端自动创建
    setCurrentSessionId(null);
    setMessages([]);
    setStreamingContent('');
  }, []);

  // 选择会话
  const handleSelectSession = useCallback((sessionId: string) => {
    if (isStreaming) {
      abort();
    }
    setCurrentSessionId(sessionId);
    setStreamingContent('');
  }, [isStreaming, abort]);

  // 删除会话
  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await chatApi.deleteSession(sessionId);
        // 从列表中移除
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        // 如果删除的是当前会话，清空
        if (sessionId === currentSessionId) {
          setCurrentSessionId(null);
          setMessages([]);
        }
      } catch (error) {
        console.error('删除会话失败:', error);
        alert('删除失败');
      }
    },
    [currentSessionId]
  );

  // 发送消息
  const handleSendMessage = useCallback(
    async (content: string) => {
      // 先添加用户消息到列表
      const userMessage: ChatMessageType = {
        id: `temp-${Date.now()}`,
        session_id: currentSessionId || '',
        role: 'user',
        content,
        tool_calls: null,
        tool_results: null,
        status: 'completed',
        model: null,
        tokens_used: null,
        external_message_id: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // 重置流式内容
      setStreamingContent('');

      // 发送消息
      const newSessionId = await sendMessage(currentSessionId, content);

      // 如果是新会话，更新会话 ID
      if (newSessionId && newSessionId !== currentSessionId) {
        setCurrentSessionId(newSessionId);
        loadSessions();
      }
    },
    [currentSessionId, sendMessage, loadSessions]
  );

  return (
    <div className="flex h-full bg-white rounded-lg shadow-lg overflow-hidden">
      {/* 侧边栏 */}
      {showSidebar && (
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
          loading={sessionsLoading}
        />
      )}

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          {messagesLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto" />
                <p className="mt-2 text-sm text-gray-500">加载中...</p>
              </div>
            </div>
          ) : messages.length === 0 && !streamingContent ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">💬</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900">开始对话</h3>
                <p className="mt-1 text-sm text-gray-500">
                  在下方输入框中输入消息开始聊天
                </p>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  role={message.role}
                  content={message.content}
                  timestamp={message.created_at}
                />
              ))}
              {/* 流式响应中的消息 */}
              {streamingContent && (
                <ChatMessage
                  role="assistant"
                  content={streamingContent}
                  isStreaming={true}
                />
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* 输入区域 */}
        <ChatInput
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder={isStreaming ? '正在响应中...' : '输入消息...'}
        />
      </div>
    </div>
  );
}

export default ChatBox;
