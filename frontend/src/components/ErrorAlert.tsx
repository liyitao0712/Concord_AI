// components/ErrorAlert.tsx
// 错误提示组件
//
// 功能说明：
// 统一列表/表格的错误状态展示，支持重试按钮。

import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  return (
    <div className="p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
        <span className="text-sm">{message}</span>
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRetry}
            className="ml-auto text-destructive hover:text-destructive"
          >
            重试
          </Button>
        )}
      </div>
    </div>
  );
}
