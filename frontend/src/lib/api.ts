// src/lib/api.ts
// API 请求工具
//
// 功能说明：
// 1. 封装 fetch 请求，自动处理 token
// 2. 提供常用的 API 方法
// 3. 处理错误响应

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Token 存储键名
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// ==================== Token 管理 ====================

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ==================== API 请求封装 ====================

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;

  // 默认请求头
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    ...options.headers as Record<string, string>,
  };

  // 如果有 token，添加到请求头
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // 解析响应
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    }

    if (!response.ok) {
      // 如果是 401，清除 token
      if (response.status === 401) {
        clearTokens();
      }

      return {
        error: data?.detail || `请求失败: ${response.status}`,
        status: response.status,
      };
    }

    return {
      data,
      status: response.status,
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : '网络错误',
      status: 0,
    };
  }
}

// ==================== 认证 API ====================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export async function login(data: LoginRequest): Promise<ApiResponse<LoginResponse>> {
  const response = await request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  // 如果登录成功，保存 token
  if (response.data) {
    setTokens(response.data.access_token, response.data.refresh_token);
  }

  return response;
}

export async function getCurrentUser(): Promise<ApiResponse<User>> {
  return request<User>('/api/auth/me');
}

export function logout(): void {
  clearTokens();
}

// ==================== 管理员 API ====================

export interface StatsResponse {
  total_users: number;
  active_users: number;
  admin_users: number;
  today_new_users: number;
}

export interface UserListResponse {
  total: number;
  page: number;
  page_size: number;
  users: User[];
}

export interface CreateUserRequest {
  email: string;
  password: string;
  name: string;
  role: string;
}

export interface UpdateUserRequest {
  email?: string;
  name?: string;
  role?: string;
}

export interface MessageResponse {
  message: string;
}

// 获取系统统计
export async function getStats(): Promise<ApiResponse<StatsResponse>> {
  return request<StatsResponse>('/admin/stats');
}

// 获取用户列表
export async function getUsers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}): Promise<ApiResponse<UserListResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
  if (params?.search) searchParams.set('search', params.search);
  if (params?.role) searchParams.set('role', params.role);
  if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());

  const query = searchParams.toString();
  return request<UserListResponse>(`/admin/users${query ? `?${query}` : ''}`);
}

// 获取单个用户
export async function getUser(userId: string): Promise<ApiResponse<User>> {
  return request<User>(`/admin/users/${userId}`);
}

