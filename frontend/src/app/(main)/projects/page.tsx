'use client';

// 项目管理独立页面（兼容旧路由）

import { ProjectsPanel } from './ProjectsPanel';
import { FolderKanban } from 'lucide-react';

export default function ProjectsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FolderKanban className="h-6 w-6" /> 项目管理
        </h1>
        <p className="text-sm text-muted-foreground mt-1">管理项目、任务和进度</p>
      </div>
      <ProjectsPanel />
    </div>
  );
}
