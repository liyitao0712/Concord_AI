// src/app/layout.tsx
// 根布局
//
// 功能说明：
// 1. 设置全局字体和样式
// 2. 包裹 AuthProvider 提供认证上下文
// 3. 设置页面元数据

import type { Metadata } from "next";
// import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

// 暂时禁用 Google Fonts，使用系统字体
// const geistSans = Geist({
//   variable: "--font-geist-sans",
//   subsets: ["latin"],
// });
//
// const geistMono = Geist_Mono({
//   variable: "--font-geist-mono",
//   subsets: ["latin"],
// });

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
      <body
        className="antialiased"
      >
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
