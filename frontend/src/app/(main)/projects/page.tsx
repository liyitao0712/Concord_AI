'use client';

// 项目管理独立页面（兼容旧路由）

import { ProjectsPanel } from './ProjectsPanel';
export default function ProjectsPage() {
  return (
    <div className="space-y-4">
      <ProjectsPanel />
    </div>
  );
}
