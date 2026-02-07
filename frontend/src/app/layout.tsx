// src/app/layout.tsx
// 根布局
//
// 功能说明：
// 1. 设置全局字体和样式
// 2. 包裹 AuthProvider 提供认证上下文
// 3. 包裹 ConfirmProvider 提供全局确认对话框
// 4. 包裹 Toaster 提供全局 Toast 通知
// 5. 设置页面元数据

import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { ConfirmProvider } from "@/components/ConfirmProvider";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Concord AI - 管理后台",
  description: "Concord AI 系统管理后台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <AuthProvider>
          <ConfirmProvider>
            {children}
          </ConfirmProvider>
        </AuthProvider>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
