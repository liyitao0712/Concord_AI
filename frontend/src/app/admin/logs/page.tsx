// src/app/admin/logs/page.tsx
// 系统日志页面
//
// 功能说明：
// 1. 显示系统日志列表
// 2. 支持按级别筛选
// 3. 支持搜索和刷新
//
// 注：当前为占位实现，后续需要后端 API 支持

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { RefreshCw, Info } from 'lucide-react';

// 模拟日志数据类型
interface LogEntry {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  module: string;
  message: string;
}

// 级别 Badge variant 映射
const levelVariants: Record<string, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  DEBUG: 'secondary',
  INFO: 'default',
  WARNING: 'outline',
  ERROR: 'destructive',
};

// 模拟日志数据
const mockLogs: LogEntry[] = [
  {
    id: '1',
    timestamp: new Date().toISOString(),
    level: 'INFO',
    module: 'app.main',
    message: '应用启动成功',
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 60000).toISOString(),
    level: 'INFO',
    module: 'app.api.chat',
    message: '新的聊天会话已创建',
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    level: 'WARNING',
    module: 'app.workflows.worker',
    message: 'Workflow 执行超时，正在重试',
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 180000).toISOString(),
    level: 'DEBUG',
    module: 'app.llm.gateway',
    message: 'LLM 请求: model=claude-3-5-sonnet, tokens=150',
  },
  {
    id: '5',
    timestamp: new Date(Date.now() - 240000).toISOString(),
    level: 'ERROR',
    module: 'app.adapters.email',
    message: 'IMAP 连接失败: Connection refused',
  },
  {
    id: '6',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    level: 'INFO',
    module: 'app.core.redis',
    message: 'Redis 连接成功',
  },
];

export default function LogsPage() {
  // 日志状态
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // 筛选状态
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // 加载日志（模拟）
  const loadLogs = useCallback(async () => {
    setLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 500));
    setLogs(mockLogs);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  // 过滤日志
  const filteredLogs = logs.filter((log) => {
    if (levelFilter && log.level !== levelFilter) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        log.message.toLowerCase().includes(query) ||
        log.module.toLowerCase().includes(query)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">系统日志</h1>
          <p className="mt-1 text-sm text-muted-foreground">查看系统运行日志</p>
        </div>
        <Button variant="outline" onClick={loadLogs}>
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      {/* 筛选和搜索 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <Input
                type="text"
                placeholder="搜索日志内容或模块..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">全部级别</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* 提示信息 */}
      <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-md text-sm">
        <Info className="h-4 w-4 flex-shrink-0" />
        当前显示的是模拟数据。完整日志功能需要后端 API 支持。
      </div>

      {/* 日志表格 */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>时间</TableHead>
              <TableHead>级别</TableHead>
              <TableHead>模块</TableHead>
              <TableHead>消息</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8">
                  <LoadingSpinner text="加载中..." />
                </TableCell>
              </TableRow>
            ) : filteredLogs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                  暂无日志记录
                </TableCell>
              </TableRow>
            ) : (
              filteredLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString('zh-CN')}
                  </TableCell>
                  <TableCell>
                    <Badge variant={levelVariants[log.level] || 'secondary'}>
                      {log.level}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap font-mono text-muted-foreground">
                    {log.module}
                  </TableCell>
                  <TableCell>
                    <div className="max-w-md truncate" title={log.message}>
                      {log.message}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <div className="border-t px-4 py-3">
          <p className="text-sm text-muted-foreground">
            显示 {filteredLogs.length} 条记录
            {levelFilter && ` (${levelFilter})`}
            {searchQuery && ` (搜索: ${searchQuery})`}
          </p>
        </div>
      </Card>
    </div>
  );
}
