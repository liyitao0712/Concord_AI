// src/components/LoadingSpinner.tsx
// 加载动画组件
//
// 功能说明：
// 1. 显示加载动画
// 2. 支持不同尺寸
// 3. 支持加载文字

'use client';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullScreen?: boolean;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export function LoadingSpinner({
  size = 'md',
  text,
  fullScreen = false,
}: LoadingSpinnerProps) {
  const spinner = (
    <div className="flex flex-col items-center justify-center">
      <div
        className={`${sizeClasses[size]} border-2 border-gray-200 border-t-blue-600 rounded-full animate-spin`}
      />
      {text && <p className="mt-2 text-sm text-gray-500">{text}</p>}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white bg-opacity-75 z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
}

// 页面级加载组件
export function PageLoading({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center h-64">
      <LoadingSpinner size="lg" text={text} />
    </div>
  );
}

// 按钮内加载组件
export function ButtonSpinner() {
  return (
    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
  );
}

export default LoadingSpinner;
