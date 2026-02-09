// hooks/usePermission.ts
// 权限检查 Hook
//
// 功能说明：
// 提供 can() 和 canAny() 方法，包装 AuthContext 中的用户权限信息。

import { useAuth } from '@/contexts/AuthContext';
import { hasPermission, hasAnyPermission } from '@/lib/permissions';

export function usePermission() {
  const { user } = useAuth();

  return {
    /** 检查单个权限 */
    can: (resource: string, action: string) =>
      hasPermission(user, resource, action),

    /** 检查多个权限（OR 逻辑，任一满足即可） */
    canAny: (checks: Array<{ resource: string; action: string }>) =>
      hasAnyPermission(user, checks),

    /** 是否超级管理员 */
    isSuperAdmin: user?.is_super_admin === true,

    /** 当前用户 */
    user,
  };
}
