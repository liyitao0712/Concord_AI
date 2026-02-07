// src/components/ChatBox/ChatInput.tsx
// 聊天输入框组件
//
// 功能说明：
// 1. 多行输入框，自动调整高度
// 2. Enter 发送，Shift+Enter 换行
// 3. 发送按钮禁用状态

'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = '输入消息...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  // 处理发送
  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled) {
      onSend(trimmedMessage);
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = message.trim().length > 0 && !disabled;

  return (
    <div className="flex items-end gap-2 p-4 border-t bg-background">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full px-4 py-3 pr-12 border border-input rounded-2xl resize-none bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted disabled:cursor-not-allowed"
          style={{ maxHeight: '200px' }}
        />
        {message.length > 0 && (
          <span className="absolute right-3 bottom-3 text-xs text-muted-foreground">
            {message.length}
          </span>
        )}
      </div>

      <Button
        onClick={handleSend}
        disabled={!canSend}
        size="icon"
        className="flex-shrink-0 h-12 w-12 rounded-full"
        title={disabled ? '正在响应...' : '发送 (Enter)'}
      >
        {disabled ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5" />
        )}
      </Button>
    </div>
  );
}

export default ChatInput;
