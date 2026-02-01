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

// ==================== 类型定义 ====================

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
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
  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        isAdmin,
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
