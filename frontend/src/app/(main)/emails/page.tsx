'use client';

// 邮件记录独立页面（兼容旧路由）

import { EmailsPanel } from './EmailsPanel';

export default function EmailsPage() {
  return (
    <div className="space-y-6">
      <EmailsPanel />
    </div>
  );
}
