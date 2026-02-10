// src/app/admin/procurement/page.tsx
// 采购管理
//
// 功能说明：
// 顶部 Tab 导航切换：供应商管理、供应商询价、供应商报价、采购合同

'use client';

import dynamic from 'next/dynamic';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PageLoading } from '@/components/LoadingSpinner';
import { Factory, FileInput, FileCheck, ShoppingCart } from 'lucide-react';

const SuppliersPanel = dynamic(
  () => import('@/app/(main)/suppliers/page'),
  { loading: () => <PageLoading /> }
);
const SupplierRfqsPanel = dynamic(
  () => import('@/app/(main)/supplier-rfqs/page'),
  { loading: () => <PageLoading /> }
);
const SupplierQuotationsPanel = dynamic(
  () => import('@/app/(main)/supplier-quotations/page'),
  { loading: () => <PageLoading /> }
);
const PurchaseContractsPanel = dynamic(
  () => import('@/app/(main)/purchase-contracts/page'),
  { loading: () => <PageLoading /> }
);

export default function ProcurementPage() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="suppliers">
        <TabsList variant="line">
          <TabsTrigger value="suppliers" className="gap-1.5">
            <Factory className="h-4 w-4" />
            供应商管理
          </TabsTrigger>
          <TabsTrigger value="supplier-rfqs" className="gap-1.5">
            <FileInput className="h-4 w-4" />
            供应商询价
          </TabsTrigger>
          <TabsTrigger value="supplier-quotations" className="gap-1.5">
            <FileCheck className="h-4 w-4" />
            供应商报价
          </TabsTrigger>
          <TabsTrigger value="purchase-contracts" className="gap-1.5">
            <ShoppingCart className="h-4 w-4" />
            采购合同
          </TabsTrigger>
        </TabsList>

        <TabsContent value="suppliers" className="mt-4">
          <SuppliersPanel />
        </TabsContent>
        <TabsContent value="supplier-rfqs" className="mt-4">
          <SupplierRfqsPanel />
        </TabsContent>
        <TabsContent value="supplier-quotations" className="mt-4">
          <SupplierQuotationsPanel />
        </TabsContent>
        <TabsContent value="purchase-contracts" className="mt-4">
          <PurchaseContractsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
