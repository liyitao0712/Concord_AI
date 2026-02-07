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
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { LoadingSpinner, PageLoading } from '@/components/LoadingSpinner';
import { Paperclip, Lightbulb, Check, X } from 'lucide-react';

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

// ==================== 主页面 ====================

export default function EmailsPage() {
  const confirm = useConfirm();

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
      toast.error(e instanceof Error ? e.message : '加载邮件详情失败');
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
      toast.error(e instanceof Error ? e.message : '分析失败');
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
        toast.success(`处理成功: ${result.message}`);
        setShowAnalyzeModal(false);
        loadEmails(); // 刷新列表
      } else {
        toast.error(`处理失败: ${result.error}`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '执行失败');
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
        const confirmed = await confirm({
          title: 'LLM 配置错误',
          description: `${errorMessage}\n\n点击「确认」前往 LLM 配置页面添加模型配置。`,
          confirmText: '前往配置',
        });
        if (confirmed) {
          window.location.href = '/admin/llm';
        }
      } else {
        toast.error(errorMessage);
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
        const confirmed = await confirm({
          title: 'LLM 配置错误',
          description: `${errorMessage}\n\n点击「确认」前往 LLM 配置页面添加模型配置。`,
          confirmText: '前往配置',
        });
        if (confirmed) {
          window.location.href = '/admin/llm';
        }
      } else {
        toast.error(errorMessage);
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
        <h1 className="text-2xl font-bold text-foreground">邮件记录</h1>
        <p className="mt-1 text-sm text-muted-foreground">查看系统接收到的邮件</p>
      </div>

      {/* 搜索和筛选 */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-4">
          <Input
            type="text"
            placeholder="搜索发件人/主题..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <select
            value={accountFilter ?? ''}
            onChange={(e) => {
              setAccountFilter(e.target.value ? Number(e.target.value) : undefined);
              setPage(1);
            }}
            className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
            className="px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">全部状态</option>
            <option value="true">已处理</option>
            <option value="false">未处理</option>
          </select>
        </div>
      </Card>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 邮件表格 */}
      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="px-6">发件人</TableHead>
              <TableHead className="px-6">主题</TableHead>
              <TableHead className="px-6">接收时间</TableHead>
              <TableHead className="px-6">状态</TableHead>
              <TableHead className="px-6">附件</TableHead>
              <TableHead className="px-6 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="px-6 py-4 text-center text-muted-foreground">
                  <LoadingSpinner text="加载中..." />
                </TableCell>
              </TableRow>
            ) : emails.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="px-6 py-4 text-center text-muted-foreground">
                  暂无邮件记录
                </TableCell>
              </TableRow>
            ) : (
              emails.map((email) => (
                <TableRow key={email.id}>
                  <TableCell className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-foreground">
                        {email.sender_name || email.sender}
                      </div>
                      {email.sender_name && (
                        <div className="text-sm text-muted-foreground">{email.sender}</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <div className="text-sm text-foreground max-w-xs truncate" title={email.subject}>
                      {email.subject || '(无主题)'}
                    </div>
                    {email.email_account_name && (
                      <div className="text-xs text-muted-foreground">
                        {email.email_account_name}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {formatDateTime(email.received_at)}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <Badge
                      className={
                        email.is_processed
                          ? 'bg-green-100 text-green-800 border-green-200'
                          : 'bg-yellow-100 text-yellow-800 border-yellow-200'
                      }
                    >
                      {email.is_processed ? '已处理' : '待处理'}
                    </Badge>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {email.attachment_count > 0 ? (
                      <span className="flex items-center">
                        <Paperclip className="size-4 mr-1" />
                        {email.attachment_count}
                      </span>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-right text-sm font-medium space-x-3">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleAiAnalyze(email.id)}
                      className="text-green-600 hover:text-green-900"
                      title="AI 外贸邮件分析"
                    >
                      AI分析
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleWorkTypeAnalyze(email.id)}
                      className="text-orange-600 hover:text-orange-900"
                      title="工作类型分析"
                    >
                      类型
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleAnalyze(email.id)}
                      className="text-purple-600 hover:text-purple-900"
                      title="路由意图分析"
                    >
                      路由
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleViewDetail(email.id)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      查看
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="px-4 py-3 flex items-center justify-between border-t">
            <div className="text-sm text-muted-foreground">
              共 {total} 封邮件，第 {page}/{totalPages} 页
            </div>
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* 邮件详情弹窗 */}
      <Dialog
        open={showDetailModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowDetailModal(false);
            setSelectedEmail(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>邮件详情</DialogTitle>
          </DialogHeader>
          {loadingDetail ? (
            <div className="text-center py-8">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : selectedEmail ? (
            <div className="space-y-6">
              {/* 基本信息 */}
              <div className="space-y-3">
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">发件人:</span>
                  <span className="flex-1 text-sm">
                    {selectedEmail.sender_name && (
                      <span className="font-medium">{selectedEmail.sender_name} </span>
                    )}
                    <span className="text-muted-foreground">&lt;{selectedEmail.sender}&gt;</span>
                  </span>
                </div>
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">收件人:</span>
                  <span className="flex-1 text-sm text-foreground">
                    {selectedEmail.recipients.join(', ')}
                  </span>
                </div>
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">主题:</span>
                  <span className="flex-1 text-sm font-medium text-foreground">
                    {selectedEmail.subject || '(无主题)'}
                  </span>
                </div>
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">时间:</span>
                  <span className="flex-1 text-sm text-foreground">
                    {formatDateTime(selectedEmail.received_at)}
                  </span>
                </div>
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">大小:</span>
                  <span className="flex-1 text-sm text-foreground">
                    {formatFileSize(selectedEmail.size_bytes)}
                  </span>
                </div>
                <div className="flex">
                  <span className="w-20 text-muted-foreground text-sm">状态:</span>
                  <span className="flex-1">
                    <Badge
                      className={
                        selectedEmail.is_processed
                          ? 'bg-green-100 text-green-800 border-green-200'
                          : 'bg-yellow-100 text-yellow-800 border-yellow-200'
                      }
                    >
                      {selectedEmail.is_processed ? '已处理' : '待处理'}
                    </Badge>
                    {selectedEmail.processed_at && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatDateTime(selectedEmail.processed_at)}
                      </span>
                    )}
                  </span>
                </div>
                {selectedEmail.email_account_name && (
                  <div className="flex">
                    <span className="w-20 text-muted-foreground text-sm">邮箱:</span>
                    <span className="flex-1 text-sm text-foreground">
                      {selectedEmail.email_account_name}
                    </span>
                  </div>
                )}
              </div>

              {/* 邮件正文 */}
              {selectedEmail.body_text && (
                <div>
                  <h4 className="text-sm font-medium text-foreground mb-2">邮件内容</h4>
                  <div className="bg-muted rounded-lg p-4 max-h-96 overflow-y-auto">
                    <pre className="text-sm text-foreground whitespace-pre-wrap font-sans">
                      {selectedEmail.body_text}
                    </pre>
                  </div>
                </div>
              )}

              {/* 附件列表 */}
              {selectedEmail.attachments.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-foreground mb-2">
                    附件 ({selectedEmail.attachments.length})
                  </h4>
                  <div className="space-y-2">
                    {selectedEmail.attachments.map((att) => (
                      <div
                        key={att.id}
                        className="flex items-center justify-between px-3 py-2 bg-muted rounded"
                      >
                        <div className="flex items-center min-w-0">
                          <Paperclip className="size-4 mr-2 text-muted-foreground flex-shrink-0" />
                          <div className="min-w-0">
                            <div className="text-sm text-foreground truncate">{att.filename}</div>
                            <div className="text-xs text-muted-foreground">
                              {formatFileSize(att.size_bytes)} - {att.content_type}
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => handleDownloadAttachment(selectedEmail.id, att.id)}
                          className="ml-3 text-blue-600 hover:text-blue-800 flex-shrink-0"
                        >
                          下载
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex justify-end space-x-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => handleDownloadRaw(selectedEmail.id)}
                >
                  下载原始邮件 (.eml)
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowDetailModal(false);
                    setSelectedEmail(null);
                  }}
                >
                  关闭
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* 路由分析弹窗 */}
      <Dialog
        open={showAnalyzeModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowAnalyzeModal(false);
            setAnalyzeResult(null);
            setAnalyzingEmailId(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>AI 路由分析</DialogTitle>
          </DialogHeader>
          {analyzing ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent mb-4"></div>
              <p className="text-muted-foreground">正在分析邮件意图...</p>
            </div>
          ) : analyzeResult ? (
            <div className="space-y-6">
              {/* 意图识别结果 */}
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-muted-foreground">识别结果</h4>
                  <Badge
                    className={
                      analyzeResult.confidence >= 0.8
                        ? 'bg-green-100 text-green-800 border-green-200'
                        : analyzeResult.confidence >= 0.5
                        ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                        : 'bg-red-100 text-red-800 border-red-200'
                    }
                  >
                    置信度: {(analyzeResult.confidence * 100).toFixed(0)}%
                  </Badge>
                </div>
                <div className="flex items-center space-x-3 mb-3">
                  <Badge className="bg-purple-100 text-purple-800 border-purple-200 px-3 py-1.5">
                    {analyzeResult.intent_label}
                  </Badge>
                  <span className="text-xs text-muted-foreground">({analyzeResult.intent})</span>
                </div>
                <p className="text-sm text-muted-foreground">{analyzeResult.reasoning}</p>
              </div>

              {/* 处理方式 */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-muted-foreground mb-3">处理方式</h4>
                <div className="space-y-2">
                  <div className="flex items-center">
                    <span className="w-20 text-xs text-muted-foreground">动作:</span>
                    <Badge className="bg-blue-100 text-blue-800 border-blue-200">
                      Agent 处理
                    </Badge>
                  </div>
                  {analyzeResult.handler_config && Object.keys(analyzeResult.handler_config).length > 0 && (
                    <div className="flex items-start">
                      <span className="w-20 text-xs text-muted-foreground">配置:</span>
                      <code className="text-xs bg-muted px-2 py-1 rounded">
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
                    <Lightbulb className="size-5 text-purple-500 mt-0.5 mr-2 flex-shrink-0" />
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-purple-800">AI 建议创建新意图</h4>
                      <div className="mt-2 space-y-1 text-sm">
                        <p><span className="text-muted-foreground">名称:</span> <span className="font-medium">{analyzeResult.new_suggestion.label}</span> ({analyzeResult.new_suggestion.name})</p>
                        <p><span className="text-muted-foreground">描述:</span> {analyzeResult.new_suggestion.description}</p>
                        <p><span className="text-muted-foreground">建议处理:</span> {analyzeResult.new_suggestion.suggested_handler}</p>
                      </div>
                      <p className="mt-2 text-xs text-purple-600">此建议将进入审批流程，管理员确认后生效</p>
                    </div>
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex justify-end space-x-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAnalyzeModal(false);
                    setAnalyzeResult(null);
                    setAnalyzingEmailId(null);
                  }}
                >
                  取消
                </Button>
                <Button
                  onClick={() => handleExecute(analyzeResult.intent)}
                  disabled={executing}
                  className="bg-purple-600 hover:bg-purple-700"
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
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* AI 分析弹窗（外贸场景） */}
      <Dialog
        open={showAiAnalysisModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowAiAnalysisModal(false);
            setAiAnalysisResult(null);
            setAnalyzingEmailId(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>AI 邮件分析</DialogTitle>
          </DialogHeader>
          {aiAnalyzing ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-green-500 border-t-transparent mb-4"></div>
              <p className="text-muted-foreground">正在分析邮件内容...</p>
              <p className="text-xs text-muted-foreground mt-2">AI 正在提取摘要、意图、产品、金额等信息</p>
            </div>
          ) : aiAnalysisResult ? (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              {/* 摘要 */}
              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-muted-foreground mb-2">摘要</h4>
                <p className="text-foreground">{aiAnalysisResult.summary}</p>
                {aiAnalysisResult.key_points && aiAnalysisResult.key_points.length > 0 && (
                  <ul className="mt-2 text-sm text-muted-foreground list-disc list-inside">
                    {aiAnalysisResult.key_points.map((point, i) => (
                      <li key={i}>{point}</li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 发件方 & 意图 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-muted rounded-lg p-4">
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">发件方</h4>
                  <div className="space-y-1 text-sm">
                    {aiAnalysisResult.sender_type && (
                      <p>
                        <span className="text-muted-foreground">类型:</span>{' '}
                        <Badge className={
                          aiAnalysisResult.sender_type === 'customer' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                          aiAnalysisResult.sender_type === 'supplier' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                          'bg-secondary text-secondary-foreground'
                        }>
                          {aiAnalysisResult.sender_type === 'customer' ? '客户' :
                           aiAnalysisResult.sender_type === 'supplier' ? '供应商' :
                           aiAnalysisResult.sender_type}
                        </Badge>
                      </p>
                    )}
                    {aiAnalysisResult.sender_company && (
                      <p><span className="text-muted-foreground">公司:</span> {aiAnalysisResult.sender_company}</p>
                    )}
                    {aiAnalysisResult.sender_country && (
                      <p><span className="text-muted-foreground">国家:</span> {aiAnalysisResult.sender_country}</p>
                    )}
                    {aiAnalysisResult.is_new_contact !== null && (
                      <p><span className="text-muted-foreground">新联系人:</span> {aiAnalysisResult.is_new_contact ? '是' : '否'}</p>
                    )}
                  </div>
                </div>

                <div className="bg-muted rounded-lg p-4">
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">意图 & 情感</h4>
                  <div className="space-y-1 text-sm">
                    {aiAnalysisResult.intent && (
                      <p>
                        <span className="text-muted-foreground">意图:</span>{' '}
                        <Badge className="bg-purple-100 text-purple-800 border-purple-200">
                          {aiAnalysisResult.intent}
                        </Badge>
                        {aiAnalysisResult.intent_confidence !== null && (
                          <span className="text-muted-foreground text-xs ml-1">
                            ({(aiAnalysisResult.intent_confidence * 100).toFixed(0)}%)
                          </span>
                        )}
                      </p>
                    )}
                    {aiAnalysisResult.urgency && (
                      <p>
                        <span className="text-muted-foreground">紧急度:</span>{' '}
                        <Badge className={
                          aiAnalysisResult.urgency === 'urgent' ? 'bg-red-100 text-red-800 border-red-200' :
                          aiAnalysisResult.urgency === 'high' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                          aiAnalysisResult.urgency === 'medium' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                          'bg-green-100 text-green-800 border-green-200'
                        }>
                          {aiAnalysisResult.urgency}
                        </Badge>
                      </p>
                    )}
                    {aiAnalysisResult.sentiment && (
                      <p>
                        <span className="text-muted-foreground">情感:</span>{' '}
                        <Badge className={
                          aiAnalysisResult.sentiment === 'positive' ? 'bg-green-100 text-green-800 border-green-200' :
                          aiAnalysisResult.sentiment === 'negative' ? 'bg-red-100 text-red-800 border-red-200' :
                          'bg-secondary text-secondary-foreground'
                        }>
                          {aiAnalysisResult.sentiment === 'positive' ? '积极' :
                           aiAnalysisResult.sentiment === 'negative' ? '消极' : '中性'}
                        </Badge>
                      </p>
                    )}
                    {aiAnalysisResult.priority && (
                      <p>
                        <span className="text-muted-foreground">优先级:</span>{' '}
                        <Badge className={
                          aiAnalysisResult.priority === 'p0' ? 'bg-red-100 text-red-800 border-red-200' :
                          aiAnalysisResult.priority === 'p1' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                          aiAnalysisResult.priority === 'p2' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                          'bg-secondary text-secondary-foreground'
                        }>
                          {aiAnalysisResult.priority}
                        </Badge>
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* 产品信息 */}
              {aiAnalysisResult.products && aiAnalysisResult.products.length > 0 && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">产品信息</h4>
                  <div className="space-y-2">
                    {aiAnalysisResult.products.map((product, i) => (
                      <div key={i} className="bg-background rounded p-2 text-sm">
                        <span className="font-medium">{product.name}</span>
                        {product.specs && <span className="text-muted-foreground ml-2">({product.specs})</span>}
                        {product.quantity && (
                          <span className="text-muted-foreground ml-2">
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
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">金额</h4>
                    <div className="space-y-1">
                      {aiAnalysisResult.amounts.map((amt, i) => (
                        <p key={i} className="text-sm">
                          <span className="font-medium text-yellow-800">
                            {amt.currency} {amt.value.toLocaleString()}
                          </span>
                          {amt.context && <span className="text-muted-foreground ml-2">({amt.context})</span>}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {aiAnalysisResult.trade_terms && (
                  <div className="bg-orange-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">贸易条款</h4>
                    <div className="space-y-1 text-sm">
                      {aiAnalysisResult.trade_terms.incoterm && (
                        <p><span className="text-muted-foreground">贸易术语:</span> {aiAnalysisResult.trade_terms.incoterm}</p>
                      )}
                      {aiAnalysisResult.trade_terms.payment_terms && (
                        <p><span className="text-muted-foreground">付款方式:</span> {aiAnalysisResult.trade_terms.payment_terms}</p>
                      )}
                      {aiAnalysisResult.trade_terms.destination && (
                        <p><span className="text-muted-foreground">目的地:</span> {aiAnalysisResult.trade_terms.destination}</p>
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
                      <h4 className="text-sm font-medium text-muted-foreground mb-2">对方问题</h4>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                        {aiAnalysisResult.questions.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {aiAnalysisResult.action_required && aiAnalysisResult.action_required.length > 0 && (
                    <div className="bg-red-50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-muted-foreground mb-2">需要处理</h4>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
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
                  <p className="text-sm text-foreground">{aiAnalysisResult.suggested_reply}</p>
                </div>
              )}

              {/* 元数据 */}
              <div className="text-xs text-muted-foreground flex justify-between pt-2 border-t">
                <span>模型: {aiAnalysisResult.llm_model || '-'}</span>
                <span>Token: {aiAnalysisResult.token_used || '-'}</span>
                <span>语言: {aiAnalysisResult.original_language || '-'}</span>
              </div>

              {/* 操作按钮 */}
              <div className="flex justify-end space-x-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => analyzingEmailId && handleAiAnalyze(analyzingEmailId, true)}
                  disabled={aiAnalyzing}
                >
                  重新分析
                </Button>
                <Button
                  className="bg-green-600 hover:bg-green-700"
                  onClick={() => {
                    setShowAiAnalysisModal(false);
                    setAiAnalysisResult(null);
                    setAnalyzingEmailId(null);
                  }}
                >
                  关闭
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* 工作类型分析弹窗 */}
      <Dialog
        open={showWorkTypeModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowWorkTypeModal(false);
            setWorkTypeResult(null);
            setAnalyzingEmailId(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>工作类型分析</DialogTitle>
          </DialogHeader>
          {workTypeAnalyzing ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-orange-500 border-t-transparent mb-4"></div>
              <p className="text-muted-foreground">正在分析工作类型...</p>
              <p className="text-xs text-muted-foreground mt-2">AI 正在匹配现有类型或识别新类型</p>
            </div>
          ) : workTypeResult ? (
            <div className="space-y-4">
              {/* 匹配结果 */}
              {workTypeResult.matched_work_type ? (
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-muted-foreground">匹配到的工作类型</h4>
                    <Badge
                      className={
                        workTypeResult.matched_work_type.confidence >= 0.8
                          ? 'bg-green-100 text-green-800 border-green-200'
                          : workTypeResult.matched_work_type.confidence >= 0.5
                          ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                          : 'bg-red-100 text-red-800 border-red-200'
                      }
                    >
                      置信度: {(workTypeResult.matched_work_type.confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex items-center space-x-3 mb-2">
                    <Badge className="bg-green-100 text-green-800 border-green-200 px-3 py-1.5">
                      {workTypeResult.matched_work_type.code}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{workTypeResult.matched_work_type.reason}</p>
                </div>
              ) : (
                <div className="bg-muted rounded-lg p-4">
                  <p className="text-sm text-muted-foreground">未匹配到现有工作类型</p>
                </div>
              )}

              {/* 新类型建议 */}
              {workTypeResult.new_suggestion?.should_suggest && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <Lightbulb className="size-5 text-orange-500 mt-0.5 mr-2 flex-shrink-0" />
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-orange-800">AI 建议创建新工作类型</h4>
                      <div className="mt-2 space-y-1 text-sm">
                        <p>
                          <span className="text-muted-foreground">代码:</span>{' '}
                          <span className="font-medium">{workTypeResult.new_suggestion.suggested_code}</span>
                        </p>
                        <p>
                          <span className="text-muted-foreground">名称:</span>{' '}
                          <span className="font-medium">{workTypeResult.new_suggestion.suggested_name}</span>
                        </p>
                        {workTypeResult.new_suggestion.suggested_parent_code && (
                          <p>
                            <span className="text-muted-foreground">父级:</span>{' '}
                            {workTypeResult.new_suggestion.suggested_parent_code}
                          </p>
                        )}
                        <p>
                          <span className="text-muted-foreground">描述:</span>{' '}
                          {workTypeResult.new_suggestion.suggested_description}
                        </p>
                        <p>
                          <span className="text-muted-foreground">置信度:</span>{' '}
                          <Badge className={
                            (workTypeResult.new_suggestion.confidence || 0) >= 0.8
                              ? 'bg-green-100 text-green-800 border-green-200'
                              : 'bg-yellow-100 text-yellow-800 border-yellow-200'
                          }>
                            {((workTypeResult.new_suggestion.confidence || 0) * 100).toFixed(0)}%
                          </Badge>
                        </p>
                        {workTypeResult.new_suggestion.reasoning && (
                          <p>
                            <span className="text-muted-foreground">推理:</span>{' '}
                            <span className="text-muted-foreground">{workTypeResult.new_suggestion.reasoning}</span>
                          </p>
                        )}
                      </div>
                      {workTypeResult.suggestion_id ? (
                        <div className="mt-3 p-2 bg-green-100 rounded text-sm text-green-800">
                          <Check className="size-4 inline mr-1" /> 已创建审批请求，请前往「工作类型管理」页面审批
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
              <div className="text-xs text-muted-foreground pt-2 border-t">
                <span>模型: {workTypeResult.llm_model || '-'}</span>
              </div>

              {/* 操作按钮 */}
              <div className="flex justify-end space-x-3 pt-4 border-t">
                {workTypeResult.suggestion_id && (
                  <Button
                    variant="outline"
                    asChild
                    className="border-orange-300 text-orange-700 hover:bg-orange-50"
                  >
                    <a href="/admin/work-types">
                      前往审批
                    </a>
                  </Button>
                )}
                <Button
                  className="bg-orange-600 hover:bg-orange-700"
                  onClick={() => {
                    setShowWorkTypeModal(false);
                    setWorkTypeResult(null);
                    setAnalyzingEmailId(null);
                  }}
                >
                  关闭
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
