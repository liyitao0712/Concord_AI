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

// 统计卡片组件
function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: number | string;
  icon: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 p-3 rounded-full ${color}`}>
          <span className="text-2xl">{icon}</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">仪表盘</h1>
        <p className="mt-1 text-sm text-gray-500">系统概览和统计数据</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="总用户数"
          value={stats?.total_users ?? 0}
          icon="👥"
          color="bg-blue-100"
        />
        <StatCard
          title="活跃用户"
          value={stats?.active_users ?? 0}
          icon="✅"
          color="bg-green-100"
        />
        <StatCard
          title="管理员"
          value={stats?.admin_users ?? 0}
          icon="👑"
          color="bg-purple-100"
        />
        <StatCard
          title="今日新增"
          value={stats?.today_new_users ?? 0}
          icon="📈"
          color="bg-yellow-100"
        />
      </div>

      {/* 快捷操作 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">快捷操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/admin/users"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl mr-3">👥</span>
            <div>
              <p className="font-medium text-gray-900">用户管理</p>
              <p className="text-sm text-gray-500">查看和管理用户</p>
            </div>
          </Link>
          <Link
            href="/admin/users?action=create"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl mr-3">➕</span>
            <div>
              <p className="font-medium text-gray-900">创建用户</p>
              <p className="text-sm text-gray-500">添加新用户账户</p>
            </div>
          </Link>
          <button
            onClick={loadStats}
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
          >
            <span className="text-2xl mr-3">🔄</span>
            <div>
              <p className="font-medium text-gray-900">刷新数据</p>
              <p className="text-sm text-gray-500">重新加载统计</p>
            </div>
          </button>
        </div>
      </div>

      {/* 系统信息 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">系统信息</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">系统版本</dt>
            <dd className="mt-1 text-sm text-gray-900">v0.1.0</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">API 地址</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
