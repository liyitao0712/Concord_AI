// src/components/ChatBox/ChatInput.tsx
// 聊天输入框组件
//
// 功能说明：
// 1. 多行输入框，自动调整高度
// 2. Enter 发送，Shift+Enter 换行
// 3. 发送按钮禁用状态

'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';

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
      // 重置高度
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
    <div className="flex items-end space-x-2 p-4 border-t border-gray-200 bg-white">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          style={{ maxHeight: '200px' }}
        />
        {/* 字符计数 */}
        {message.length > 0 && (
          <span className="absolute right-3 bottom-3 text-xs text-gray-400">
            {message.length}
          </span>
        )}
      </div>

      {/* 发送按钮 */}
      <button
        onClick={handleSend}
        disabled={!canSend}
        className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
          canSend
            ? 'bg-blue-600 hover:bg-blue-700 text-white'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
        title={disabled ? '正在响应...' : '发送 (Enter)'}
      >
        {disabled ? (
          // 加载动画
          <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        ) : (
          // 发送图标
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
        )}
      </button>
    </div>
  );
}

export default ChatInput;
