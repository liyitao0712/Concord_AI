// components/FormFooter.tsx
// 统一表单底部操作栏
//
// 功能说明：
// 统一弹窗表单的取消/提交按钮样式和布局。

import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface FormFooterProps {
  onCancel: () => void;
  submitText?: string;
  cancelText?: string;
  loading?: boolean;
  disabled?: boolean;
  /** 设为 submit 时作为表单提交按钮 */
  type?: 'button' | 'submit';
  onSubmit?: () => void;
}

export function FormFooter({
  onCancel,
  onSubmit,
  submitText = '保存',
  cancelText = '取消',
  loading = false,
  disabled = false,
  type = 'submit',
}: FormFooterProps) {
  return (
    <div className="flex justify-end gap-3 pt-4">
      <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
        {cancelText}
      </Button>
      <Button
        type={type}
        onClick={type === 'button' ? onSubmit : undefined}
        disabled={loading || disabled}
      >
        {loading && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
        {loading ? '保存中...' : submitText}
      </Button>
    </div>
  );
}