// 创建用户
export async function createUser(data: CreateUserRequest): Promise<ApiResponse<User>> {
  return request<User>('/admin/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// 更新用户
export async function updateUser(userId: string, data: UpdateUserRequest): Promise<ApiResponse<User>> {
  return request<User>(`/admin/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// 删除用户
export async function deleteUser(userId: string): Promise<ApiResponse<MessageResponse>> {
  return request<MessageResponse>(`/admin/users/${userId}`, {
    method: 'DELETE',
  });
}

// 切换用户状态
export async function toggleUserStatus(userId: string): Promise<ApiResponse<User>> {
  return request<User>(`/admin/users/${userId}/toggle`, {
    method: 'POST',
  });
}

// 重置用户密码
export async function resetUserPassword(userId: string, newPassword: string): Promise<ApiResponse<MessageResponse>> {
  return request<MessageResponse>(`/admin/users/${userId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  });
}

// ==================== 管理员 API 对象 ====================

export const adminApi = {
  getStats,
  getUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  toggleUserStatus,
  resetUserPassword,
};

// ==================== 系统设置 API ====================

export interface EmailConfig {
  smtp_configured: boolean;
  imap_configured: boolean;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  imap_host: string | null;
  imap_port: number | null;
  imap_user: string | null;
}

export interface EmailConfigUpdate {
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  imap_host?: string;
  imap_port?: number;
  imap_user?: string;
  imap_password?: string;
}

export const settingsApi = {
  // 邮件配置
  async getEmailConfig(): Promise<EmailConfig> {
    const response = await request<EmailConfig>('/admin/settings/email');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async updateEmailConfig(data: EmailConfigUpdate): Promise<any> {
    const response = await request('/admin/settings/email', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data;
  },
};


// ==================== 飞书配置 API ====================

export interface FeishuConfig {
  enabled: boolean;
  configured: boolean;
  app_id: string | null;
  app_id_preview: string | null;
  app_secret_configured: boolean;
  encrypt_key_configured: boolean;
  verification_token_configured: boolean;
}

export interface FeishuConfigUpdate {
  enabled?: boolean;
  app_id?: string;
  app_secret?: string;
  encrypt_key?: string;
  verification_token?: string;
}

export interface FeishuTestResult {
  success: boolean;
  message?: string;
  app_id?: string;
  error?: string;
}

export interface FeishuWorkerStatus {
  enabled: boolean;
  configured: boolean;
  worker_running: boolean;
  worker_pid?: number;
  message: string;
}

// ==================== OSS 配置 API ====================

export interface OSSConfig {
  configured: boolean;
  endpoint: string | null;
  bucket: string | null;
  access_key_id_preview: string | null;
  access_key_secret_configured: boolean;
}

export interface OSSConfigUpdate {
  endpoint?: string;
  bucket?: string;
  access_key_id?: string;
  access_key_secret?: string;
}

export interface OSSTestResult {
  success: boolean;
  message?: string;
  bucket?: string;
  endpoint?: string;
  error?: string;
}

export const ossApi = {
  async getConfig(): Promise<OSSConfig> {
    const response = await request<OSSConfig>('/admin/settings/oss');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async updateConfig(data: OSSConfigUpdate): Promise<any> {
    const response = await request('/admin/settings/oss', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data;
  },

  async testConnection(): Promise<OSSTestResult> {
    const response = await request<OSSTestResult>('/admin/settings/oss/test', {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== 飞书配置 API ====================

export const feishuApi = {
  async getConfig(): Promise<FeishuConfig> {
    const response = await request<FeishuConfig>('/admin/settings/feishu');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async updateConfig(data: FeishuConfigUpdate): Promise<any> {
    const response = await request('/admin/settings/feishu', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data;
  },

  async testConnection(): Promise<FeishuTestResult> {
    const response = await request<FeishuTestResult>('/admin/settings/feishu/test', {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async getWorkerStatus(): Promise<FeishuWorkerStatus> {
    const response = await request<FeishuWorkerStatus>('/admin/settings/feishu/status');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== 邮箱账户 API ====================

export interface EmailAccount {
  id: number;
  name: string;
  purpose: string;
  description: string | null;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_use_tls: boolean;
  smtp_configured: boolean;
  imap_host: string | null;
  imap_port: number;
  imap_user: string | null;
  imap_use_ssl: boolean;
  imap_configured: boolean;
  imap_folder: string;
  imap_mark_as_read: boolean;
  imap_sync_days: number | null;
  imap_unseen_only: boolean;
  imap_fetch_limit: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailAccountCreate {
  name: string;
  purpose: string;
  description?: string;
  smtp_host: string;
  smtp_port?: number;
  smtp_user: string;
  smtp_password: string;
  smtp_use_tls?: boolean;
  imap_host?: string;
  imap_port?: number;
  imap_user?: string;
  imap_password?: string;
  imap_use_ssl?: boolean;
  imap_folder?: string;
  imap_mark_as_read?: boolean;
  imap_sync_days?: number;
  imap_unseen_only?: boolean;
  imap_fetch_limit?: number;
  is_default?: boolean;
}

export interface EmailAccountUpdate {
  name?: string;
  purpose?: string;
  description?: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_use_tls?: boolean;
  imap_host?: string;
  imap_port?: number;
  imap_user?: string;
  imap_password?: string;
  imap_use_ssl?: boolean;
  imap_folder?: string;
  imap_mark_as_read?: boolean;
  imap_sync_days?: number;
  imap_unseen_only?: boolean;
  imap_fetch_limit?: number;
  is_active?: boolean;
}

export interface EmailAccountTestResult {
  smtp_success: boolean | null;
  smtp_message: string | null;
  imap_success: boolean | null;
  imap_message: string | null;
}

export const emailAccountsApi = {
  async list(): Promise<{ total: number; items: EmailAccount[] }> {
    const response = await request<{ total: number; items: EmailAccount[] }>('/admin/email-accounts');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async get(id: number): Promise<EmailAccount> {
    const response = await request<EmailAccount>(`/admin/email-accounts/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async create(data: EmailAccountCreate): Promise<EmailAccount> {
    const response = await request<EmailAccount>('/admin/email-accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async update(id: number, data: EmailAccountUpdate): Promise<EmailAccount> {
    const response = await request<EmailAccount>(`/admin/email-accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async delete(id: number): Promise<void> {
    const response = await request(`/admin/email-accounts/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  async setDefault(id: number): Promise<EmailAccount> {
    const response = await request<EmailAccount>(`/admin/email-accounts/${id}/default`, {
      method: 'PUT',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async test(id: number): Promise<EmailAccountTestResult> {
    const response = await request<EmailAccountTestResult>(`/admin/email-accounts/${id}/test`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async fetch(id: number, limit: number = 50): Promise<{
    account_id: number;
    emails_found: number;
    emails_saved: number;
    duration_seconds: number;
  }> {
    const response = await request<{
      account_id: number;
      emails_found: number;
      emails_saved: number;
      duration_seconds: number;
    }>(`/admin/email-accounts/${id}/fetch?limit=${limit}`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== Chat API ====================

export interface ChatSession {
  id: string;
  user_id: string;
  external_user_id: string | null;
  source: string;
  title: string;
  agent_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls: any | null;
  tool_results: any | null;
  status: string;
  model: string | null;
  tokens_used: number | null;
  external_message_id: string | null;
  created_at: string;
}

export interface ChatSessionListResponse {
  total: number;
  page: number;
  page_size: number;
  sessions: ChatSession[];
}

export interface ChatMessageListResponse {
  session_id: string;
  messages: ChatMessage[];
}

export interface CreateSessionRequest {
  title?: string;
  agent_id?: string;
  source?: string;
}

export interface SendMessageRequest {
  session_id: string;
  message: string;
  model?: string;
  temperature?: number;
}

export interface SendMessageResponse {
  session_id: string;
  message_id: string;
  content: string;
  model: string;
  tokens_used: number;
}

// SSE 流式响应类型
export interface SSETokenEvent {
  type: 'token';
  content: string;
}

export interface SSEDoneEvent {
  type: 'done';
  session_id: string;
  message_id: string;
}

export interface SSEErrorEvent {
  type: 'error';
  error: string;
}

export type SSEEvent = SSETokenEvent | SSEDoneEvent | SSEErrorEvent;

export const chatApi = {
  // 创建会话
  async createSession(data?: CreateSessionRequest): Promise<ChatSession> {
    const response = await request<ChatSession>('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取会话列表
  async getSessions(params?: { page?: number; page_size?: number }): Promise<ChatSessionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    const query = searchParams.toString();
    const response = await request<ChatSessionListResponse>(`/api/chat/sessions${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取会话详情
  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await request<ChatSession>(`/api/chat/sessions/${sessionId}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除会话
  async deleteSession(sessionId: string): Promise<void> {
    const response = await request(`/api/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // 获取消息历史
  async getMessages(sessionId: string, limit?: number): Promise<ChatMessageListResponse> {
    const searchParams = new URLSearchParams();
    if (limit) searchParams.set('limit', limit.toString());
    const query = searchParams.toString();
    const response = await request<ChatMessageListResponse>(
      `/api/chat/sessions/${sessionId}/messages${query ? `?${query}` : ''}`
    );
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 非流式发送消息
  async sendMessage(data: SendMessageRequest): Promise<SendMessageResponse> {
    const response = await request<SendMessageResponse>('/api/chat/send', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取流式 API URL（用于 SSE）
  getStreamUrl(): string {
    return `${API_BASE_URL}/api/chat/stream`;
  },

  // 获取 API 基础 URL
  getBaseUrl(): string {
    return API_BASE_URL;
  },
};


// ==================== 邮件记录 API ====================

export interface EmailAttachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  is_inline: boolean;
  is_signature: boolean;
}

export interface EmailListItem {
  id: string;
  sender: string;
  sender_name: string | null;
  subject: string;
  received_at: string;
  is_processed: boolean;
  attachment_count: number;
  email_account_name: string | null;
}

export interface EmailDetail {
  id: string;
  sender: string;
  sender_name: string | null;
  subject: string;
  recipients: string[];
  body_text: string;
  received_at: string;
  is_processed: boolean;
  processed_at: string | null;
  event_id: string | null;
  size_bytes: number;
  oss_key: string;
  email_account_id: number | null;
  email_account_name: string | null;
  attachments: EmailAttachment[];
}

export interface EmailListResponse {
  total: number;
  page: number;
  page_size: number;
  items: EmailListItem[];
}

export const emailsApi = {
  async list(params?: {
    page?: number;
    page_size?: number;
    account_id?: number;
    is_processed?: boolean;
    search?: string;
  }): Promise<EmailListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.account_id) searchParams.set('account_id', params.account_id.toString());
    if (params?.is_processed !== undefined) searchParams.set('is_processed', params.is_processed.toString());
    if (params?.search) searchParams.set('search', params.search);
    const query = searchParams.toString();
    const response = await request<EmailListResponse>(`/admin/emails${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async get(emailId: string): Promise<EmailDetail> {
    const response = await request<EmailDetail>(`/admin/emails/${emailId}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getRawUrl(emailId: string): string {
    return `${API_BASE_URL}/admin/emails/${emailId}/raw`;
  },

  getAttachmentUrl(emailId: string, attachmentId: string): string {
    return `${API_BASE_URL}/admin/emails/${emailId}/attachments/${attachmentId}`;
  },

  // 分析邮件意图
  async analyze(emailId: string): Promise<EmailRouteAnalyzeResult> {
    const response = await request<EmailRouteAnalyzeResult>(`/admin/emails/${emailId}/analyze`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 执行邮件处理
  async execute(emailId: string, data?: { intent?: string; force?: boolean }): Promise<EmailRouteExecuteResult> {
    const response = await request<EmailRouteExecuteResult>(`/admin/emails/${emailId}/execute`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // AI 分析邮件（外贸场景）
  async aiAnalyze(emailId: string, force: boolean = false): Promise<EmailAnalysisResult> {
    const response = await request<EmailAnalysisResult>(`/admin/emails/${emailId}/ai-analyze?force=${force}`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取已保存的分析结果
  async getAnalysis(emailId: string): Promise<EmailAnalysisResult | null> {
    const response = await request<EmailAnalysisResult | null>(`/admin/emails/${emailId}/analysis`);
    if (response.error) throw new Error(response.error);
    return response.data ?? null;
  },

  // 工作类型分析
  async workTypeAnalyze(emailId: string): Promise<WorkTypeAnalyzeResult> {
    const response = await request<WorkTypeAnalyzeResult>(`/admin/emails/${emailId}/work-type-analyze`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// 邮件路由分析结果
export interface EmailRouteAnalyzeResult {
  intent: string;
  intent_label: string;
  confidence: number;
  reasoning: string;
  action: string;
  handler_config: Record<string, unknown>;
  workflow_name: string | null;
  needs_escalation: boolean;
  escalation_reason: string | null;
  new_suggestion: {
    name: string;
    label: string;
    description: string;
    suggested_handler: string;
  } | null;
}

// 邮件路由执行结果
export interface EmailRouteExecuteResult {
  success: boolean;
  message: string;
  intent: string;
  action: string;
  workflow_id: string | null;
  error: string | null;
}

// 工作类型分析结果
export interface WorkTypeAnalyzeResult {
  email_id: string;
  matched_work_type: {
    code: string;
    confidence: number;
    reason: string;
  } | null;
  new_suggestion: {
    should_suggest: boolean;
    suggested_code: string | null;
    suggested_name: string | null;
    suggested_description: string | null;
    suggested_parent_code: string | null;
    suggested_keywords: string[];
    confidence: number;
    reasoning: string | null;
  } | null;
  suggestion_id: string | null;
  llm_model: string | null;
}

// AI 邮件分析结果（外贸场景）
export interface EmailAnalysisResult {
  id: string;
  email_id: string;
  summary: string;
  key_points: string[] | null;
  original_language: string | null;

  // 发件方
  sender_type: string | null;
  sender_company: string | null;
  sender_country: string | null;
  is_new_contact: boolean | null;

  // 意图
  intent: string | null;
  intent_confidence: number | null;
  urgency: string | null;
  sentiment: string | null;

  // 业务信息
  products: Array<{
    name: string;
    specs?: string;
    quantity?: number;
    unit?: string;
    target_price?: number;
  }> | null;
  amounts: Array<{
    value: number;
    currency: string;
    context?: string;
  }> | null;
  trade_terms: {
    incoterm?: string;
    payment_terms?: string;
    destination?: string;
  } | null;
  deadline: string | null;

  // 跟进
  questions: string[] | null;
  action_required: string[] | null;
  suggested_reply: string | null;
  priority: string | null;

  // 元数据
  llm_model: string | null;
  token_used: number | null;
  created_at: string | null;
}


// ==================== Prompt API ====================

export interface PromptItem {
  id: string;
  name: string;
  category: string;
  display_name: string | null;
  content: string;
  variables: Record<string, string> | null;
  description: string | null;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PromptListResponse {
  items: PromptItem[];
  total: number;
}

export interface PromptTestResult {
  rendered: string;
  variables_used: string[];
  missing_variables: string[];
}

export const promptsApi = {
  // 获取 Prompt 列表
  async list(params?: { category?: string; is_active?: boolean }): Promise<PromptListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set('category', params.category);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<PromptListResponse>(`/admin/prompts${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取 Prompt 详情
  async get(name: string): Promise<PromptItem> {
    const response = await request<PromptItem>(`/admin/prompts/${name}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新 Prompt
  async update(name: string, data: {
    content: string;
    display_name?: string;
    description?: string;
    variables?: Record<string, string>;
    is_active?: boolean;
  }): Promise<PromptItem> {
    const response = await request<PromptItem>(`/admin/prompts/${name}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 测试 Prompt 渲染
  async test(name: string, variables: Record<string, string>): Promise<PromptTestResult> {
    const response = await request<PromptTestResult>(`/admin/prompts/${name}/test`, {
      method: 'POST',
      body: JSON.stringify({ variables }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取 Prompt 默认值
  async getDefault(name: string): Promise<{
    name: string;
    content: string;
    variables: Record<string, string>;
    display_name: string | null;
    description: string | null;
  }> {
    const response = await request(`/admin/prompts/${name}/default`);
    if (response.error) throw new Error(response.error);
    return response.data as any;
  },

  // 重置 Prompt 为默认值
  async resetToDefault(name: string): Promise<PromptItem> {
    const response = await request<PromptItem>(`/admin/prompts/${name}/reset`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== LLM 模型配置 API ====================

export interface LLMModelConfig {
  id: string;
  model_id: string;
  provider: string;
  model_name: string;
  api_key_preview: string | null;
  api_endpoint: string | null;
  total_requests: number;
  total_tokens: number;
  last_used_at: string | null;
  is_enabled: boolean;
  is_configured: boolean;
  description: string | null;
  parameters: Record<string, any> | null;
  created_at: string;
  updated_at: string | null;
}

export interface LLMModelListResponse {
  items: LLMModelConfig[];
  total: number;
}

export interface LLMModelCreateRequest {
  model_id: string;  // 如：anthropic/claude-opus-4-5-20251101
  provider: string;  // 如：anthropic, openai, gemini
  model_name: string;  // 如：Claude Opus 4.5
  description?: string;
  api_key?: string;
  api_endpoint?: string;
  parameters?: Record<string, any>;
  is_enabled?: boolean;
}

export interface LLMModelUpdateRequest {
  api_key?: string;
  api_endpoint?: string;
  is_enabled?: boolean;
  parameters?: Record<string, any>;
}

export interface LLMModelTestRequest {
  test_prompt?: string;
}

export interface LLMModelTestResponse {
  success: boolean;
  response?: string;
  error?: string;
  model_used?: string;
  tokens_used?: number;
}

export interface LLMModelUsageStats {
  stats: Array<{
    model_id: string;
    model_name: string;
    provider: string;
    total_requests: number;
    total_tokens: number;
    last_used_at: string | null;
  }>;
  total_requests: number;
  total_tokens: number;
}

export const llmModelsApi = {
  // 获取模型列表
  async list(params?: {
    provider?: string;
    is_enabled?: boolean;
    is_configured?: boolean;
  }): Promise<LLMModelListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.provider) searchParams.set('provider', params.provider);
    if (params?.is_enabled !== undefined) searchParams.set('is_enabled', params.is_enabled.toString());
    if (params?.is_configured !== undefined) searchParams.set('is_configured', params.is_configured.toString());
    const query = searchParams.toString();
    const response = await request<LLMModelListResponse>(`/admin/llm/models${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建新模型
  async create(data: LLMModelCreateRequest): Promise<LLMModelConfig> {
    const response = await request<LLMModelConfig>('/admin/llm/models', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取模型详情
  async get(modelId: string): Promise<LLMModelConfig> {
    const response = await request<LLMModelConfig>(`/admin/llm/models/${encodeURIComponent(modelId)}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新模型配置
  async update(modelId: string, data: LLMModelUpdateRequest): Promise<LLMModelConfig> {
    const response = await request<LLMModelConfig>(`/admin/llm/models/${encodeURIComponent(modelId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除模型
  async delete(modelId: string): Promise<void> {
    const response = await request(`/admin/llm/models/${encodeURIComponent(modelId)}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // 测试模型连接
  async test(modelId: string, data?: LLMModelTestRequest): Promise<LLMModelTestResponse> {
    const response = await request<LLMModelTestResponse>(`/admin/llm/models/${encodeURIComponent(modelId)}/test`, {
      method: 'POST',
      body: JSON.stringify(data || { test_prompt: '你好' }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取使用统计
  async getUsageStats(): Promise<LLMModelUsageStats> {
    const response = await request<LLMModelUsageStats>('/admin/llm/models/stats/usage');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== Agent 配置管理 API ====================

export interface AgentListItem {
  name: string;
  display_name: string;
  description: string;
  prompt_name: string;
  system_prompt_name: string;
  model: string | null;
  tools: string[];
}

export interface AgentConfigResponse {
  agent_name: string;
  model: string | null;
  temperature: number | null;
  max_tokens: number | null;
  enabled: boolean;
}

export interface AgentConfigUpdateRequest {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  enabled?: boolean;
}

export const agentsConfigApi = {
  // 获取所有 Agent 列表
  async list(): Promise<AgentListItem[]> {
    const response = await request<AgentListItem[]>('/api/agents/admin/list');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取 Agent 配置
  async getConfig(agentName: string): Promise<AgentConfigResponse> {
    const response = await request<AgentConfigResponse>(`/api/agents/admin/${encodeURIComponent(agentName)}/config`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新 Agent 配置
  async updateConfig(agentName: string, data: AgentConfigUpdateRequest): Promise<AgentConfigResponse> {
    const response = await request<AgentConfigResponse>(`/api/agents/admin/${encodeURIComponent(agentName)}/config`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// ==================== 工作类型管理 API ====================

export interface WorkType {
  id: string;
  parent_id: string | null;
  code: string;
  name: string;
  description: string;
  level: number;
  path: string;
  examples: string[];
  keywords: string[];
  is_active: boolean;
  is_system: boolean;
  usage_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WorkTypeTreeNode {
  id: string;
  parent_id: string | null;
  code: string;
  name: string;
  description: string;
  level: number;
  is_active: boolean;
  is_system: boolean;
  usage_count: number;
  children: WorkTypeTreeNode[];
}

export interface WorkTypeListResponse {
  items: WorkType[];
  total: number;
}

export interface WorkTypeTreeResponse {
  items: WorkTypeTreeNode[];
  total: number;
}

export interface WorkTypeCreate {
  code: string;
  name: string;
  description: string;
  parent_id?: string;
  examples?: string[];
  keywords?: string[];
  is_active?: boolean;
}

export interface WorkTypeUpdate {
  code?: string;
  name?: string;
  description?: string;
  examples?: string[];
  keywords?: string[];
  is_active?: boolean;
}

export interface WorkTypeSuggestion {
  id: string;
  suggested_code: string;
  suggested_name: string;
  suggested_description: string;
  suggested_parent_id: string | null;
  suggested_parent_code: string | null;
  suggested_level: number;
  suggested_examples: string[];
  suggested_keywords: string[];
  confidence: number;
  reasoning: string | null;
  trigger_email_id: string | null;
  trigger_content: string;
  trigger_source: string;
  status: 'pending' | 'approved' | 'rejected' | 'merged';
  workflow_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_work_type_id: string | null;
  merged_to_id: string | null;
  created_at: string;
}

export interface WorkTypeSuggestionListResponse {
  items: WorkTypeSuggestion[];
  total: number;
}

export const workTypesApi = {
  // 获取工作类型列表
  async list(params?: { is_active?: boolean; level?: number; parent_id?: string }): Promise<WorkTypeListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    if (params?.level !== undefined) searchParams.set('level', params.level.toString());
    if (params?.parent_id) searchParams.set('parent_id', params.parent_id);
    const query = searchParams.toString();
    const response = await request<WorkTypeListResponse>(`/admin/work-types${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取树形结构
  async tree(params?: { is_active?: boolean }): Promise<WorkTypeTreeResponse> {
    const searchParams = new URLSearchParams();
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<WorkTypeTreeResponse>(`/admin/work-types/tree${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取工作类型详情
  async get(id: string): Promise<WorkType> {
    const response = await request<WorkType>(`/admin/work-types/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建工作类型
  async create(data: WorkTypeCreate): Promise<WorkType> {
    const response = await request<WorkType>('/admin/work-types', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新工作类型
  async update(id: string, data: WorkTypeUpdate): Promise<WorkType> {
    const response = await request<WorkType>(`/admin/work-types/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除工作类型
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/work-types/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // 获取建议列表
  async listSuggestions(params?: { status?: string; page?: number; page_size?: number }): Promise<WorkTypeSuggestionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    const query = searchParams.toString();
    const response = await request<WorkTypeSuggestionListResponse>(`/admin/work-type-suggestions${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取建议详情
  async getSuggestion(id: string): Promise<WorkTypeSuggestion> {
    const response = await request<WorkTypeSuggestion>(`/admin/work-type-suggestions/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 批准建议（支持覆盖 AI 建议的字段）
  async approveSuggestion(id: string, data: {
    note?: string;
    code?: string;
    name?: string;
    description?: string;
    parent_id?: string;
    keywords?: string[];
    examples?: string[];
  }): Promise<WorkType> {
    const response = await request<WorkType>(`/admin/work-type-suggestions/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 拒绝建议
  async rejectSuggestion(id: string, note?: string): Promise<void> {
    const response = await request(`/admin/work-type-suggestions/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    if (response.error) throw new Error(response.error);
  },
};


// ==================== 客户管理 ====================

export interface Customer {
  id: string;
  name: string;
  short_name: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  company_size: string | null;
  annual_revenue: string | null;
  customer_level: string;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  payment_terms: string | null;
  shipping_terms: string | null;
  is_active: boolean;
  source: string | null;
  notes: string | null;
  tags: string[];
  contact_count: number;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: string;
  customer_id: string;
  name: string;
  title: string | null;
  department: string | null;
  email: string | null;
  phone: string | null;
  mobile: string | null;
  social_media: Record<string, string>;
  is_primary: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerDetail extends Customer {
  contacts: Contact[];
}

export interface CustomerCreate {
  name: string;
  short_name?: string;
  country?: string;
  region?: string;
  industry?: string;
  company_size?: string;
  annual_revenue?: string;
  customer_level?: string;
  email?: string;
  phone?: string;
  website?: string;
  address?: string;
  payment_terms?: string;
  shipping_terms?: string;
  is_active?: boolean;
  source?: string;
  notes?: string;
  tags?: string[];
}

export interface CustomerUpdate {
  name?: string;
  short_name?: string;
  country?: string;
  region?: string;
  industry?: string;
  company_size?: string;
  annual_revenue?: string;
  customer_level?: string;
  email?: string;
  phone?: string;
  website?: string;
  address?: string;
  payment_terms?: string;
  shipping_terms?: string;
  is_active?: boolean;
  source?: string;
  notes?: string;
  tags?: string[];
}

export interface CustomerListResponse {
  items: Customer[];
  total: number;
}

export interface AILookupResponse {
  short_name: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  company_size: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  tags: string[];
  notes: string | null;
  confidence: number;
  error: string | null;
}

export interface ContactCreate {
  customer_id: string;
  name: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile?: string;
  social_media?: Record<string, string>;
  is_primary?: boolean;
  is_active?: boolean;
  notes?: string;
}

export interface ContactUpdate {
  name?: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile?: string;
  social_media?: Record<string, string>;
  is_primary?: boolean;
  is_active?: boolean;
  notes?: string;
}

export interface ContactListResponse {
  items: Contact[];
  total: number;
}

export const customersApi = {
  // 获取客户列表
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    country?: string;
    customer_level?: string;
    is_active?: boolean;
  }): Promise<CustomerListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.country) searchParams.set('country', params.country);
    if (params?.customer_level) searchParams.set('customer_level', params.customer_level);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<CustomerListResponse>(`/admin/customers${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取客户详情（含联系人）
  async get(id: string): Promise<CustomerDetail> {
    const response = await request<CustomerDetail>(`/admin/customers/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建客户
  async create(data: CustomerCreate): Promise<Customer> {
    const response = await request<Customer>('/admin/customers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新客户
  async update(id: string, data: CustomerUpdate): Promise<Customer> {
    const response = await request<Customer>(`/admin/customers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除客户
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/customers/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // AI 搜索公司信息
  async aiLookup(companyName: string): Promise<AILookupResponse> {
    const response = await request<AILookupResponse>('/admin/customers/ai-lookup', {
      method: 'POST',
      body: JSON.stringify({ company_name: companyName }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

export const contactsApi = {
  // 获取联系人列表
  async list(params?: {
    customer_id?: string;
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
  }): Promise<ContactListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.customer_id) searchParams.set('customer_id', params.customer_id);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<ContactListResponse>(`/admin/contacts${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取联系人详情
  async get(id: string): Promise<Contact> {
    const response = await request<Contact>(`/admin/contacts/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建联系人
  async create(data: ContactCreate): Promise<Contact> {
    const response = await request<Contact>('/admin/contacts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新联系人
  async update(id: string, data: ContactUpdate): Promise<Contact> {
    const response = await request<Contact>(`/admin/contacts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除联系人
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/contacts/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};


// ==================== 客户建议审批 ====================

export interface CustomerSuggestion {
  id: string;
  suggestion_type: string; // "new_customer" | "new_contact"

  // AI 提取的客户信息
  suggested_company_name: string;
  suggested_short_name: string | null;
  suggested_country: string | null;
  suggested_region: string | null;
  suggested_industry: string | null;
  suggested_website: string | null;
  suggested_email_domain: string | null;
  suggested_customer_level: string;
  suggested_tags: string[];

  // AI 提取的联系人信息
  suggested_contact_name: string | null;
  suggested_contact_email: string | null;
  suggested_contact_title: string | null;
  suggested_contact_phone: string | null;
  suggested_contact_department: string | null;

  // AI 分析
  confidence: number;
  reasoning: string | null;
  sender_type: string | null;

  // 触发来源
  trigger_email_id: string | null;
  trigger_content: string;
  trigger_source: string;

  // 查重
  email_domain: string | null;
  matched_customer_id: string | null;

  // 审批状态
  status: string;
  workflow_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_customer_id: string | null;
  created_contact_id: string | null;

  created_at: string;
}

export interface CustomerSuggestionListResponse {
  items: CustomerSuggestion[];
  total: number;
}

export interface CustomerReviewData {
  note?: string;
  company_name?: string;
  short_name?: string;
  country?: string;
  region?: string;
  industry?: string;
  website?: string;
  customer_level?: string;
  tags?: string[];
  contact_name?: string;
  contact_email?: string;
  contact_title?: string;
  contact_phone?: string;
  contact_department?: string;
}

export const customerSuggestionsApi = {
  // 获取客户建议列表
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  }): Promise<CustomerSuggestionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.status) searchParams.set('status', params.status);
    if (params?.search) searchParams.set('search', params.search);
    const query = searchParams.toString();
    const response = await request<CustomerSuggestionListResponse>(
      `/admin/customer-suggestions${query ? `?${query}` : ''}`
    );
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取建议详情
  async get(id: string): Promise<CustomerSuggestion> {
    const response = await request<CustomerSuggestion>(`/admin/customer-suggestions/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 批准建议
  async approve(id: string, data: CustomerReviewData): Promise<{ message: string; customer_id?: string; contact_id?: string }> {
    const response = await request<{ message: string; customer_id?: string; contact_id?: string }>(
      `/admin/customer-suggestions/${id}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 拒绝建议
  async reject(id: string, note?: string): Promise<{ message: string }> {
    const response = await request<{ message: string }>(
      `/admin/customer-suggestions/${id}/reject`,
      {
        method: 'POST',
        body: JSON.stringify({ note }),
      }
    );
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};


// ==================== 供应商管理 ====================

export interface Supplier {
  id: string;
  name: string;
  short_name: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  company_size: string | null;
  main_products: string | null;
  supplier_level: string;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  payment_terms: string | null;
  shipping_terms: string | null;
  is_active: boolean;
  source: string | null;
  notes: string | null;
  tags: string[];
  contact_count: number;
  created_at: string;
  updated_at: string;
}

export interface SupplierContact {
  id: string;
  supplier_id: string;
  name: string;
  title: string | null;
  department: string | null;
  email: string | null;
  phone: string | null;
  mobile: string | null;
  social_media: Record<string, string>;
  is_primary: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierDetail extends Supplier {
  contacts: SupplierContact[];
}

export interface SupplierCreate {
  name: string;
  short_name?: string;
  country?: string;
  region?: string;
  industry?: string;
  company_size?: string;
  main_products?: string;
  supplier_level?: string;
  email?: string;
  phone?: string;
  website?: string;
  address?: string;
  payment_terms?: string;
  shipping_terms?: string;
  is_active?: boolean;
  source?: string;
  notes?: string;
  tags?: string[];
}

export interface SupplierUpdate {
  name?: string;
  short_name?: string;
  country?: string;
  region?: string;
  industry?: string;
  company_size?: string;
  main_products?: string;
  supplier_level?: string;
  email?: string;
  phone?: string;
  website?: string;
  address?: string;
  payment_terms?: string;
  shipping_terms?: string;
  is_active?: boolean;
  source?: string;
  notes?: string;
  tags?: string[];
}

export interface SupplierListResponse {
  items: Supplier[];
  total: number;
}

export interface SupplierContactCreate {
  supplier_id: string;
  name: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile?: string;
  social_media?: Record<string, string>;
  is_primary?: boolean;
  is_active?: boolean;
  notes?: string;
}

export interface SupplierContactUpdate {
  name?: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile?: string;
  social_media?: Record<string, string>;
  is_primary?: boolean;
  is_active?: boolean;
  notes?: string;
}

export interface SupplierContactListResponse {
  items: SupplierContact[];
  total: number;
}

export const suppliersApi = {
  // 获取供应商列表
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    country?: string;
    supplier_level?: string;
    is_active?: boolean;
  }): Promise<SupplierListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.country) searchParams.set('country', params.country);
    if (params?.supplier_level) searchParams.set('supplier_level', params.supplier_level);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<SupplierListResponse>(`/admin/suppliers${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取供应商详情（含联系人）
  async get(id: string): Promise<SupplierDetail> {
    const response = await request<SupplierDetail>(`/admin/suppliers/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建供应商
  async create(data: SupplierCreate): Promise<Supplier> {
    const response = await request<Supplier>('/admin/suppliers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新供应商
  async update(id: string, data: SupplierUpdate): Promise<Supplier> {
    const response = await request<Supplier>(`/admin/suppliers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除供应商
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/suppliers/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};

export const supplierContactsApi = {
  // 获取联系人列表
  async list(params?: {
    supplier_id?: string;
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
  }): Promise<SupplierContactListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.supplier_id) searchParams.set('supplier_id', params.supplier_id);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<SupplierContactListResponse>(`/admin/supplier-contacts${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取联系人详情
  async get(id: string): Promise<SupplierContact> {
    const response = await request<SupplierContact>(`/admin/supplier-contacts/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建联系人
  async create(data: SupplierContactCreate): Promise<SupplierContact> {
    const response = await request<SupplierContact>('/admin/supplier-contacts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新联系人
  async update(id: string, data: SupplierContactUpdate): Promise<SupplierContact> {
    const response = await request<SupplierContact>(`/admin/supplier-contacts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除联系人
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/supplier-contacts/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};


// ==================== 文件上传 ====================

export interface UploadResponse {
  key: string;
  storage_type: string;
  url: string;
}

export const uploadApi = {
  async uploadImage(file: File, directory: string = 'images/general'): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('directory', directory);

    const token = getAccessToken();
    const response = await fetch(`${API_BASE_URL}/admin/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `上传失败: ${response.status}`);
    }

    return response.json();
  },
};


// ==================== 品类管理 ====================

export interface Category {
  id: string;
  code: string;
  name: string;
  name_en: string | null;
  parent_id: string | null;
  parent_name: string | null;
  description: string | null;
  vat_rate: number | null;
  tax_rebate_rate: number | null;
  image_url: string | null;
  product_count: number;
  children_count: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryTreeNode {
  id: string;
  code: string;
  name: string;
  name_en: string | null;
  description: string | null;
  vat_rate: number | null;
  tax_rebate_rate: number | null;
  image_url: string | null;
  product_count: number;
  children: CategoryTreeNode[];
}

export interface CategoryCreate {
  code: string;
  name: string;
  name_en?: string;
  parent_id?: string;
  description?: string;
  vat_rate?: number;
  tax_rebate_rate?: number;
  image_key?: string;
  image_storage_type?: string;
}

export interface CategoryUpdate {
  code?: string;
  name?: string;
  name_en?: string;
  parent_id?: string | null;
  description?: string;
  vat_rate?: number;
  tax_rebate_rate?: number;
  image_key?: string | null;
  image_storage_type?: string | null;
}

export interface CategoryListResponse {
  items: Category[];
  total: number;
}

export interface CategoryTreeResponse {
  items: CategoryTreeNode[];
}

export const categoriesApi = {
  // 获取品类列表（平铺）
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    parent_id?: string;
  }): Promise<CategoryListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.parent_id) searchParams.set('parent_id', params.parent_id);
    const query = searchParams.toString();
    const response = await request<CategoryListResponse>(`/admin/categories${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取品类树形结构
  async tree(params?: { is_active?: boolean }): Promise<CategoryTreeResponse> {
    const searchParams = new URLSearchParams();
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
    const query = searchParams.toString();
    const response = await request<CategoryTreeResponse>(`/admin/categories/tree${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取下一个可用品类编码
  async nextCode(parentId?: string): Promise<{ code: string }> {
    const searchParams = new URLSearchParams();
    if (parentId) searchParams.set('parent_id', parentId);
    const query = searchParams.toString();
    const response = await request<{ code: string }>(`/admin/categories/next-code${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取品类详情
  async get(id: string): Promise<Category> {
    const response = await request<Category>(`/admin/categories/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建品类
  async create(data: CategoryCreate): Promise<Category> {
    const response = await request<Category>('/admin/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新品类
  async update(id: string, data: CategoryUpdate): Promise<Category> {
    const response = await request<Category>(`/admin/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除品类
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/categories/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};


// ==================== 产品管理 ====================

export interface Product {
  id: string;
  category_id: string | null;
  category_name: string | null;
  name: string;
  model_number: string | null;
  specifications: string | null;
  unit: string | null;
  moq: number | null;
  reference_price: number | null;
  currency: string;
  hs_code: string | null;
  origin: string | null;
  material: string | null;
  packaging: string | null;
  images: string[];
  description: string | null;
  tags: string[];
  status: string;
  notes: string | null;
  supplier_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductSupplierInfo {
  id: string;
  product_id: string;
  supplier_id: string;
  supplier_name: string | null;
  supply_price: number | null;
  currency: string;
  moq: number | null;
  lead_time: number | null;
  is_primary: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends Product {
  suppliers: ProductSupplierInfo[];
}

export interface ProductCreate {
  name: string;
  category_id?: string;
  model_number?: string;
  specifications?: string;
  unit?: string;
  moq?: number;
  reference_price?: number;
  currency?: string;
  hs_code?: string;
  origin?: string;
  material?: string;
  packaging?: string;
  images?: string[];
  description?: string;
  tags?: string[];
  status?: string;
  notes?: string;
}

export interface ProductUpdate {
  name?: string;
  category_id?: string | null;
  model_number?: string;
  specifications?: string;
  unit?: string;
  moq?: number;
  reference_price?: number;
  currency?: string;
  hs_code?: string;
  origin?: string;
  material?: string;
  packaging?: string;
  images?: string[];
  description?: string;
  tags?: string[];
  status?: string;
  notes?: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
}

export interface ProductSupplierCreate {
  supplier_id: string;
  supply_price?: number;
  currency?: string;
  moq?: number;
  lead_time?: number;
  is_primary?: boolean;
  notes?: string;
}

export interface ProductSupplierUpdate {
  supply_price?: number;
  currency?: string;
  moq?: number;
  lead_time?: number;
  is_primary?: boolean;
  notes?: string;
}

export const productsApi = {
  // 获取产品列表
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    category_id?: string;
    status?: string;
  }): Promise<ProductListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.category_id) searchParams.set('category_id', params.category_id);
    if (params?.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    const response = await request<ProductListResponse>(`/admin/products${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取产品详情（含供应商）
  async get(id: string): Promise<ProductDetail> {
    const response = await request<ProductDetail>(`/admin/products/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建产品
  async create(data: ProductCreate): Promise<Product> {
    const response = await request<Product>('/admin/products', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新产品
  async update(id: string, data: ProductUpdate): Promise<Product> {
    const response = await request<Product>(`/admin/products/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除产品
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/products/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // 添加供应商关联
  async addSupplier(productId: string, data: ProductSupplierCreate): Promise<ProductSupplierInfo> {
    const response = await request<ProductSupplierInfo>(`/admin/products/${productId}/suppliers`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新供应商关联
  async updateSupplier(productId: string, supplierId: string, data: ProductSupplierUpdate): Promise<ProductSupplierInfo> {
    const response = await request<ProductSupplierInfo>(`/admin/products/${productId}/suppliers/${supplierId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 移除供应商关联
  async removeSupplier(productId: string, supplierId: string): Promise<void> {
    const response = await request(`/admin/products/${productId}/suppliers/${supplierId}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};


// ==================== 国家数据库 ====================

export interface Country {
  id: string;
  name_zh: string;
  name_en: string;
  full_name_zh: string | null;
  full_name_en: string | null;
  iso_code_2: string;
  iso_code_3: string | null;
  numeric_code: string | null;
  phone_code: string | null;
  currency_name_zh: string | null;
  currency_name_en: string | null;
  currency_code: string | null;
  created_at: string | null;
}

export interface CountryListResponse {
  items: Country[];
  total: number;
}

export const countriesApi = {
  // 获取国家列表
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<CountryListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    const query = searchParams.toString();
    const response = await request<CountryListResponse>(`/admin/countries${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取国家详情
  async get(id: string): Promise<Country> {
    const response = await request<Country>(`/admin/countries/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};


// ==================== 贸易术语 ====================

export interface TradeTerm {
  id: string;
  code: string;
  name_en: string;
  name_zh: string;
  version: string;
  transport_mode: string;
  description_zh: string | null;
  description_en: string | null;
  risk_transfer: string | null;
  is_current: boolean;
  sort_order: number;
  created_at: string | null;
}

export interface TradeTermListResponse {
  items: TradeTerm[];
  total: number;
}

export const tradeTermsApi = {
  // 获取贸易术语列表
  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    version?: string;
    is_current?: boolean;
  }): Promise<TradeTermListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.version) searchParams.set('version', params.version);
    if (params?.is_current !== undefined) searchParams.set('is_current', String(params.is_current));
    const query = searchParams.toString();
    const response = await request<TradeTermListResponse>(`/admin/trade-terms${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取贸易术语详情
  async get(id: string): Promise<TradeTerm> {
    const response = await request<TradeTerm>(`/admin/trade-terms/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};
