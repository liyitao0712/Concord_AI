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

export interface LLMConfig {
  default_model: string;
  available_models: Array<{
    id: string;
    name: string;
    provider: string;
    description: string;
    recommended?: boolean;
  }>;
  anthropic_configured: boolean;
  openai_configured: boolean;
  volcengine_configured: boolean;
  anthropic_key_preview: string | null;
  openai_key_preview: string | null;
  volcengine_key_preview: string | null;
}

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

export interface LLMConfigUpdate {
  default_model?: string;
  custom_model_id?: string;  // 自定义模型 ID（如火山引擎 Endpoint ID）
  anthropic_api_key?: string;
  openai_api_key?: string;
  volcengine_api_key?: string;
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

export interface TestResult {
  success: boolean;
  model?: string;
  provider?: string;
  response?: string;
  error?: string;
}

export const settingsApi = {
  // LLM 配置
  async getLLMConfig(): Promise<LLMConfig> {
    const response = await request<LLMConfig>('/admin/settings/llm');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  async updateLLMConfig(data: LLMConfigUpdate): Promise<any> {
    const response = await request('/admin/settings/llm', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data;
  },

  async testLLMConnection(modelId?: string): Promise<TestResult> {
    const response = await request<TestResult>('/admin/settings/llm/test', {
      method: 'POST',
      body: JSON.stringify(modelId ? { model_id: modelId } : {}),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

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

// ==================== 意图管理 API ====================

export interface IntentItem {
  id: string;
  name: string;
  label: string;
  description: string;
  examples: string[];
  keywords: string[];
  default_handler: string;
  handler_config: Record<string, unknown>;
  escalation_rules: Record<string, unknown> | null;
  escalation_workflow: string | null;
  priority: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface IntentListResponse {
  items: IntentItem[];
  total: number;
}

export interface IntentCreate {
  name: string;
  label: string;
  description: string;
  examples?: string[];
  keywords?: string[];
  default_handler?: string;
  handler_config?: Record<string, unknown>;
  escalation_rules?: Record<string, unknown>;
  escalation_workflow?: string;
  priority?: number;
  is_active?: boolean;
}

export interface IntentUpdate {
  label?: string;
  description?: string;
  examples?: string[];
  keywords?: string[];
  default_handler?: string;
  handler_config?: Record<string, unknown>;
  escalation_rules?: Record<string, unknown>;
  escalation_workflow?: string;
  priority?: number;
  is_active?: boolean;
}

export interface RouteTestRequest {
  content: string;
  source?: string;
  subject?: string;
}

export interface RouteTestResponse {
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

export interface IntentSuggestionItem {
  id: string;
  suggested_name: string;
  suggested_label: string;
  suggested_description: string;
  suggested_handler: string;
  trigger_message: string;
  trigger_source: string;
  status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface IntentSuggestionListResponse {
  items: IntentSuggestionItem[];
  total: number;
}

export const intentsApi = {
  // 获取意图列表
  async list(params?: { is_active?: boolean }): Promise<IntentListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    const query = searchParams.toString();
    const response = await request<IntentListResponse>(`/admin/intents${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取意图详情
  async get(id: string): Promise<IntentItem> {
    const response = await request<IntentItem>(`/admin/intents/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 创建意图
  async create(data: IntentCreate): Promise<IntentItem> {
    const response = await request<IntentItem>('/admin/intents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 更新意图
  async update(id: string, data: IntentUpdate): Promise<IntentItem> {
    const response = await request<IntentItem>(`/admin/intents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 删除意图
  async delete(id: string): Promise<void> {
    const response = await request(`/admin/intents/${id}`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // 测试路由分类
  async test(data: RouteTestRequest): Promise<RouteTestResponse> {
    const response = await request<RouteTestResponse>('/admin/intents/test', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 获取意图建议列表
  async listSuggestions(params?: { status?: string }): Promise<IntentSuggestionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    const response = await request<IntentSuggestionListResponse>(`/admin/intent-suggestions${query ? `?${query}` : ''}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 批准意图建议
  async approveSuggestion(id: string, note?: string): Promise<IntentItem> {
    const response = await request<IntentItem>(`/admin/intent-suggestions/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // 拒绝意图建议
  async rejectSuggestion(id: string, note?: string): Promise<void> {
    const response = await request(`/admin/intent-suggestions/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    if (response.error) throw new Error(response.error);
  },
};

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
  description: string;
  prompt_name: string;
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

  // 批准建议
  async approveSuggestion(id: string, note?: string): Promise<WorkType> {
    const response = await request<WorkType>(`/admin/work-type-suggestions/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
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
