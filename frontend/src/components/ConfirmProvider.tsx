// src/components/ConfirmProvider.tsx
// 全局确认对话框提供者
//
// 功能说明：
// 1. 提供 useConfirm hook 替代原生 confirm()
// 2. 使用 shadcn AlertDialog 显示确认对话框
// 3. 返回 Promise<boolean>，支持 async/await

'use client';

import { createContext, useContext, useState, useCallback, useRef } from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog';

interface ConfirmOptions {
  title?: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'destructive';
}

type ConfirmFn = (options: string | ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

export function useConfirm(): ConfirmFn {
  const confirm = useContext(ConfirmContext);
  if (!confirm) {
    throw new Error('useConfirm 必须在 ConfirmProvider 内使用');
  }
  return confirm;
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({
    title: '确认操作',
    description: '',
    confirmText: '确认',
    cancelText: '取消',
    variant: 'default',
  });
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm: ConfirmFn = useCallback((opts) => {
    const normalized: ConfirmOptions =
      typeof opts === 'string' ? { description: opts } : opts;

    setOptions({
      title: normalized.title || '确认操作',
      description: normalized.description,
      confirmText: normalized.confirmText || '确认',
      cancelText: normalized.cancelText || '取消',
      variant: normalized.variant || 'default',
    });
    setOpen(true);

    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  const handleConfirm = () => {
    setOpen(false);
    resolveRef.current?.(true);
    resolveRef.current = null;
  };

  const handleCancel = () => {
    setOpen(false);
    resolveRef.current?.(false);
    resolveRef.current = null;
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <AlertDialog open={open} onOpenChange={(v) => !v && handleCancel()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{options.title}</AlertDialogTitle>
            <AlertDialogDescription>{options.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancel}>
              {options.cancelText}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              variant={options.variant === 'destructive' ? 'destructive' : 'default'}
            >
              {options.confirmText}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ConfirmContext.Provider>
  );
}
