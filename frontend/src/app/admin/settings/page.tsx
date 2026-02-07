'use client';

import { useState, useEffect } from 'react';
import {
  emailAccountsApi,
  EmailAccount,
  EmailAccountCreate,
  EmailAccountUpdate,
  EmailAccountTestResult,
  ossApi,
  OSSConfig,
  OSSConfigUpdate,
  OSSTestResult,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { LoadingSpinner, PageLoading } from '@/components/LoadingSpinner';
import { Mail, Cloud, Check, AlertTriangle, X, Plus, Download, Pencil, Star, Trash2, FlaskConical } from 'lucide-react';

// 用途选项
const PURPOSE_OPTIONS = [
  { value: 'sales', label: '销售/询价' },
  { value: 'support', label: '客服/投诉' },
  { value: 'notification', label: '系统通知' },
  { value: 'general', label: '通用' },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="email">
        <TabsList variant="line">
          <TabsTrigger value="email">
            <Mail className="size-4 mr-1" />
            邮箱管理
          </TabsTrigger>
          <TabsTrigger value="oss">
            <Cloud className="size-4 mr-1" />
            OSS 存储
          </TabsTrigger>
        </TabsList>

        <TabsContent value="email">
          <EmailAccountsTab />
        </TabsContent>
        <TabsContent value="oss">
          <OSSConfigTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ==================== OSS 配置 Tab ====================
function OSSConfigTab() {
  const [config, setConfig] = useState<OSSConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [testResult, setTestResult] = useState<OSSTestResult | null>(null);
  const [isEditing, setIsEditing] = useState(false);  // 编辑模式

  // 表单状态
  const [formData, setFormData] = useState<OSSConfigUpdate>({
    endpoint: '',
    bucket: '',
    access_key_id: '',
    access_key_secret: '',
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await ossApi.getConfig();
      setConfig(data);
      // 预填已有配置
      setFormData({
        endpoint: data.endpoint || '',
        bucket: data.bucket || '',
        access_key_id: '',  // 密钥不回填
        access_key_secret: '',
      });
      // 如果未配置，自动进入编辑模式
      if (!data.configured) {
        setIsEditing(true);
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '加载配置失败' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      // 只提交非空字段
      const updateData: OSSConfigUpdate = {};

      // 清理 endpoint：移除 https:// 前缀，去除重复域名
      if (formData.endpoint) {
        let cleanedEndpoint = formData.endpoint
          .replace(/^https?:\/\//, '')  // 移除 http:// 或 https://
          .trim();

        // 检测并修复重复的域名（如 oss-cn-hangzhou.aliyuncs.comoss-cn-guangzhou.aliyuncs.com）
        const domainPattern = /^([a-z0-9-]+\.aliyuncs\.com)/;
        const match = cleanedEndpoint.match(domainPattern);
        if (match) {
          cleanedEndpoint = match[1];
        }

        updateData.endpoint = cleanedEndpoint;
      }

      if (formData.bucket) updateData.bucket = formData.bucket.trim();
      if (formData.access_key_id) updateData.access_key_id = formData.access_key_id.trim();
      if (formData.access_key_secret) updateData.access_key_secret = formData.access_key_secret.trim();

      await ossApi.updateConfig(updateData);
      setMessage({ type: 'success', text: '配置已保存' });
      // 清空密钥输入
      setFormData(prev => ({ ...prev, access_key_id: '', access_key_secret: '' }));
      await loadConfig();
      setIsEditing(false);  // 保存后退出编辑模式
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await ossApi.testConnection();
      setTestResult(result);

      // 如果测试失败，同时在消息区域显示错误（方便用户看到详细信息）
      if (!result.success) {
        setMessage({
          type: 'error',
          text: `连接失败: ${result.error}`,
        });
      }
    } catch (error: any) {
      const errorMessage = error.message || '测试失败';
      setTestResult({
        success: false,
        error: errorMessage,
      });
      setMessage({
        type: 'error',
        text: errorMessage,
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">OSS 存储配置</h1>
        <p className="mt-1 text-sm text-muted-foreground">配置阿里云 OSS 对象存储，用于保存邮件附件等文件</p>
      </div>

      {/* 提示消息 */}
      {message && (
        <div
          className={`p-4 rounded-md ${
            message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 配置状态 */}
      <Card className="p-0">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-medium text-foreground">配置信息</h2>
            <div className="flex items-center space-x-3">
              {config?.configured ? (
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  <Check className="size-3 mr-1" /> 已配置
                </Badge>
              ) : (
                <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">
                  <AlertTriangle className="size-3 mr-1" /> 未配置
                </Badge>
              )}
              {config?.configured && !isEditing && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTest}
                    disabled={testing}
                  >
                    <FlaskConical className="size-4" />
                    {testing ? '测试中...' : '测试连接'}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => setIsEditing(true)}
                  >
                    <Pencil className="size-4" />
                    编辑配置
                  </Button>
                </>
              )}
            </div>
          </div>

          {config?.configured && !isEditing && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Endpoint:</span>
                <span className="ml-2 text-foreground font-mono">{config.endpoint}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Bucket:</span>
                <span className="ml-2 text-foreground">{config.bucket}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Access Key ID:</span>
                <span className="ml-2 text-foreground">{config.access_key_id_preview}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Access Key Secret:</span>
                <span className="ml-2 text-foreground">{config.access_key_secret_configured ? '********' : '未设置'}</span>
              </div>
            </div>
          )}

          {(!config?.configured || isEditing) && (
            <div>
              <p className="text-sm text-muted-foreground mb-6">
                {config?.configured
                  ? '只需填写要修改的字段，留空的字段保持不变'
                  : '请填写阿里云 OSS 配置信息'}
              </p>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Label>
                    Endpoint（区域节点） {!config?.configured && '*'}
                  </Label>
                  <Input
                    type="text"
                    value={formData.endpoint}
                    onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
                    placeholder="oss-cn-guangzhou.aliyuncs.com"
                    className="mt-1 font-mono text-xs"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    只填写区域节点，<strong>不要</strong>包含 Bucket 名称<br/>
                    <span className="text-green-600">正确：oss-cn-guangzhou.aliyuncs.com</span><br/>
                    <span className="text-red-600">错误：concordai.oss-cn-guangzhou.aliyuncs.com</span>
                  </p>
                </div>
                <div>
                  <Label>
                    Bucket（存储桶名称） {!config?.configured && '*'}
                  </Label>
                  <Input
                    type="text"
                    value={formData.bucket}
                    onChange={(e) => setFormData({ ...formData, bucket: e.target.value })}
                    placeholder="concordai"
                    className="mt-1"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    只填写 Bucket 名称，不要包含域名后缀
                  </p>
                </div>
                <div>
                  <Label>
                    Access Key ID {!config?.configured && '*'}
                    {config?.configured && <span className="text-muted-foreground font-normal">（留空不修改）</span>}
                  </Label>
                  <Input
                    type="text"
                    value={formData.access_key_id}
                    onChange={(e) => setFormData({ ...formData, access_key_id: e.target.value })}
                    placeholder={config?.access_key_id_preview || 'LTAI...'}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>
                    Access Key Secret {!config?.configured && '*'}
                    {config?.configured && <span className="text-muted-foreground font-normal">（留空不修改）</span>}
                  </Label>
                  <Input
                    type="password"
                    value={formData.access_key_secret}
                    onChange={(e) => setFormData({ ...formData, access_key_secret: e.target.value })}
                    placeholder="********"
                    className="mt-1"
                  />
                </div>
              </div>

              <div className="mt-6 flex items-center space-x-4">
                <Button
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存配置'}
                </Button>
                {config?.configured && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsEditing(false);
                      // 重置表单
                      setFormData({
                        endpoint: config.endpoint || '',
                        bucket: config.bucket || '',
                        access_key_id: '',
                        access_key_secret: '',
                      });
                    }}
                  >
                    取消
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 测试结果 */}
      {testResult && (
        <div className={`p-4 rounded-lg ${testResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex items-center">
            {testResult.success ? (
              <Check className="size-5 mr-2 text-green-500" />
            ) : (
              <X className="size-5 mr-2 text-red-500" />
            )}
            <span className={`font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
              {testResult.success ? '连接成功' : '连接失败'}
            </span>
          </div>
          <p className={`mt-1 text-sm ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
            {testResult.message || testResult.error}
          </p>
          {testResult.success && testResult.bucket && (
            <p className="mt-1 text-sm text-green-700">
              Bucket: {testResult.bucket} @ {testResult.endpoint}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ==================== 邮箱管理 Tab ====================
function EmailAccountsTab() {
  const confirm = useConfirm();
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 模态框状态
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<EmailAccount | null>(null);
  const [saving, setSaving] = useState(false);

  // 测试结果模态框
  const [showTestModal, setShowTestModal] = useState(false);
  const [testResult, setTestResult] = useState<EmailAccountTestResult | null>(null);
  const [testing, setTesting] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState<EmailAccountCreate>({
    name: '',
    purpose: 'general',
    description: '',
    smtp_host: '',
    smtp_port: 465,
    smtp_user: '',
    smtp_password: '',
    smtp_use_tls: true,
    imap_host: '',
    imap_port: 993,
    imap_user: '',
    imap_password: '',
    imap_use_ssl: true,
    imap_folder: 'INBOX',
    imap_mark_as_read: false,
    imap_sync_days: undefined,  // undefined 表示同步全部历史邮件
    imap_unseen_only: false,    // 同步所有邮件（包括已读）
    imap_fetch_limit: 50,
    is_default: false,
  });

  // 加载账户列表
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setLoading(true);
    try {
      const data = await emailAccountsApi.list();
      setAccounts(data.items);
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '加载失败' });
    } finally {
      setLoading(false);
    }
  };

  // 打开新增模态框
  const handleAdd = () => {
    setEditingAccount(null);
    setFormData({
      name: '',
      purpose: 'general',
      description: '',
      smtp_host: '',
      smtp_port: 465,
      smtp_user: '',
      smtp_password: '',
      smtp_use_tls: true,
      imap_host: '',
      imap_port: 993,
      imap_user: '',
      imap_password: '',
      imap_use_ssl: true,
      is_default: false,
    });
    setShowModal(true);
  };

  // 打开编辑模态框
  const handleEdit = (account: EmailAccount) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      purpose: account.purpose,
      description: account.description || '',
      smtp_host: account.smtp_host,
      smtp_port: account.smtp_port,
      smtp_user: account.smtp_user,
      smtp_password: '',
      smtp_use_tls: account.smtp_use_tls,
      imap_host: account.imap_host || '',
      imap_port: account.imap_port,
      imap_user: account.imap_user || '',
      imap_password: '',
      imap_use_ssl: account.imap_use_ssl,
      is_default: account.is_default,
    });
    setShowModal(true);
  };

  // 保存（新增或编辑）
  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      if (editingAccount) {
        // 编辑
        const updateData: EmailAccountUpdate = { ...formData };
        // 如果密码为空，不更新密码
        if (!updateData.smtp_password) delete updateData.smtp_password;
        if (!updateData.imap_password) delete updateData.imap_password;
        await emailAccountsApi.update(editingAccount.id, updateData);
        setMessage({ type: 'success', text: '更新成功' });
      } else {
        // 新增
        await emailAccountsApi.create(formData);
        setMessage({ type: 'success', text: '创建成功' });
      }
      setShowModal(false);
      await loadAccounts();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  // 删除
  const handleDelete = async (account: EmailAccount) => {
    const confirmed = await confirm({
      title: '确认删除',
      description: `确定要删除邮箱账户 "${account.name}" 吗？`,
      variant: 'destructive',
      confirmText: '删除',
    });
    if (!confirmed) return;

    try {
      await emailAccountsApi.delete(account.id);
      setMessage({ type: 'success', text: '删除成功' });
      await loadAccounts();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '删除失败' });
    }
  };

  // 设为默认
  const handleSetDefault = async (account: EmailAccount) => {
    try {
      await emailAccountsApi.setDefault(account.id);
      setMessage({ type: 'success', text: `已将 "${account.name}" 设为默认邮箱` });
      await loadAccounts();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '操作失败' });
    }
  };

  // 测试连接
  const handleTest = async (account: EmailAccount) => {
    setTesting(true);
    setTestResult(null);
    setShowTestModal(true);
    try {
      const result = await emailAccountsApi.test(account.id);
      setTestResult(result);
    } catch (error: any) {
      setTestResult({
        smtp_success: false,
        smtp_message: error.message || '测试失败',
        imap_success: false,
        imap_message: error.message || '测试失败',
      });
    } finally {
      setTesting(false);
    }
  };

  // 立即拉取邮件
  const [fetching, setFetching] = useState(false);
  const handleFetchEmails = async (account: EmailAccount) => {
    if (!account.imap_configured) {
      setMessage({ type: 'error', text: '该邮箱未配置 IMAP，无法拉取邮件' });
      return;
    }

    const confirmed = await confirm({
      title: '拉取邮件',
      description: `确定要立即拉取「${account.name}」的邮件吗？\n\n这将从邮箱服务器拉取最多 50 封邮件并保存到数据库。`,
    });

    if (!confirmed) return;

    setFetching(true);
    setMessage(null);
    try {
      const result = await emailAccountsApi.fetch(account.id, 50);
      setMessage({
        type: 'success',
        text: `拉取完成！发现 ${result.emails_found} 封邮件，成功保存 ${result.emails_saved} 封（耗时 ${result.duration_seconds}秒）`,
      });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '拉取失败' });
    } finally {
      setFetching(false);
    }
  };

  // 获取用途标签
  const getPurposeLabel = (purpose: string) => {
    const option = PURPOSE_OPTIONS.find(o => o.value === purpose);
    return option?.label || purpose;
  };

  if (loading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">邮箱管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理系统邮箱账户，支持多邮箱配置</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="size-4" />
          新增邮箱
        </Button>
      </div>

      {/* 提示消息 */}
      {message && (
        <div
          className={`p-4 rounded-md ${
            message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 邮箱列表 */}
      {accounts.length === 0 ? (
        <Card className="p-8 text-center">
          <CardContent>
            <p className="text-muted-foreground">暂无邮箱账户</p>
            <Button
              variant="link"
              onClick={handleAdd}
              className="mt-4"
            >
              点击添加第一个邮箱
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-6">账户名称</TableHead>
                <TableHead className="px-6">用途</TableHead>
                <TableHead className="px-6">SMTP</TableHead>
                <TableHead className="px-6">IMAP</TableHead>
                <TableHead className="px-6">状态</TableHead>
                <TableHead className="px-6 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell className="px-6 py-4">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-foreground">
                          {account.name}
                          {account.is_default && (
                            <Badge className="ml-2 bg-blue-100 text-blue-800 border-blue-200">
                              默认
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground">{account.smtp_user}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <Badge variant="secondary">
                      {getPurposeLabel(account.purpose)}
                    </Badge>
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {account.smtp_configured ? (
                      <span className="text-green-600">
                        <Check className="size-3 inline mr-1" />
                        {account.smtp_host}:{account.smtp_port}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">未配置</span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                    {account.imap_configured ? (
                      <span className="text-green-600">
                        <Check className="size-3 inline mr-1" />
                        {account.imap_host}:{account.imap_port}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">未配置</span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    {account.is_active ? (
                      <Badge className="bg-green-100 text-green-800 border-green-200">
                        启用
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        禁用
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-right text-sm font-medium space-x-2">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleTest(account)}
                    >
                      测试
                    </Button>
                    {account.imap_configured && (
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleFetchEmails(account)}
                        disabled={fetching}
                        title="立即从邮箱服务器拉取邮件"
                        className="text-purple-600 hover:text-purple-900"
                      >
                        <Download className="size-3" />
                        {fetching ? '拉取中...' : '拉取'}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleEdit(account)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      编辑
                    </Button>
                    {!account.is_default && (
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleSetDefault(account)}
                        className="text-green-600 hover:text-green-900"
                      >
                        设为默认
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleDelete(account)}
                      className="text-red-600 hover:text-red-900"
                    >
                      删除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* 新增/编辑模态框 */}
      <Dialog open={showModal} onOpenChange={(open) => !open && setShowModal(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{editingAccount ? '编辑邮箱账户' : '新增邮箱账户'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* 基本信息 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>账户名称 *</Label>
                <Input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="如：销售邮箱"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>用途 *</Label>
                <select
                  value={formData.purpose}
                  onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {PURPOSE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <Label>描述</Label>
              <Input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="可选"
                className="mt-1"
              />
            </div>

            {/* SMTP 配置 */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-foreground mb-3">SMTP 发件配置</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>服务器地址 *</Label>
                  <Input
                    type="text"
                    value={formData.smtp_host}
                    onChange={(e) => setFormData({ ...formData, smtp_host: e.target.value })}
                    placeholder="smtp.example.com"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>端口</Label>
                  <Input
                    type="number"
                    value={formData.smtp_port}
                    onChange={(e) => setFormData({ ...formData, smtp_port: parseInt(e.target.value) })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>用户名/邮箱 *</Label>
                  <Input
                    type="email"
                    value={formData.smtp_user}
                    onChange={(e) => setFormData({ ...formData, smtp_user: e.target.value })}
                    placeholder="your@email.com"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>
                    密码/授权码 {editingAccount ? '(留空不修改)' : '*'}
                  </Label>
                  <Input
                    type="password"
                    value={formData.smtp_password}
                    onChange={(e) => setFormData({ ...formData, smtp_password: e.target.value })}
                    className="mt-1"
                  />
                </div>
              </div>
              <div className="mt-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.smtp_use_tls}
                    onChange={(e) => setFormData({ ...formData, smtp_use_tls: e.target.checked })}
                    className="rounded border-input text-primary focus:ring-ring"
                  />
                  <span className="ml-2 text-sm text-muted-foreground">使用 TLS</span>
                </label>
              </div>
            </div>

            {/* IMAP 配置 */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-foreground mb-3">IMAP 收件配置（可选）</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>服务器地址</Label>
                  <Input
                    type="text"
                    value={formData.imap_host}
                    onChange={(e) => setFormData({ ...formData, imap_host: e.target.value })}
                    placeholder="imap.example.com"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>端口</Label>
                  <Input
                    type="number"
                    value={formData.imap_port}
                    onChange={(e) => setFormData({ ...formData, imap_port: parseInt(e.target.value) })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>用户名/邮箱</Label>
                  <Input
                    type="email"
                    value={formData.imap_user}
                    onChange={(e) => setFormData({ ...formData, imap_user: e.target.value })}
                    placeholder="your@email.com"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>
                    密码/授权码 {editingAccount ? '(留空不修改)' : ''}
                  </Label>
                  <Input
                    type="password"
                    value={formData.imap_password}
                    onChange={(e) => setFormData({ ...formData, imap_password: e.target.value })}
                    className="mt-1"
                  />
                </div>
              </div>
              <div className="mt-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.imap_use_ssl}
                    onChange={(e) => setFormData({ ...formData, imap_use_ssl: e.target.checked })}
                    className="rounded border-input text-primary focus:ring-ring"
                  />
                  <span className="ml-2 text-sm text-muted-foreground">使用 SSL</span>
                </label>
              </div>

              {/* IMAP 同步策略配置 */}
              <div className="mt-4 p-3 bg-muted rounded-md">
                <h5 className="text-xs font-medium text-foreground mb-3">
                  <Mail className="size-3 inline mr-1" /> 邮件同步策略
                </h5>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-xs">
                      同步天数
                      <span className="text-muted-foreground ml-1" title="留空表示同步全部历史邮件">i</span>
                    </Label>
                    <Input
                      type="number"
                      value={formData.imap_sync_days || ''}
                      onChange={(e) => setFormData({ ...formData, imap_sync_days: e.target.value ? parseInt(e.target.value) : undefined })}
                      placeholder="留空=全部"
                      min="1"
                      className="mt-1"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">首次拉取 N 天内邮件</p>
                  </div>
                  <div>
                    <Label className="text-xs">每次拉取数量</Label>
                    <Input
                      type="number"
                      value={formData.imap_fetch_limit}
                      onChange={(e) => setFormData({ ...formData, imap_fetch_limit: parseInt(e.target.value) || 50 })}
                      min="1"
                      max="500"
                      className="mt-1"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">单次最多拉取邮件数</p>
                  </div>
                  <div>
                    <Label className="text-xs">邮件文件夹</Label>
                    <Input
                      type="text"
                      value={formData.imap_folder}
                      onChange={(e) => setFormData({ ...formData, imap_folder: e.target.value })}
                      placeholder="INBOX"
                      className="mt-1"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">监控的邮箱文件夹</p>
                  </div>
                </div>
                <div className="mt-3 space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.imap_unseen_only}
                      onChange={(e) => setFormData({ ...formData, imap_unseen_only: e.target.checked })}
                      className="rounded border-input text-primary focus:ring-ring"
                    />
                    <span className="ml-2 text-xs text-muted-foreground">只同步未读邮件（默认同步全部）</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.imap_mark_as_read}
                      onChange={(e) => setFormData({ ...formData, imap_mark_as_read: e.target.checked })}
                      className="rounded border-input text-primary focus:ring-ring"
                    />
                    <span className="ml-2 text-xs text-muted-foreground">拉取后标记为已读</span>
                  </label>
                </div>
              </div>
            </div>

            {/* 设为默认 */}
            {!editingAccount && (
              <div className="border-t pt-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="rounded border-input text-primary focus:ring-ring"
                  />
                  <span className="ml-2 text-sm text-muted-foreground">设为默认邮箱</span>
                </label>
              </div>
            )}

            {/* 按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setShowModal(false)}
              >
                取消
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving || !formData.name || !formData.smtp_host || !formData.smtp_user || (!editingAccount && !formData.smtp_password)}
              >
                {saving ? '保存中...' : '保存'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 测试结果模态框 */}
      <Dialog open={showTestModal} onOpenChange={(open) => !open && setShowTestModal(false)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>连接测试结果</DialogTitle>
          </DialogHeader>
          {testing ? (
            <div className="py-8 text-center">
              <LoadingSpinner text="测试中..." />
            </div>
          ) : testResult ? (
            <div className="space-y-4">
              {/* SMTP 结果 */}
              <div className="p-4 rounded-lg bg-muted">
                <div className="flex items-center">
                  {testResult.smtp_success ? (
                    <Check className="size-5 mr-2 text-green-500" />
                  ) : (
                    <X className="size-5 mr-2 text-red-500" />
                  )}
                  <span className="font-medium">SMTP 发件服务器</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{testResult.smtp_message || '未测试'}</p>
              </div>

              {/* IMAP 结果 */}
              <div className="p-4 rounded-lg bg-muted">
                <div className="flex items-center">
                  {testResult.imap_success ? (
                    <Check className="size-5 mr-2 text-green-500" />
                  ) : testResult.imap_success === null ? (
                    <span className="size-5 mr-2 text-muted-foreground text-xl leading-none">-</span>
                  ) : (
                    <X className="size-5 mr-2 text-red-500" />
                  )}
                  <span className="font-medium">IMAP 收件服务器</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{testResult.imap_message || '未配置'}</p>
              </div>

              <div className="pt-4 border-t">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setShowTestModal(false)}
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
