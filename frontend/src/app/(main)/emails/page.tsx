'use client';

// 邮件记录独立页面（兼容旧路由）

import { EmailsPanel } from './EmailsPanel';

export default function EmailsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">邮件记录</h1>
        <p className="mt-1 text-sm text-muted-foreground">查看系统接收到的邮件</p>
      </div>
      <EmailsPanel />
    </div>
  );
}
