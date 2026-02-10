// src/app/admin/sales/page.tsx
// 销售管理
//
// 功能说明：
// 顶部 Tab 导航切换：客户管理、客户询价、报价单、销售合同

'use client';

import dynamic from 'next/dynamic';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PageLoading } from '@/components/LoadingSpinner';
import { Building2, FileSearch, FileOutput, Receipt } from 'lucide-react';

const CustomersPanel = dynamic(
  () => import('@/app/(main)/customers/page'),
  { loading: () => <PageLoading /> }
);
const ClientRfqsPanel = dynamic(
  () => import('@/app/(main)/client-rfqs/page'),
  { loading: () => <PageLoading /> }
);
const QuotationsPanel = dynamic(
  () => import('@/app/(main)/quotations/page'),
  { loading: () => <PageLoading /> }
);
const SalesContractsPanel = dynamic(
  () => import('@/app/(main)/sales-contracts/page'),
  { loading: () => <PageLoading /> }
);

export default function SalesPage() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="customers">
        <TabsList variant="line" className="h-auto">
          <TabsTrigger value="customers" className="gap-1.5 text-base px-4 py-2">
            <Building2 className="h-4 w-4" />
            客户管理
          </TabsTrigger>
          <TabsTrigger value="client-rfqs" className="gap-1.5 text-base px-4 py-2">
            <FileSearch className="h-4 w-4" />
            客户询价
          </TabsTrigger>
          <TabsTrigger value="quotations" className="gap-1.5 text-base px-4 py-2">
            <FileOutput className="h-4 w-4" />
            报价单
          </TabsTrigger>
          <TabsTrigger value="sales-contracts" className="gap-1.5 text-base px-4 py-2">
            <Receipt className="h-4 w-4" />
            销售合同
          </TabsTrigger>
        </TabsList>

        <TabsContent value="customers" className="mt-4">
          <CustomersPanel />
        </TabsContent>
        <TabsContent value="client-rfqs" className="mt-4">
          <ClientRfqsPanel />
        </TabsContent>
        <TabsContent value="quotations" className="mt-4">
          <QuotationsPanel />
        </TabsContent>
        <TabsContent value="sales-contracts" className="mt-4">
          <SalesContractsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
