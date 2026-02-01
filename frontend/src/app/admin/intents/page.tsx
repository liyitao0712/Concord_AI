// src/app/admin/intents/page.tsx
// 意图管理页面
//
// 功能说明：
// 1. 意图列表展示
// 2. 创建/编辑/删除意图
// 3. 测试路由分类
// 4. 意图建议审批

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  intentsApi,
  IntentItem,
  IntentCreate,
  IntentSuggestionItem,
  RouteTestResponse,
} from '@/lib/api';

// ==================== 工具函数 ====================

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
        <div
          className="fixed inset-0 bg-black opacity-50"
          onClick={onClose}
        />
        <div className={`relative bg-white rounded-lg shadow-xl ${wide ? 'max-w-4xl' : 'max-w-2xl'} w-full p-6 max-h-[90vh] overflow-y-auto`}>
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

// ==================== Tab 组件 ====================

function Tabs({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: { id: string; label: string; count?: number }[];
  activeTab: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}

// ==================== 主页面 ====================

export default function IntentsPage() {
  // Tab 状态
  const [activeTab, setActiveTab] = useState<'intents' | 'suggestions' | 'test'>('intents');

  // 意图列表状态
  const [intents, setIntents] = useState<IntentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 建议列表状态
  const [suggestions, setSuggestions] = useState<IntentSuggestionItem[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);

  // 创建/编辑弹窗
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingIntent, setEditingIntent] = useState<IntentItem | null>(null);
  const [formData, setFormData] = useState<Partial<IntentCreate>>({});
  const [saving, setSaving] = useState(false);

  // 测试状态
  const [testContent, setTestContent] = useState('');
  const [testSource, setTestSource] = useState('email');
  const [testSubject, setTestSubject] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<RouteTestResponse | null>(null);

  // 加载意图列表
  const loadIntents = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await intentsApi.list();
      setIntents(response.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    }

    setLoading(false);
  }, []);

  // 加载建议列表
  const loadSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);

    try {
      const response = await intentsApi.listSuggestions({ status: 'pending' });
      setSuggestions(response.items);
    } catch (e) {
      console.error('加载建议失败:', e);
    }

    setSuggestionsLoading(false);
  }, []);

  useEffect(() => {
    loadIntents();
    loadSuggestions();
  }, [loadIntents, loadSuggestions]);

  // 打开创建弹窗
  const handleCreate = () => {
    setEditingIntent(null);
    setFormData({
      name: '',
      label: '',
      description: '',
      examples: [],
      keywords: [],
      default_handler: 'agent',
      handler_config: {},
      priority: 0,
      is_active: true,
    });
    setShowEditModal(true);
  };

  // 打开编辑弹窗
  const handleEdit = (intent: IntentItem) => {
    setEditingIntent(intent);
    setFormData({
      label: intent.label,
      description: intent.description,
      examples: intent.examples,
      keywords: intent.keywords,
      default_handler: intent.default_handler,
      handler_config: intent.handler_config,
      escalation_rules: intent.escalation_rules || undefined,
      escalation_workflow: intent.escalation_workflow || undefined,
      priority: intent.priority,
      is_active: intent.is_active,
    });
    setShowEditModal(true);
  };

  // 保存意图
  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingIntent) {
        await intentsApi.update(editingIntent.id, formData);
      } else {
        await intentsApi.create(formData as IntentCreate);
      }
      setShowEditModal(false);
      loadIntents();
      alert('保存成功');
    } catch (e) {
      alert(e instanceof Error ? e.message : '保存失败');
    }
    setSaving(false);
  };

  // 删除意图
  const handleDelete = async (intent: IntentItem) => {
    if (!confirm(`确定要删除意图 "${intent.label}" 吗？`)) return;

    try {
      await intentsApi.delete(intent.id);
      loadIntents();
      alert('删除成功');
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  // 切换状态
  const handleToggleActive = async (intent: IntentItem) => {
    try {
      await intentsApi.update(intent.id, { is_active: !intent.is_active });
      loadIntents();
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 测试路由
  const handleTest = async () => {
    if (!testContent.trim()) {
      alert('请输入测试内容');
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const result = await intentsApi.test({
        content: testContent,
        source: testSource,
        subject: testSubject || undefined,
      });
      setTestResult(result);
    } catch (e) {
      alert(e instanceof Error ? e.message : '测试失败');
    }

    setTesting(false);
  };

  // 批准建议
  const handleApproveSuggestion = async (suggestion: IntentSuggestionItem) => {
    if (!confirm(`确定要批准意图建议 "${suggestion.suggested_label}" 吗？`)) return;

    try {
      await intentsApi.approveSuggestion(suggestion.id);
      loadSuggestions();
      loadIntents();
      alert('已批准');
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 拒绝建议
  const handleRejectSuggestion = async (suggestion: IntentSuggestionItem) => {
    const note = prompt('请输入拒绝原因（可选）:');
    if (note === null) return;

    try {
      await intentsApi.rejectSuggestion(suggestion.id, note || undefined);
      loadSuggestions();
      alert('已拒绝');
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 处理器类型颜色
  const getHandlerColor = (handler: string) => {
    return handler === 'workflow'
      ? 'bg-purple-100 text-purple-800'
      : 'bg-blue-100 text-blue-800';
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">意图管理</h1>
          <p className="mt-1 text-sm text-gray-500">管理 AI 消息分类意图，支持动态增删改</p>
        </div>
        {activeTab === 'intents' && (
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            新建意图
          </button>
        )}
      </div>

      {/* Tab 切换 */}
      <Tabs
        tabs={[
          { id: 'intents', label: '意图列表', count: intents.length },
          { id: 'suggestions', label: '待审批建议', count: suggestions.length },
          { id: 'test', label: '测试路由' },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as 'intents' | 'suggestions' | 'test')}
      />

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 意图列表 Tab */}
      {activeTab === 'intents' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  描述
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  处理器
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  优先级
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  来源
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    加载中...
                  </td>
                </tr>
              ) : intents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    暂无意图
                  </td>
                </tr>
              ) : (
                intents.map((intent) => (
                  <tr key={intent.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {intent.label}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {intent.name}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 max-w-xs truncate">
                        {intent.description}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded ${getHandlerColor(intent.default_handler)}`}>
                        {intent.default_handler}
                      </span>
                      {intent.escalation_workflow && (
                        <span className="ml-1 text-xs text-gray-400">
                          (可升级)
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {intent.priority}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleToggleActive(intent)}
                        className={`px-2 py-1 text-xs rounded ${
                          intent.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {intent.is_active ? '启用' : '禁用'}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {intent.created_by === 'system' ? (
                        <span className="text-blue-600">系统</span>
                      ) : intent.created_by === 'ai' ? (
                        <span className="text-purple-600">AI</span>
                      ) : (
                        <span className="text-gray-600">管理员</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                      <button
                        onClick={() => handleEdit(intent)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        编辑
                      </button>
                      {intent.created_by !== 'system' && (
                        <button
                          onClick={() => handleDelete(intent)}
                          className="text-red-600 hover:text-red-900"
                        >
                          删除
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 建议列表 Tab */}
      {activeTab === 'suggestions' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  建议名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  描述
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  触发消息
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  来源
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  时间
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {suggestionsLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    加载中...
                  </td>
                </tr>
              ) : suggestions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    暂无待审批建议
                  </td>
                </tr>
              ) : (
                suggestions.map((suggestion) => (
                  <tr key={suggestion.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {suggestion.suggested_label}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {suggestion.suggested_name}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 max-w-xs truncate">
                        {suggestion.suggested_description}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 max-w-xs truncate">
                        {suggestion.trigger_message}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-800">
                        {suggestion.trigger_source}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTime(suggestion.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                      <button
                        onClick={() => handleApproveSuggestion(suggestion)}
                        className="text-green-600 hover:text-green-900"
                      >
                        批准
                      </button>
                      <button
                        onClick={() => handleRejectSuggestion(suggestion)}
                        className="text-red-600 hover:text-red-900"
                      >
                        拒绝
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 测试路由 Tab */}
      {activeTab === 'test' && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            {/* 来源选择 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                消息来源
              </label>
              <select
                value={testSource}
                onChange={(e) => setTestSource(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="email">邮件</option>
                <option value="feishu">飞书</option>
                <option value="web">Web</option>
              </select>
            </div>

            {/* 主题（邮件） */}
            {testSource === 'email' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  邮件主题（可选）
                </label>
                <input
                  type="text"
                  value={testSubject}
                  onChange={(e) => setTestSubject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="输入邮件主题..."
                />
              </div>
            )}
          </div>

          {/* 内容输入 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              消息内容
            </label>
            <textarea
              value={testContent}
              onChange={(e) => setTestContent(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="输入要测试的消息内容..."
            />
          </div>

          {/* 测试按钮 */}
          <div>
            <button
              onClick={handleTest}
              disabled={testing || !testContent.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {testing ? '分析中...' : '测试路由'}
            </button>
          </div>

          {/* 测试结果 */}
          {testResult && (
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">分析结果</h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500">匹配意图</div>
                  <div className="text-lg font-medium text-gray-900">
                    {testResult.intent_label}
                    <span className="ml-2 text-sm font-mono text-gray-500">
                      ({testResult.intent})
                    </span>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500">置信度</div>
                  <div className="text-lg font-medium text-gray-900">
                    {(testResult.confidence * 100).toFixed(0)}%
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500">处理方式</div>
                  <div className="text-lg font-medium text-gray-900">
                    <span className={`px-2 py-1 text-sm rounded ${getHandlerColor(testResult.action)}`}>
                      {testResult.action}
                    </span>
                    {testResult.workflow_name && (
                      <span className="ml-2 text-sm text-gray-500">
                        ({testResult.workflow_name})
                      </span>
                    )}
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500">需要升级</div>
                  <div className="text-lg font-medium text-gray-900">
                    {testResult.needs_escalation ? (
                      <span className="text-orange-600">
                        是 - {testResult.escalation_reason}
                      </span>
                    ) : (
                      <span className="text-green-600">否</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 bg-gray-50 p-4 rounded-md">
                <div className="text-sm text-gray-500 mb-1">分析理由</div>
                <div className="text-sm text-gray-900">
                  {testResult.reasoning}
                </div>
              </div>

              {testResult.new_suggestion && (
                <div className="mt-4 bg-yellow-50 border border-yellow-200 p-4 rounded-md">
                  <div className="text-sm font-medium text-yellow-800 mb-2">
                    AI 建议创建新意图
                  </div>
                  <div className="text-sm text-yellow-700">
                    <div>名称: {testResult.new_suggestion.label} ({testResult.new_suggestion.name})</div>
                    <div>描述: {testResult.new_suggestion.description}</div>
                    <div>处理器: {testResult.new_suggestion.suggested_handler}</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 编辑弹窗 */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title={editingIntent ? `编辑意图: ${editingIntent.label}` : '新建意图'}
        wide
      >
        <div className="space-y-4">
          {/* 名称（仅创建时可编辑） */}
          {!editingIntent && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  英文标识 *
                </label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono"
                  placeholder="inquiry"
                />
                <p className="mt-1 text-xs text-gray-500">只能包含字母、数字、下划线</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  中文名称 *
                </label>
                <input
                  type="text"
                  value={formData.label || ''}
                  onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="询价"
                />
              </div>
            </div>
          )}

          {/* 中文名称（编辑时） */}
          {editingIntent && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                中文名称 *
              </label>
              <input
                type="text"
                value={formData.label || ''}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="询价"
              />
            </div>
          )}

          {/* 描述 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              描述 *
            </label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="给 AI 的描述，帮助它理解什么消息属于这个意图..."
            />
          </div>

          {/* 示例 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              示例消息（每行一个）
            </label>
            <textarea
              value={(formData.examples || []).join('\n')}
              onChange={(e) => setFormData({
                ...formData,
                examples: e.target.value.split('\n').filter(s => s.trim()),
              })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="请问这个产品多少钱？&#10;能给个报价吗？&#10;价格是多少？"
            />
          </div>

          {/* 关键词 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              关键词（逗号分隔）
            </label>
            <input
              type="text"
              value={(formData.keywords || []).join(', ')}
              onChange={(e) => setFormData({
                ...formData,
                keywords: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="价格, 报价, 多少钱"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* 处理器类型 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                默认处理器
              </label>
              <select
                value={formData.default_handler || 'agent'}
                onChange={(e) => setFormData({ ...formData, default_handler: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="agent">Agent（直接处理）</option>
                <option value="workflow">Workflow（需要审批）</option>
              </select>
            </div>

            {/* 优先级 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                优先级
              </label>
              <input
                type="number"
                value={formData.priority || 0}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">数字越大优先级越高</p>
            </div>
          </div>

          {/* 升级工作流 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              升级工作流（可选）
            </label>
            <input
              type="text"
              value={formData.escalation_workflow || ''}
              onChange={(e) => setFormData({ ...formData, escalation_workflow: e.target.value || undefined })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="QuoteApprovalWorkflow"
            />
            <p className="mt-1 text-xs text-gray-500">当满足升级条件时，使用此工作流</p>
          </div>

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              onClick={() => setShowEditModal(false)}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={
                saving ||
                !formData.label?.trim() ||
                !formData.description?.trim() ||
                (!editingIntent && !formData.name?.trim())
              }
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
