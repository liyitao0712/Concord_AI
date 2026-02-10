// components/DataTable/DataTableShell.tsx
// 数据表格容器
//
// 功能说明：
// 组合 Card + Table + Loading + Empty + Pagination，
// 消除每个列表页面重复的表格包装逻辑。

'use client';

import { Card } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Pagination } from './Pagination';
import { EmptyState } from './EmptyState';
import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface DataTableShellProps {
  /** 数据是否加载中 */
  loading: boolean;
  /** 当前页数据条数 */
  itemCount: number;
  /** 表头列数（用于 loading/empty 状态的 colSpan） */
  columns: number;
  /** 分页参数 */
  total: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  /** 空状态配置 */
  emptyIcon?: LucideIcon;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  /** 表格内容（TableHeader + TableBody） */
  children: ReactNode;
}

export function DataTableShell({
  loading,
  itemCount,
  columns,
  total,
  page,
  totalPages,
  onPageChange,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  emptyAction,
  children,
}: DataTableShellProps) {
  return (
    <Card className="py-0 overflow-hidden">
      {loading ? (
        <Table>
          <TableBody>
            <TableRow>
              <TableCell colSpan={columns} className="h-48">
                <div className="flex justify-center">
                  <LoadingSpinner text="加载中..." />
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      ) : itemCount === 0 ? (
        <EmptyState
          icon={emptyIcon}
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
        />
      ) : (
        <>
          <Table>{children}</Table>
          <Pagination
            page={page}
            totalPages={totalPages}
            total={total}
            onPageChange={onPageChange}
          />
        </>
      )}
    </Card>
  );
}
