// src/app/login/page.tsx
// 登录页面
//
// 功能说明：
// 1. 管理员登录表单
// 2. 验证用户身份
// 3. 登录成功后跳转到管理后台

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Loader2 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isAdmin, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 如果已登录且是管理员，跳转到后台
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      if (isAdmin) {
        router.push('/admin');
      } else {
        setError('您不是管理员，无法访问管理后台');
      }
    }
  }, [isLoading, isAuthenticated, isAdmin, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    const result = await login({ email, password });

    if (result.success) {
      // login 后会自动刷新用户信息，useEffect 会处理跳转
    } else {
      setError(result.error || '登录失败');
    }

    setSubmitting(false);
  };

  // 加载中显示
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/40">
        <LoadingSpinner size="lg" text="加载中..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Concord AI</CardTitle>
          <CardDescription>管理后台登录</CardDescription>
        </CardHeader>
        <CardContent>
          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm">
              {error}
            </div>
          )}

          {/* 登录表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="admin@example.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {submitting ? '登录中...' : '登录'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            仅限系统管理员登录
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
