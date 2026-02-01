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
import Modal from '@/components/Modal';

// 用途选项
const PURPOSE_OPTIONS = [
  { value: 'sales', label: '销售/询价' },
  { value: 'support', label: '客服/投诉' },
  { value: 'notification', label: '系统通知' },
  { value: 'general', label: '通用' },
];

// Tab 配置
const TABS = [
  { id: 'email', label: '邮箱管理', icon: '📧' },
  { id: 'oss', label: 'OSS 存储', icon: '☁️' },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('email');

  return (
    <div className="space-y-6">
      {/* Tab 导航 */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab 内容 */}
      {activeTab === 'email' && <EmailAccountsTab />}
      {activeTab === 'oss' && <OSSConfigTab />}
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
      if (formData.endpoint) updateData.endpoint = formData.endpoint;
      if (formData.bucket) updateData.bucket = formData.bucket;
      if (formData.access_key_id) updateData.access_key_id = formData.access_key_id;
      if (formData.access_key_secret) updateData.access_key_secret = formData.access_key_secret;

      await ossApi.updateConfig(updateData);
      setMessage({ type: 'success', text: '配置已保存' });
      // 清空密钥输入
      setFormData(prev => ({ ...prev, access_key_id: '', access_key_secret: '' }));
      await loadConfig();
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
    } catch (error: any) {
      setTestResult({
        success: false,
        error: error.message || '测试失败',
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">OSS 存储配置</h1>
        <p className="mt-1 text-sm text-gray-500">配置阿里云 OSS 对象存储，用于保存邮件附件等文件</p>
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
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium text-gray-900">当前状态</h2>
          {config?.configured ? (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              ✓ 已配置
            </span>
          ) : (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
              ⚠ 未配置
            </span>
          )}
        </div>

        {config?.configured && (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Endpoint:</span>
              <span className="ml-2 text-gray-900">{config.endpoint}</span>
            </div>
            <div>
              <span className="text-gray-500">Bucket:</span>
              <span className="ml-2 text-gray-900">{config.bucket}</span>
            </div>
            <div>
              <span className="text-gray-500">Access Key ID:</span>
              <span className="ml-2 text-gray-900">{config.access_key_id_preview}</span>
            </div>
            <div>
              <span className="text-gray-500">Access Key Secret:</span>
              <span className="ml-2 text-gray-900">{config.access_key_secret_configured ? '********' : '未设置'}</span>
            </div>
          </div>
        )}
      </div>

      {/* 配置表单 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          {config?.configured ? '修改配置' : '新增配置'}
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          {config?.configured
            ? '只需填写要修改的字段，留空的字段保持不变'
            : '请填写阿里云 OSS 配置信息'}
        </p>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Endpoint {!config?.configured && '*'}
            </label>
            <input
              type="text"
              value={formData.endpoint}
              onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
              placeholder="oss-cn-hangzhou.aliyuncs.com"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-400">不需要包含 https:// 前缀</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Bucket {!config?.configured && '*'}
            </label>
            <input
              type="text"
              value={formData.bucket}
              onChange={(e) => setFormData({ ...formData, bucket: e.target.value })}
              placeholder="your-bucket-name"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Access Key ID {!config?.configured && '*'}
              {config?.configured && <span className="text-gray-400 font-normal">（留空不修改）</span>}
            </label>
            <input
              type="text"
              value={formData.access_key_id}
              onChange={(e) => setFormData({ ...formData, access_key_id: e.target.value })}
              placeholder={config?.access_key_id_preview || 'LTAI...'}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Access Key Secret {!config?.configured && '*'}
              {config?.configured && <span className="text-gray-400 font-normal">（留空不修改）</span>}
            </label>
            <input
              type="password"
              value={formData.access_key_secret}
              onChange={(e) => setFormData({ ...formData, access_key_secret: e.target.value })}
              placeholder="********"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
        </div>

        <div className="mt-6 flex items-center space-x-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={handleTest}
            disabled={testing || !config?.configured}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            {testing ? '测试中...' : '测试连接'}
          </button>
        </div>
      </div>

      {/* 测试结果 */}
      {testResult && (
        <div className={`p-4 rounded-lg ${testResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex items-center">
            <span className={`text-xl mr-2 ${testResult.success ? 'text-green-500' : 'text-red-500'}`}>
              {testResult.success ? '✓' : '✗'}
            </span>
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
    if (!confirm(`确定要删除邮箱账户 "${account.name}" 吗？`)) return;

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

  // 获取用途标签
  const getPurposeLabel = (purpose: string) => {
    const option = PURPOSE_OPTIONS.find(o => o.value === purpose);
    return option?.label || purpose;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">邮箱管理</h1>
          <p className="mt-1 text-sm text-gray-500">管理系统邮箱账户，支持多邮箱配置</p>
        </div>
        <button
          onClick={handleAdd}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          + 新增邮箱
        </button>
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
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <p className="text-gray-500">暂无邮箱账户</p>
          <button
            onClick={handleAdd}
            className="mt-4 text-blue-600 hover:text-blue-500"
          >
            点击添加第一个邮箱
          </button>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  账户名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  用途
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SMTP
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  IMAP
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {accounts.map((account) => (
                <tr key={account.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {account.name}
                          {account.is_default && (
                            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                              默认
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">{account.smtp_user}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {getPurposeLabel(account.purpose)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {account.smtp_configured ? (
                      <span className="text-green-600">✓ {account.smtp_host}:{account.smtp_port}</span>
                    ) : (
                      <span className="text-gray-400">未配置</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {account.imap_configured ? (
                      <span className="text-green-600">✓ {account.imap_host}:{account.imap_port}</span>
                    ) : (
                      <span className="text-gray-400">未配置</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {account.is_active ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        启用
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        禁用
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleTest(account)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      测试
                    </button>
                    <button
                      onClick={() => handleEdit(account)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      编辑
                    </button>
                    {!account.is_default && (
                      <button
                        onClick={() => handleSetDefault(account)}
                        className="text-green-600 hover:text-green-900"
                      >
                        设为默认
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(account)}
                      className="text-red-600 hover:text-red-900"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 新增/编辑模态框 */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingAccount ? '编辑邮箱账户' : '新增邮箱账户'}
        size="lg"
      >
        <div className="space-y-4">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">账户名称 *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="如：销售邮箱"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">用途 *</label>
              <select
                value={formData.purpose}
                onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                {PURPOSE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">描述</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="可选"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>

          {/* SMTP 配置 */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">SMTP 发件配置</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">服务器地址 *</label>
                <input
                  type="text"
                  value={formData.smtp_host}
                  onChange={(e) => setFormData({ ...formData, smtp_host: e.target.value })}
                  placeholder="smtp.example.com"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">端口</label>
                <input
                  type="number"
                  value={formData.smtp_port}
                  onChange={(e) => setFormData({ ...formData, smtp_port: parseInt(e.target.value) })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">用户名/邮箱 *</label>
                <input
                  type="email"
                  value={formData.smtp_user}
                  onChange={(e) => setFormData({ ...formData, smtp_user: e.target.value })}
                  placeholder="your@email.com"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  密码/授权码 {editingAccount ? '(留空不修改)' : '*'}
                </label>
                <input
                  type="password"
                  value={formData.smtp_password}
                  onChange={(e) => setFormData({ ...formData, smtp_password: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
            <div className="mt-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.smtp_use_tls}
                  onChange={(e) => setFormData({ ...formData, smtp_use_tls: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-600">使用 TLS</span>
              </label>
            </div>
          </div>

          {/* IMAP 配置 */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">IMAP 收件配置（可选）</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">服务器地址</label>
                <input
                  type="text"
                  value={formData.imap_host}
                  onChange={(e) => setFormData({ ...formData, imap_host: e.target.value })}
                  placeholder="imap.example.com"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">端口</label>
                <input
                  type="number"
                  value={formData.imap_port}
                  onChange={(e) => setFormData({ ...formData, imap_port: parseInt(e.target.value) })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">用户名/邮箱</label>
                <input
                  type="email"
                  value={formData.imap_user}
                  onChange={(e) => setFormData({ ...formData, imap_user: e.target.value })}
                  placeholder="your@email.com"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  密码/授权码 {editingAccount ? '(留空不修改)' : ''}
                </label>
                <input
                  type="password"
                  value={formData.imap_password}
                  onChange={(e) => setFormData({ ...formData, imap_password: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
            <div className="mt-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.imap_use_ssl}
                  onChange={(e) => setFormData({ ...formData, imap_use_ssl: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-600">使用 SSL</span>
              </label>
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
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-600">设为默认邮箱</span>
              </label>
            </div>
          )}

          {/* 按钮 */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              onClick={() => setShowModal(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !formData.name || !formData.smtp_host || !formData.smtp_user || (!editingAccount && !formData.smtp_password)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </Modal>

      {/* 测试结果模态框 */}
      <Modal
        isOpen={showTestModal}
        onClose={() => setShowTestModal(false)}
        title="连接测试结果"
        size="sm"
      >
        {testing ? (
          <div className="py-8 text-center">
            <div className="text-gray-500">测试中...</div>
          </div>
        ) : testResult ? (
          <div className="space-y-4">
            {/* SMTP 结果 */}
            <div className="p-4 rounded-lg bg-gray-50">
              <div className="flex items-center">
                <span className={`text-xl mr-2 ${testResult.smtp_success ? 'text-green-500' : 'text-red-500'}`}>
                  {testResult.smtp_success ? '✓' : '✗'}
                </span>
                <span className="font-medium">SMTP 发件服务器</span>
              </div>
              <p className="mt-1 text-sm text-gray-600">{testResult.smtp_message || '未测试'}</p>
            </div>

            {/* IMAP 结果 */}
            <div className="p-4 rounded-lg bg-gray-50">
              <div className="flex items-center">
                <span className={`text-xl mr-2 ${testResult.imap_success ? 'text-green-500' : testResult.imap_success === null ? 'text-gray-400' : 'text-red-500'}`}>
                  {testResult.imap_success ? '✓' : testResult.imap_success === null ? '-' : '✗'}
                </span>
                <span className="font-medium">IMAP 收件服务器</span>
              </div>
              <p className="mt-1 text-sm text-gray-600">{testResult.imap_message || '未配置'}</p>
            </div>

            <div className="pt-4 border-t">
              <button
                onClick={() => setShowTestModal(false)}
                className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
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
