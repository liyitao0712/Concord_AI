// components/FormSection.tsx
// 表单分区组件
//
// 功能说明：
// 统一表单中的分区标题 + 可折叠内容，
// 替代 customers 页面的内联 FormSection 和其他页面的 div + h4 + Separator 手搓。

'use client';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import { ChevronDown } from 'lucide-react';

interface FormSectionProps {
  title: string;
  /** 是否默认展开 */
  defaultOpen?: boolean;
  /** 是否可折叠（false 时始终展开，不显示折叠图标） */
  collapsible?: boolean;
  children: React.ReactNode;
}

export function FormSection({
  title,
  defaultOpen = true,
  collapsible = true,
  children,
}: FormSectionProps) {
  if (!collapsible) {
    return (
      <div>
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
        </div>
        <Separator className="mt-2 mb-3" />
        {children}
      </div>
    );
  }

  return (
    <Collapsible defaultOpen={defaultOpen}>
      <CollapsibleTrigger asChild>
        <button type="button" className="w-full group text-left">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-foreground">{title}</h4>
            <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
          </div>
          <Separator className="mt-2" />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-3">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
