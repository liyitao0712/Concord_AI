// components/FormDialog.tsx
// 统一表单弹窗组件
//
// 功能说明：
// 封装 Dialog + DialogContent + DialogHeader，
// 统一弹窗尺寸、滚动行为和标题区域。

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { DIALOG_SIZES, type DialogSize } from '@/lib/design-tokens';

interface FormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  /** 弹窗尺寸: sm / md / lg / xl */
  size?: DialogSize;
  children: React.ReactNode;
}

export function FormDialog({
  open,
  onOpenChange,
  title,
  description,
  size = 'md',
  children,
}: FormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={`max-h-[90vh] overflow-y-auto ${DIALOG_SIZES[size]}`}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
