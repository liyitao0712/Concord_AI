// src/app/admin/page.tsx
// 管理后台仪表盘
//
// 功能说明：
// 1. 显示系统统计数据
// 2. 快捷操作入口
// 3. 系统概览

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getStats, StatsResponse } from '@/lib/api';
import { StatCard } from '@/components/StatCard';
import { PageLoading } from '@/components/LoadingSpinner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, CheckCircle, Crown, TrendingUp, UserPlus, RefreshCw } from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    const response = await getStats();
    if (response.data) {
      setStats(response.data);
    } else {
      setError(response.error || '加载统计数据失败');
    }
    setLoading(false);
  };

  if (loading) {
    return <PageLoading />;
  }

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-md">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold">仪表盘</h1>
        <p className="mt-1 text-sm text-muted-foreground">系统概览和统计数据</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="总用户数"
          value={stats?.total_users ?? 0}
          icon={Users}
          color="bg-blue-100 text-blue-600"
        />
        <StatCard
          title="活跃用户"
          value={stats?.active_users ?? 0}
          icon={CheckCircle}
          color="bg-green-100 text-green-600"
        />
        <StatCard
          title="管理员"
          value={stats?.admin_users ?? 0}
          icon={Crown}
          color="bg-purple-100 text-purple-600"
        />
        <StatCard
          title="今日新增"
          value={stats?.today_new_users ?? 0}
          icon={TrendingUp}
          color="bg-amber-100 text-amber-600"
        />
      </div>

      {/* 快捷操作 */}
      <Card>
        <CardHeader>
          <CardTitle>快捷操作</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/admin/users">
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Users className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium">用户管理</p>
                    <p className="text-sm text-muted-foreground">查看和管理用户</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Link href="/admin/users?action=create">
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <UserPlus className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium">创建用户</p>
                    <p className="text-sm text-muted-foreground">添加新用户账户</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer" onClick={loadStats}>
              <CardContent className="flex items-center gap-3 p-4">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <RefreshCw className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="font-medium">刷新数据</p>
                  <p className="text-sm text-muted-foreground">重新加载统计</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* 系统信息 */}
      <Card>
        <CardHeader>
          <CardTitle>系统信息</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">系统版本</dt>
              <dd className="mt-1 text-sm">v0.1.0</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">API 地址</dt>
              <dd className="mt-1 text-sm">
                {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
