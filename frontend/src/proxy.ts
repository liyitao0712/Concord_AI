// src/proxy.ts
// 设备检测代理
//
// 功能说明：
// 通过 User-Agent 判断访问设备类型（mobile / desktop），
// 将结果写入 cookie，供服务端组件和客户端 Hook 读取。
//
// Next.js 16 使用 proxy.ts 替代 middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const MOBILE_UA_PATTERNS = [
  /Android/i,
  /webOS/i,
  /iPhone/i,
  /iPad/i,
  /iPod/i,
  /BlackBerry/i,
  /Windows Phone/i,
  /Mobile/i,
];

function isMobileUA(userAgent: string): boolean {
  return MOBILE_UA_PATTERNS.some((pattern) => pattern.test(userAgent));
}

export function proxy(request: NextRequest) {
  const userAgent = request.headers.get('user-agent') || '';
  const deviceType = isMobileUA(userAgent) ? 'mobile' : 'desktop';

  const existing = request.cookies.get('device-type')?.value;

  const response = NextResponse.next();

  // 仅在值变化时更新 cookie
  if (existing !== deviceType) {
    response.cookies.set('device-type', deviceType, {
      path: '/',
      maxAge: 60 * 60 * 24 * 365,
      sameSite: 'lax',
    });
  }

  return response;
}

// 排除静态资源和 API 路由
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*|api).*)'],
};
