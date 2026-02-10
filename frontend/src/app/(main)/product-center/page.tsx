// src/app/admin/product-center/page.tsx
// 产品管理
//
// 功能说明：
// 顶部 Tab 导航切换：品类管理、产品管理

'use client';

import dynamic from 'next/dynamic';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PageLoading } from '@/components/LoadingSpinner';
import { FolderTree, Package } from 'lucide-react';

const CategoriesPanel = dynamic(
  () => import('@/app/(main)/categories/page'),
  { loading: () => <PageLoading /> }
);
const ProductsPanel = dynamic(
  () => import('@/app/(main)/products/page'),
  { loading: () => <PageLoading /> }
);

export default function ProductCenterPage() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="categories">
        <TabsList variant="line">
          <TabsTrigger value="categories" className="gap-1.5">
            <FolderTree className="h-4 w-4" />
            品类管理
          </TabsTrigger>
          <TabsTrigger value="products" className="gap-1.5">
            <Package className="h-4 w-4" />
            产品管理
          </TabsTrigger>
        </TabsList>

        <TabsContent value="categories" className="mt-4">
          <CategoriesPanel />
        </TabsContent>
        <TabsContent value="products" className="mt-4">
          <ProductsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
