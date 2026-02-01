// src/components/ChatBox/ChatMessage.tsx
// 消息气泡组件
//
// 功能说明：
// 1. 显示用户和 AI 消息
// 2. 支持流式显示时的光标效果
// 3. 支持复制内容

'use client';

import { useState } from 'react';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  timestamp?: string;
}

export function ChatMessage({
  role,
  content,
  isStreaming = false,
  timestamp,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const isUser = role === 'user';
  const isSystem = role === 'system';

  // 复制内容
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  // 系统消息样式
  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <span className="px-3 py-1 text-xs text-gray-500 bg-gray-100 rounded-full">
          {content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 group`}
    >
      <div
        className={`max-w-[80%] ${
          isUser
            ? 'bg-blue-600 text-white rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl'
            : 'bg-gray-100 text-gray-900 rounded-tl-2xl rounded-tr-2xl rounded-br-2xl'
        } px-4 py-3 relative`}
      >
        {/* 消息内容 */}
        <div className="whitespace-pre-wrap break-words">
          {content}
          {/* 流式光标 */}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>

        {/* 时间戳和操作 */}
        <div
          className={`flex items-center mt-1 text-xs ${
            isUser ? 'text-blue-200' : 'text-gray-400'
          }`}
        >
          {timestamp && (
            <span>
              {new Date(timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}

          {/* 复制按钮（悬停显示） */}
          {!isStreaming && content && (
            <button
              onClick={handleCopy}
              className={`ml-2 opacity-0 group-hover:opacity-100 transition-opacity ${
                isUser ? 'hover:text-white' : 'hover:text-gray-600'
              }`}
              title="复制"
            >
              {copied ? '已复制' : '复制'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
