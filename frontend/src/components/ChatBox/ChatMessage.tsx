// src/components/ChatBox/ChatMessage.tsx
// 消息气泡组件
//
// 功能说明：
// 1. 显示用户和 AI 消息
// 2. 支持流式显示时的光标效果
// 3. 支持复制内容

'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Copy, Check } from 'lucide-react';

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
        <Badge variant="secondary" className="font-normal">
          {content}
        </Badge>
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
            ? 'bg-primary text-primary-foreground rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl'
            : 'bg-muted rounded-tl-2xl rounded-tr-2xl rounded-br-2xl'
        } px-4 py-3 relative`}
      >
        {/* 消息内容 */}
        <div className="whitespace-pre-wrap break-words">
          {content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>

        {/* 时间戳和操作 */}
        <div
          className={`flex items-center mt-1 text-xs ${
            isUser ? 'text-primary-foreground/60' : 'text-muted-foreground'
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

          {!isStreaming && content && (
            <Button
              variant="ghost"
              size="icon"
              className={`ml-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity ${
                isUser ? 'hover:bg-primary-foreground/10' : ''
              }`}
              onClick={handleCopy}
              title="复制"
            >
              {copied ? (
                <Check className="h-3 w-3" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
