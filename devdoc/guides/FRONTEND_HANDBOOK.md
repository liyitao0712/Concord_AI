# Concord AI - 前端开发手册

> Next.js 14 前端结构与开发指南
> 拆分自: MANUAL.md §14

---

## 项目结构

```
frontend/src/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx          # 根布局（全局 Provider）
│   ├── page.tsx            # 首页（自动重定向）
│   ├── login/
│   │   └── page.tsx        # 登录页
│   └── admin/
│       ├── layout.tsx      # 管理后台布局（侧边栏+顶栏）
│       ├── page.tsx        # 仪表盘
│       └── users/
│           └── page.tsx    # 用户管理
├── contexts/
│   └── AuthContext.tsx     # 认证上下文（登录状态管理）
└── lib/
    └── api.ts              # API 工具库（封装 fetch）
```

---

## 认证上下文

```tsx
// contexts/AuthContext.tsx

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 检查 Token 并获取用户信息
    const token = localStorage.getItem('access_token');
    if (token) {
      getCurrentUser().then(setUser).finally(() => setLoading(false));
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await api.login({ email, password });
    localStorage.setItem('access_token', response.access_token);
    const user = await getCurrentUser();
    setUser(user);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

---

## API 工具库

```typescript
// lib/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }

  return response.json();
}

// 认证 API
export const login = (data: LoginRequest) =>
  request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const getCurrentUser = () =>
  request<User>('/api/auth/me');

// 管理员 API
export const getStats = () =>
  request<StatsResponse>('/admin/stats');

export const getUsers = (params?: { page?: number; search?: string }) =>
  request<UserListResponse>(`/admin/users?${new URLSearchParams(params)}`);
```

---

## 页面保护

```tsx
// app/admin/layout.tsx

export default function AdminLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
    if (!loading && user && user.role !== 'admin') {
      router.replace('/');  // 非管理员不能访问
    }
  }, [user, loading]);

  if (loading) return <Loading />;
  if (!user || user.role !== 'admin') return null;

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

---

*拆分自 MANUAL.md | 最后更新: 2026-02-01*
