// src/contexts/AuthContext.tsx
// 认证上下文
//
// 功能说明：
// 1. 管理用户登录状态
// 2. 提供登录/登出方法
// 3. 在应用中共享用户信息

'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, getCurrentUser, login as apiLogin, logout as apiLogout, getAccessToken, LoginRequest } from '@/lib/api';
import { hasPermission, hasAnyPermission } from '@/lib/permissions';

// ==================== 类型定义 ====================

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
  hasPermission: (resource: string, action: string) => boolean;
  hasAnyPermission: (checks: Array<{ resource: string; action: string }>) => boolean;
  login: (data: LoginRequest) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

// ==================== Context 创建 ====================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ==================== Provider 组件 ====================

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 刷新用户信息
  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    const response = await getCurrentUser();
    if (response.data) {
      setUser(response.data);
    } else {
      setUser(null);
    }
    setIsLoading(false);
  }, []);

  // 初始化时获取用户信息
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // 监听 token 过期事件（由 api.ts 在刷新失败时触发）
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
    };
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  // 登录
  const login = async (data: LoginRequest) => {
    const response = await apiLogin(data);
    if (response.data) {
      await refreshUser();
      return { success: true };
    }
    return { success: false, error: response.error };
  };

  // 登出
  const logout = () => {
    apiLogout();
    setUser(null);
  };

  // 计算属性
  const isAuthenticated = !!user;
  const isSuperAdmin = user?.is_super_admin === true;
  const isAdmin = isAuthenticated && (isSuperAdmin || user?.role === 'admin' || (user?.permissions?.length ?? 0) > 0);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        isAdmin,
        isSuperAdmin,
        hasPermission: (resource: string, action: string) => hasPermission(user, resource, action),
        hasAnyPermission: (checks: Array<{ resource: string; action: string }>) => hasAnyPermission(user, checks),
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ==================== Hook ====================

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
