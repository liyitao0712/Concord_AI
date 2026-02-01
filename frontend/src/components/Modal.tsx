// src/components/Modal.tsx
// 通用模态框组件
//
// 功能说明：
// 1. 可复用的模态框容器
// 2. 支持点击背景关闭
// 3. 支持 ESC 键关闭
// 4. 支持不同尺寸

'use client';

import { useEffect, useCallback } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
};

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
}: ModalProps) {
  // ESC 键关闭
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // 防止背景滚动
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
        {/* 背景遮罩 */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* 模态框内容 */}
        <div
          className={`relative inline-block bg-white rounded-lg shadow-xl transform transition-all ${sizeClasses[size]} w-full p-6 text-left align-middle`}
        >
          {/* 标题栏 */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <span className="sr-only">关闭</span>
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* 内容 */}
          {children}
        </div>
      </div>
    </div>
  );
}

export default Modal;
