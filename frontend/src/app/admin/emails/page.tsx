// src/app/admin/emails/page.tsx
// 邮件记录页面
//
// 功能说明：
// 1. 邮件列表展示（分页、搜索、筛选）
// 2. 查看邮件详情
// 3. 下载原始邮件
// 4. 下载附件
// 5. 路由分析（RouterAgent 意图分类）
// 6. 执行处理

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  emailsApi,
  emailAccountsApi,
  EmailListItem,
  EmailDetail,
  EmailAccount,
  EmailAnalysisResult,
  WorkTypeAnalyzeResult,
  getAccessToken,
} from '@/lib/api';

// 路由分析结果类型
interface RouteAnalyzeResult {
  intent: string;
  intent_label: string;
  confidence: number;
  reasoning: string;
  action: string;
  handler_config: Record<string, unknown>;
  new_suggestion: {
    name: string;
    label: string;
    description: string;
    suggested_handler: string;
  } | null;
}

// ==================== 工具函数 ====================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ==================== 模态框组件 ====================

function Modal({
  isOpen,
  onClose,
  title,
  children,
  wide = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 py-8">
        {/* 背景遮罩 */}
        <div
          className="fixed inset-0 bg-black opacity-50"
          onClick={onClose}
        />

        {/* 模态框内容 */}
        <div className={`relative bg-white rounded-lg shadow-xl ${wide ? 'max-w-3xl' : 'max-w-md'} w-full p-6 max-h-[90vh] overflow-y-auto`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

// ==================== 主页面 ====================

export default function EmailsPage() {
  // 列表状态
  const [emails, setEmails] = useState<EmailListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [accountFilter, setAccountFilter] = useState<number | undefined>();
  const [processedFilter, setProcessedFilter] = useState<boolean | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 邮箱账户列表（用于筛选）
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);

  // 详情弹窗
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<EmailDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 路由分析
  const [showAnalyzeModal, setShowAnalyzeModal] = useState(false);
  const [analyzingEmailId, setAnalyzingEmailId] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<RouteAnalyzeResult | null>(null);
  const [executing, setExecuting] = useState(false);

  // AI 分析（外贸场景）
  const [showAiAnalysisModal, setShowAiAnalysisModal] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<EmailAnalysisResult | null>(null);

  // 工作类型分析
  const [showWorkTypeModal, setShowWorkTypeModal] = useState(false);
  const [workTypeAnalyzing, setWorkTypeAnalyzing] = useState(false);
  const [workTypeResult, setWorkTypeResult] = useState<WorkTypeAnalyzeResult | null>(null);

  // 加载邮箱账户列表
  useEffect(() => {
    emailAccountsApi.list().then(res => {
      setAccounts(res.items);
    }).catch(() => {});
  }, []);

  // 加载邮件列表
  const loadEmails = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await emailsApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        account_id: accountFilter,
        is_processed: processedFilter,
      });

      setEmails(response.items);
      setTotal(response.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载邮件列表失败');
    }

    setLoading(false);
  }, [page, pageSize, search, accountFilter, processedFilter]);

  useEffect(() => {
    loadEmails();
  }, [loadEmails]);

  // 搜索防抖
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // 查看邮件详情
  const handleViewDetail = async (emailId: string) => {
    setLoadingDetail(true);
    setShowDetailModal(true);

    try {
      const detail = await emailsApi.get(emailId);
      setSelectedEmail(detail);
    } catch (e) {
      alert(e instanceof Error ? e.message : '加载邮件详情失败');
      setShowDetailModal(false);
    }

    setLoadingDetail(false);
  };

  // 下载原始邮件
  const handleDownloadRaw = (emailId: string) => {
    const url = emailsApi.getRawUrl(emailId);
    const token = getAccessToken();
    // 使用隐藏的 iframe 或直接打开带 token 的 URL
    window.open(`${url}?token=${token}`, '_blank');
  };

  // 下载附件
  const handleDownloadAttachment = (emailId: string, attachmentId: string) => {
    const url = emailsApi.getAttachmentUrl(emailId, attachmentId);
    const token = getAccessToken();
    window.open(`${url}?token=${token}`, '_blank');
  };

  // 分析邮件意图
  const handleAnalyze = async (emailId: string) => {
    setAnalyzingEmailId(emailId);
    setAnalyzing(true);
    setAnalyzeResult(null);
    setShowAnalyzeModal(true);

    try {
      const result = await emailsApi.analyze(emailId);
      setAnalyzeResult(result);
    } catch (e) {
      alert(e instanceof Error ? e.message : '分析失败');
      setShowAnalyzeModal(false);
    }

    setAnalyzing(false);
  };

  // 执行处理
  const handleExecute = async (intent?: string) => {
    if (!analyzingEmailId) return;

    setExecuting(true);
    try {
      const result = await emailsApi.execute(analyzingEmailId, { intent, force: true });
      if (result.success) {
        alert(`处理成功: ${result.message}`);
        setShowAnalyzeModal(false);
        loadEmails(); // 刷新列表
      } else {
        alert(`处理失败: ${result.error}`);
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : '执行失败');
    }
    setExecuting(false);
  };

  // AI 分析邮件（外贸场景）
  const handleAiAnalyze = async (emailId: string, force: boolean = false) => {
    setAnalyzingEmailId(emailId);
    setAiAnalyzing(true);
    setAiAnalysisResult(null);
    setShowAiAnalysisModal(true);

    try {
      const result = await emailsApi.aiAnalyze(emailId, force);
      setAiAnalysisResult(result);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'AI 分析失败';

      // 检查是否是 LLM 配置相关的错误
      if (
        errorMessage.includes('LLM 模型未配置') ||
        errorMessage.includes('API Key 未配置') ||
        errorMessage.includes('未找到可用的 LLM 模型配置')
      ) {
        const confirmGoToConfig = confirm(
          `❌ ${errorMessage}\n\n点击「确定」前往 LLM 配置页面添加模型配置。`
        );
        if (confirmGoToConfig) {
          window.location.href = '/admin/llm';
        }
      } else {
        alert(`❌ ${errorMessage}`);
      }

      setShowAiAnalysisModal(false);
    }

    setAiAnalyzing(false);
  };

  // 工作类型分析
  const handleWorkTypeAnalyze = async (emailId: string) => {
    setAnalyzingEmailId(emailId);
    setWorkTypeAnalyzing(true);
    setWorkTypeResult(null);
    setShowWorkTypeModal(true);

    try {
      const result = await emailsApi.workTypeAnalyze(emailId);
      setWorkTypeResult(result);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : '工作类型分析失败';

      if (
        errorMessage.includes('LLM 模型未配置') ||
        errorMessage.includes('API Key 未配置')
      ) {
        const confirmGoToConfig = confirm(
          `❌ ${errorMessage}\n\n点击「确定」前往 LLM 配置页面添加模型配置。`
        );
        if (confirmGoToConfig) {
          window.location.href = '/admin/llm';
        }
      } else {
        alert(`❌ ${errorMessage}`);
      }

      setShowWorkTypeModal(false);
    }

    setWorkTypeAnalyzing(false);
  };

  // 计算分页
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">邮件记录</h1>
        <p className="mt-1 text-sm text-gray-500">查看系统接收到的邮件</p>
      </div>

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="搜索发件人/主题..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
          <select
            value={accountFilter ?? ''}
            onChange={(e) => {
              setAccountFilter(e.target.value ? Number(e.target.value) : undefined);
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">全部邮箱</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>{acc.name}</option>
            ))}
          </select>
          <select
            value={processedFilter === undefined ? '' : processedFilter.toString()}
            onChange={(e) => {
              const val = e.target.value;
              setProcessedFilter(val === '' ? undefined : val === 'true');
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">全部状态</option>
            <option value="true">已处理</option>
            <option value="false">未处理</option>
          </select>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 邮件表格 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                发件人
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                主题
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                接收时间
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                附件
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  加载中...
                </td>
              </tr>
            ) : emails.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  暂无邮件记录
                </td>
              </tr>
            ) : (
              emails.map((email) => (
                <tr key={email.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {email.sender_name || email.sender}
                      </div>
                      {email.sender_name && (
                        <div className="text-sm text-gray-500">{email.sender}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 max-w-xs truncate" title={email.subject}>
                      {email.subject || '(无主题)'}
                    </div>
                    {email.email_account_name && (
                      <div className="text-xs text-gray-500">
                        {email.email_account_name}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDateTime(email.received_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        email.is_processed
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {email.is_processed ? '已处理' : '待处理'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {email.attachment_count > 0 ? (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                        </svg>
                        {email.attachment_count}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                    <button
                      onClick={() => handleAiAnalyze(email.id)}
                      className="text-green-600 hover:text-green-900"
                      title="AI 外贸邮件分析"
                    >
                      AI分析
                    </button>
                    <button
                      onClick={() => handleWorkTypeAnalyze(email.id)}
                      className="text-orange-600 hover:text-orange-900"
                      title="工作类型分析"
                    >
                      类型
                    </button>
                    <button
                      onClick={() => handleAnalyze(email.id)}
                      className="text-purple-600 hover:text-purple-900"
                      title="路由意图分析"
                    >
                      路由
                    </button>
                    <button
                      onClick={() => handleViewDetail(email.id)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      查看
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
            <div className="text-sm text-gray-500">
              共 {total} 封邮件，第 {page}/{totalPages} 页
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-50"
              >
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 邮件详情弹窗 */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => {
          setShowDetailModal(false);
          setSelectedEmail(null);
        }}
        title="邮件详情"
        wide
      >
        {loadingDetail ? (
          <div className="text-center py-8 text-gray-500">加载中...</div>
        ) : selectedEmail ? (
          <div className="space-y-6">
            {/* 基本信息 */}
            <div className="space-y-3">
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">发件人:</span>
                <span className="flex-1 text-sm">
                  {selectedEmail.sender_name && (
                    <span className="font-medium">{selectedEmail.sender_name} </span>
                  )}
                  <span className="text-gray-600">&lt;{selectedEmail.sender}&gt;</span>
                </span>
              </div>
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">收件人:</span>
                <span className="flex-1 text-sm text-gray-900">
                  {selectedEmail.recipients.join(', ')}
                </span>
              </div>
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">主题:</span>
                <span className="flex-1 text-sm font-medium text-gray-900">
                  {selectedEmail.subject || '(无主题)'}
                </span>
              </div>
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">时间:</span>
                <span className="flex-1 text-sm text-gray-900">
                  {formatDateTime(selectedEmail.received_at)}
                </span>
              </div>
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">大小:</span>
                <span className="flex-1 text-sm text-gray-900">
                  {formatFileSize(selectedEmail.size_bytes)}
                </span>
              </div>
              <div className="flex">
                <span className="w-20 text-gray-500 text-sm">状态:</span>
                <span className="flex-1">
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      selectedEmail.is_processed
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {selectedEmail.is_processed ? '已处理' : '待处理'}
                  </span>
                  {selectedEmail.processed_at && (
                    <span className="ml-2 text-xs text-gray-500">
                      {formatDateTime(selectedEmail.processed_at)}
                    </span>
                  )}
                </span>
              </div>
              {selectedEmail.email_account_name && (
                <div className="flex">
                  <span className="w-20 text-gray-500 text-sm">邮箱:</span>
                  <span className="flex-1 text-sm text-gray-900">
                    {selectedEmail.email_account_name}
                  </span>
                </div>
              )}
            </div>

            {/* 邮件正文 */}
            {selectedEmail.body_text && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">邮件内容</h4>
                <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                    {selectedEmail.body_text}
                  </pre>
                </div>
              </div>
            )}

            {/* 附件列表 */}
            {selectedEmail.attachments.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  附件 ({selectedEmail.attachments.length})
                </h4>
                <div className="space-y-2">
                  {selectedEmail.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded"
                    >
                      <div className="flex items-center min-w-0">
                        <svg className="w-4 h-4 mr-2 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                        </svg>
                        <div className="min-w-0">
                          <div className="text-sm text-gray-900 truncate">{att.filename}</div>
                          <div className="text-xs text-gray-500">
                            {formatFileSize(att.size_bytes)} - {att.content_type}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDownloadAttachment(selectedEmail.id, att.id)}
                        className="ml-3 text-blue-600 hover:text-blue-800 text-sm flex-shrink-0"
                      >
                        下载
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => handleDownloadRaw(selectedEmail.id)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
              >
                下载原始邮件 (.eml)
              </button>
              <button
                onClick={() => {
                  setShowDetailModal(false);
                  setSelectedEmail(null);
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-md text-sm hover:bg-gray-700"
              >
                关闭
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* 路由分析弹窗 */}
      <Modal
        isOpen={showAnalyzeModal}
        onClose={() => {
          setShowAnalyzeModal(false);
          setAnalyzeResult(null);
          setAnalyzingEmailId(null);
        }}
        title="AI 路由分析"
        wide
      >
        {analyzing ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent mb-4"></div>
            <p className="text-gray-600">正在分析邮件意图...</p>
          </div>
        ) : analyzeResult ? (
          <div className="space-y-6">
            {/* 意图识别结果 */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-700">识别结果</h4>
                <span
                  className={`px-2 py-1 text-xs font-medium rounded ${
                    analyzeResult.confidence >= 0.8
                      ? 'bg-green-100 text-green-800'
                      : analyzeResult.confidence >= 0.5
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  置信度: {(analyzeResult.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center space-x-3 mb-3">
                <span className="px-3 py-1.5 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
                  {analyzeResult.intent_label}
                </span>
                <span className="text-xs text-gray-500">({analyzeResult.intent})</span>
              </div>
              <p className="text-sm text-gray-600">{analyzeResult.reasoning}</p>
            </div>

            {/* 处理方式 */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">处理方式</h4>
              <div className="space-y-2">
                <div className="flex items-center">
                  <span className="w-20 text-xs text-gray-500">动作:</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-blue-100 text-blue-800">
                    Agent 处理
                  </span>
                </div>
                {analyzeResult.handler_config && Object.keys(analyzeResult.handler_config).length > 0 && (
                  <div className="flex items-start">
                    <span className="w-20 text-xs text-gray-500">配置:</span>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                      {JSON.stringify(analyzeResult.handler_config)}
                    </code>
                  </div>
                )}
              </div>
            </div>

            {/* 新意图建议 */}
            {analyzeResult.new_suggestion && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-purple-500 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-purple-800">AI 建议创建新意图</h4>
                    <div className="mt-2 space-y-1 text-sm">
                      <p><span className="text-gray-500">名称:</span> <span className="font-medium">{analyzeResult.new_suggestion.label}</span> ({analyzeResult.new_suggestion.name})</p>
                      <p><span className="text-gray-500">描述:</span> {analyzeResult.new_suggestion.description}</p>
                      <p><span className="text-gray-500">建议处理:</span> {analyzeResult.new_suggestion.suggested_handler}</p>
                    </div>
                    <p className="mt-2 text-xs text-purple-600">此建议将进入审批流程，管理员确认后生效</p>
                  </div>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => {
                  setShowAnalyzeModal(false);
                  setAnalyzeResult(null);
                  setAnalyzingEmailId(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={() => handleExecute(analyzeResult.intent)}
                disabled={executing}
                className="px-4 py-2 bg-purple-600 text-white rounded-md text-sm hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {executing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    执行中...
                  </>
                ) : (
                  <>
                    执行处理
                  </>
                )}
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* AI 分析弹窗（外贸场景） */}
      <Modal
        isOpen={showAiAnalysisModal}
        onClose={() => {
          setShowAiAnalysisModal(false);
          setAiAnalysisResult(null);
          setAnalyzingEmailId(null);
        }}
        title="AI 邮件分析"
        wide
      >
        {aiAnalyzing ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-green-500 border-t-transparent mb-4"></div>
            <p className="text-gray-600">正在分析邮件内容...</p>
            <p className="text-xs text-gray-400 mt-2">AI 正在提取摘要、意图、产品、金额等信息</p>
          </div>
        ) : aiAnalysisResult ? (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            {/* 摘要 */}
            <div className="bg-green-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">摘要</h4>
              <p className="text-gray-900">{aiAnalysisResult.summary}</p>
              {aiAnalysisResult.key_points && aiAnalysisResult.key_points.length > 0 && (
                <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                  {aiAnalysisResult.key_points.map((point, i) => (
                    <li key={i}>{point}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* 发件方 & 意图 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">发件方</h4>
                <div className="space-y-1 text-sm">
                  {aiAnalysisResult.sender_type && (
                    <p>
                      <span className="text-gray-500">类型:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        aiAnalysisResult.sender_type === 'customer' ? 'bg-blue-100 text-blue-800' :
                        aiAnalysisResult.sender_type === 'supplier' ? 'bg-orange-100 text-orange-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {aiAnalysisResult.sender_type === 'customer' ? '客户' :
                         aiAnalysisResult.sender_type === 'supplier' ? '供应商' :
                         aiAnalysisResult.sender_type}
                      </span>
                    </p>
                  )}
                  {aiAnalysisResult.sender_company && (
                    <p><span className="text-gray-500">公司:</span> {aiAnalysisResult.sender_company}</p>
                  )}
                  {aiAnalysisResult.sender_country && (
                    <p><span className="text-gray-500">国家:</span> {aiAnalysisResult.sender_country}</p>
                  )}
                  {aiAnalysisResult.is_new_contact !== null && (
                    <p><span className="text-gray-500">新联系人:</span> {aiAnalysisResult.is_new_contact ? '是' : '否'}</p>
                  )}
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">意图 & 情感</h4>
                <div className="space-y-1 text-sm">
                  {aiAnalysisResult.intent && (
                    <p>
                      <span className="text-gray-500">意图:</span>{' '}
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs">
                        {aiAnalysisResult.intent}
                      </span>
                      {aiAnalysisResult.intent_confidence !== null && (
                        <span className="text-gray-400 text-xs ml-1">
                          ({(aiAnalysisResult.intent_confidence * 100).toFixed(0)}%)
                        </span>
                      )}
                    </p>
                  )}
                  {aiAnalysisResult.urgency && (
                    <p>
                      <span className="text-gray-500">紧急度:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        aiAnalysisResult.urgency === 'urgent' ? 'bg-red-100 text-red-800' :
                        aiAnalysisResult.urgency === 'high' ? 'bg-orange-100 text-orange-800' :
                        aiAnalysisResult.urgency === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {aiAnalysisResult.urgency}
                      </span>
                    </p>
                  )}
                  {aiAnalysisResult.sentiment && (
                    <p>
                      <span className="text-gray-500">情感:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        aiAnalysisResult.sentiment === 'positive' ? 'bg-green-100 text-green-800' :
                        aiAnalysisResult.sentiment === 'negative' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {aiAnalysisResult.sentiment === 'positive' ? '积极' :
                         aiAnalysisResult.sentiment === 'negative' ? '消极' : '中性'}
                      </span>
                    </p>
                  )}
                  {aiAnalysisResult.priority && (
                    <p>
                      <span className="text-gray-500">优先级:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        aiAnalysisResult.priority === 'p0' ? 'bg-red-100 text-red-800' :
                        aiAnalysisResult.priority === 'p1' ? 'bg-orange-100 text-orange-800' :
                        aiAnalysisResult.priority === 'p2' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {aiAnalysisResult.priority}
                      </span>
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* 产品信息 */}
            {aiAnalysisResult.products && aiAnalysisResult.products.length > 0 && (
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">产品信息</h4>
                <div className="space-y-2">
                  {aiAnalysisResult.products.map((product, i) => (
                    <div key={i} className="bg-white rounded p-2 text-sm">
                      <span className="font-medium">{product.name}</span>
                      {product.specs && <span className="text-gray-500 ml-2">({product.specs})</span>}
                      {product.quantity && (
                        <span className="text-gray-600 ml-2">
                          x {product.quantity} {product.unit || ''}
                        </span>
                      )}
                      {product.target_price && (
                        <span className="text-green-600 ml-2">
                          目标价: {product.target_price}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 金额 & 贸易条款 */}
            <div className="grid grid-cols-2 gap-4">
              {aiAnalysisResult.amounts && aiAnalysisResult.amounts.length > 0 && (
                <div className="bg-yellow-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">金额</h4>
                  <div className="space-y-1">
                    {aiAnalysisResult.amounts.map((amt, i) => (
                      <p key={i} className="text-sm">
                        <span className="font-medium text-yellow-800">
                          {amt.currency} {amt.value.toLocaleString()}
                        </span>
                        {amt.context && <span className="text-gray-500 ml-2">({amt.context})</span>}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {aiAnalysisResult.trade_terms && (
                <div className="bg-orange-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">贸易条款</h4>
                  <div className="space-y-1 text-sm">
                    {aiAnalysisResult.trade_terms.incoterm && (
                      <p><span className="text-gray-500">贸易术语:</span> {aiAnalysisResult.trade_terms.incoterm}</p>
                    )}
                    {aiAnalysisResult.trade_terms.payment_terms && (
                      <p><span className="text-gray-500">付款方式:</span> {aiAnalysisResult.trade_terms.payment_terms}</p>
                    )}
                    {aiAnalysisResult.trade_terms.destination && (
                      <p><span className="text-gray-500">目的地:</span> {aiAnalysisResult.trade_terms.destination}</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 问题 & 需要做的事 */}
            {(aiAnalysisResult.questions?.length || aiAnalysisResult.action_required?.length) && (
              <div className="grid grid-cols-2 gap-4">
                {aiAnalysisResult.questions && aiAnalysisResult.questions.length > 0 && (
                  <div className="bg-purple-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">对方问题</h4>
                    <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                      {aiAnalysisResult.questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {aiAnalysisResult.action_required && aiAnalysisResult.action_required.length > 0 && (
                  <div className="bg-red-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">需要处理</h4>
                    <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                      {aiAnalysisResult.action_required.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* 建议回复 */}
            {aiAnalysisResult.suggested_reply && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-green-800 mb-2">建议回复要点</h4>
                <p className="text-sm text-gray-700">{aiAnalysisResult.suggested_reply}</p>
              </div>
            )}

            {/* 元数据 */}
            <div className="text-xs text-gray-400 flex justify-between pt-2 border-t">
              <span>模型: {aiAnalysisResult.llm_model || '-'}</span>
              <span>Token: {aiAnalysisResult.token_used || '-'}</span>
              <span>语言: {aiAnalysisResult.original_language || '-'}</span>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => analyzingEmailId && handleAiAnalyze(analyzingEmailId, true)}
                disabled={aiAnalyzing}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
              >
                重新分析
              </button>
              <button
                onClick={() => {
                  setShowAiAnalysisModal(false);
                  setAiAnalysisResult(null);
                  setAnalyzingEmailId(null);
                }}
                className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700"
              >
                关闭
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* 工作类型分析弹窗 */}
      <Modal
        isOpen={showWorkTypeModal}
        onClose={() => {
          setShowWorkTypeModal(false);
          setWorkTypeResult(null);
          setAnalyzingEmailId(null);
        }}
        title="工作类型分析"
        wide
      >
        {workTypeAnalyzing ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-orange-500 border-t-transparent mb-4"></div>
            <p className="text-gray-600">正在分析工作类型...</p>
            <p className="text-xs text-gray-400 mt-2">AI 正在匹配现有类型或识别新类型</p>
          </div>
        ) : workTypeResult ? (
          <div className="space-y-4">
            {/* 匹配结果 */}
            {workTypeResult.matched_work_type ? (
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-gray-700">匹配到的工作类型</h4>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded ${
                      workTypeResult.matched_work_type.confidence >= 0.8
                        ? 'bg-green-100 text-green-800'
                        : workTypeResult.matched_work_type.confidence >= 0.5
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    置信度: {(workTypeResult.matched_work_type.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center space-x-3 mb-2">
                  <span className="px-3 py-1.5 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                    {workTypeResult.matched_work_type.code}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{workTypeResult.matched_work_type.reason}</p>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">未匹配到现有工作类型</p>
              </div>
            )}

            {/* 新类型建议 */}
            {workTypeResult.new_suggestion?.should_suggest && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-orange-500 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-orange-800">AI 建议创建新工作类型</h4>
                    <div className="mt-2 space-y-1 text-sm">
                      <p>
                        <span className="text-gray-500">代码:</span>{' '}
                        <span className="font-medium">{workTypeResult.new_suggestion.suggested_code}</span>
                      </p>
                      <p>
                        <span className="text-gray-500">名称:</span>{' '}
                        <span className="font-medium">{workTypeResult.new_suggestion.suggested_name}</span>
                      </p>
                      {workTypeResult.new_suggestion.suggested_parent_code && (
                        <p>
                          <span className="text-gray-500">父级:</span>{' '}
                          {workTypeResult.new_suggestion.suggested_parent_code}
                        </p>
                      )}
                      <p>
                        <span className="text-gray-500">描述:</span>{' '}
                        {workTypeResult.new_suggestion.suggested_description}
                      </p>
                      <p>
                        <span className="text-gray-500">置信度:</span>{' '}
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          (workTypeResult.new_suggestion.confidence || 0) >= 0.8
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {((workTypeResult.new_suggestion.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </p>
                      {workTypeResult.new_suggestion.reasoning && (
                        <p>
                          <span className="text-gray-500">推理:</span>{' '}
                          <span className="text-gray-600">{workTypeResult.new_suggestion.reasoning}</span>
                        </p>
                      )}
                    </div>
                    {workTypeResult.suggestion_id ? (
                      <div className="mt-3 p-2 bg-green-100 rounded text-sm text-green-800">
                        ✅ 已创建审批请求，请前往「工作类型管理」页面审批
                      </div>
                    ) : (
                      <p className="mt-2 text-xs text-orange-600">
                        此建议将自动进入审批流程，管理员确认后生效
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 元数据 */}
            <div className="text-xs text-gray-400 pt-2 border-t">
              <span>模型: {workTypeResult.llm_model || '-'}</span>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              {workTypeResult.suggestion_id && (
                <a
                  href="/admin/work-types"
                  className="px-4 py-2 border border-orange-300 text-orange-700 rounded-md text-sm hover:bg-orange-50"
                >
                  前往审批
                </a>
              )}
              <button
                onClick={() => {
                  setShowWorkTypeModal(false);
                  setWorkTypeResult(null);
                  setAnalyzingEmailId(null);
                }}
                className="px-4 py-2 bg-orange-600 text-white rounded-md text-sm hover:bg-orange-700"
              >
                关闭
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
