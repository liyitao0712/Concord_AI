// src/app/admin/storage/page.tsx
// 仓储管理
//
// 功能说明：
// 顶部 Tab 导航切换：仓库管理、入仓单、出仓单

'use client';

import dynamic from 'next/dynamic';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PageLoading } from '@/components/LoadingSpinner';
import { Warehouse, PackagePlus, PackageMinus } from 'lucide-react';

const WarehousesPanel = dynamic(
  () => import('@/app/admin/warehouses/page'),
  { loading: () => <PageLoading /> }
);
const InboundOrdersPanel = dynamic(
  () => import('@/app/admin/inbound-orders/page'),
  { loading: () => <PageLoading /> }
);
const OutboundOrdersPanel = dynamic(
  () => import('@/app/admin/outbound-orders/page'),
  { loading: () => <PageLoading /> }
);

export default function StoragePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">仓储管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">仓库、入仓与出仓</p>
      </div>

      <Tabs defaultValue="warehouses">
        <TabsList variant="line">
          <TabsTrigger value="warehouses" className="gap-1.5">
            <Warehouse className="h-4 w-4" />
            仓库管理
          </TabsTrigger>
          <TabsTrigger value="inbound" className="gap-1.5">
            <PackagePlus className="h-4 w-4" />
            入仓单
          </TabsTrigger>
          <TabsTrigger value="outbound" className="gap-1.5">
            <PackageMinus className="h-4 w-4" />
            出仓单
          </TabsTrigger>
        </TabsList>

        <TabsContent value="warehouses" className="mt-4">
          <WarehousesPanel />
        </TabsContent>
        <TabsContent value="inbound" className="mt-4">
          <InboundOrdersPanel />
        </TabsContent>
        <TabsContent value="outbound" className="mt-4">
          <OutboundOrdersPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
