'use client';

import { useState, useEffect } from 'react';
import { llmModelsApi, type LLMModelConfig } from '@/lib/api';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface ProviderGroup {
  id: string;
  name: string;
  description: string;
  docsUrl: string;
  models: LLMModelConfig[];
}

export default function LLMConfigPage() {
  const [models, setModels] = useState<LLMModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 折叠/展开状态（默认全部收缩）
  const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({
    anthropic: false,
    openai: false,
    gemini: false,
    qwen: false,
    volcengine: false,
  });

  // 每个模型的 API Key 输入状态
  const [modelApiKeys, setModelApiKeys] = useState<Record<string, string>>({});

  // 操作状态
  const [savingModel, setSavingModel] = useState<string | null>(null);
  const [testingModel, setTestingModel] = useState<string | null>(null);

  // 新增模型弹窗
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    model_id: '',
    provider: 'anthropic',
    model_name: '',
    description: '',
    api_key: '',
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      console.log('[LLM Config] 开始加载模型列表...');
      const data = await llmModelsApi.list();
      console.log('[LLM Config] API 返回数据:', data);
      console.log('[LLM Config] items 数量:', data.items?.length || 0);
      setModels(data.items || []);
    } catch (error) {
      console.error('[LLM Config] 加载模型列表失败:', error);
      setMessage({ type: 'error', text: `加载模型列表失败: ${error instanceof Error ? error.message : '未知错误'}` });
    } finally {
      setLoading(false);
    }
  };

  // 按提供商分组模型
  const getProviderGroups = (): ProviderGroup[] => {
    const providers = [
      {
        id: 'anthropic',
        name: 'Anthropic (Claude)',
        description: 'Claude 系列模型，包括 Opus、Sonnet、Haiku',
        docsUrl: 'https://console.anthropic.com',
      },
      {
        id: 'openai',
        name: 'OpenAI (GPT)',
        description: 'GPT 系列模型，包括 GPT-4o、GPT-4 Turbo',
        docsUrl: 'https://platform.openai.com',
      },
      {
        id: 'gemini',
        name: 'Google Gemini',
        description: 'Google 最新的 Gemini 模型系列',
        docsUrl: 'https://ai.google.dev',
      },
      {
        id: 'qwen',
        name: '阿里千问',
        description: '阿里巴巴通义千问大模型',
        docsUrl: 'https://dashscope.console.aliyun.com',
      },
      {
        id: 'volcengine',
        name: '火山引擎',
        description: '字节跳动豆包大模型',
        docsUrl: 'https://console.volcengine.com',
      },
    ];

    return providers.map(provider => ({
      ...provider,
      models: models.filter(m => m.provider === provider.id),
    })).filter(p => p.models.length > 0); // 只显示有模型的提供商
  };

  // 切换提供商折叠状态
  const toggleProvider = (providerId: string) => {
    setExpandedProviders(prev => ({
      ...prev,
      [providerId]: !prev[providerId],
    }));
  };

  // 保存模型 API Key
  const saveModelConfig = async (modelId: string) => {
    const apiKey = modelApiKeys[modelId];
    if (!apiKey || !apiKey.trim()) {
      setMessage({ type: 'error', text: '请输入 API Key' });
      return;
    }

    setSavingModel(modelId);
    setMessage(null);

    try {
      await llmModelsApi.update(modelId, { api_key: apiKey });
      setMessage({ type: 'success', text: '配置已保存' });

      // 清空输入框
      setModelApiKeys(prev => ({ ...prev, [modelId]: '' }));

      // 重新加载模型列表
      await loadModels();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '保存失败' });
    } finally {
      setSavingModel(null);
    }
  };

  // 测试模型连接
  const testModel = async (modelId: string) => {
    setTestingModel(modelId);
    setMessage(null);

    try {
      const result = await llmModelsApi.test(modelId, { test_prompt: '你好' });

      if (result.success) {
        setMessage({
          type: 'success',
          text: `测试成功！响应: ${result.response?.substring(0, 50)}${(result.response?.length || 0) > 50 ? '...' : ''}`,
        });
      } else {
        setMessage({ type: 'error', text: result.error || '测试失败' });
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '测试失败' });
    } finally {
      setTestingModel(null);
    }
  };

  // 切换模型启用状态
  const toggleModelEnabled = async (modelId: string, currentEnabled: boolean) => {
    try {
      await llmModelsApi.update(modelId, { is_enabled: !currentEnabled });
      await loadModels();
      setMessage({
        type: 'success',
        text: currentEnabled ? '模型已禁用' : '模型已启用',
      });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '操作失败' });
    }
  };

  // 创建新模型
  const handleCreateModel = async () => {
    if (!createFormData.model_id || !createFormData.provider || !createFormData.model_name) {
      setMessage({ type: 'error', text: '请填写必填字段' });
      return;
    }

    setCreating(true);
    setMessage(null);

    try {
      await llmModelsApi.create({
        model_id: createFormData.model_id,
        provider: createFormData.provider,
        model_name: createFormData.model_name,
        description: createFormData.description || undefined,
        api_key: createFormData.api_key || undefined,
        is_enabled: true,
      });

      setMessage({ type: 'success', text: '模型已添加' });
      setShowCreateModal(false);
      setCreateFormData({
        model_id: '',
        provider: 'anthropic',
        model_name: '',
        description: '',
        api_key: '',
      });

      // 重新加载模型列表
      await loadModels();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '创建失败' });
    } finally {
      setCreating(false);
    }
  };

  // 删除模型
  const handleDeleteModel = async (modelId: string, modelName: string) => {
    if (!confirm(`确定要删除模型 "${modelName}" 吗？\n\n删除后相关的使用统计也会丢失。`)) {
      return;
    }

    try {
      await llmModelsApi.delete(modelId);
      setMessage({ type: 'success', text: '模型已删除' });

      // 立即从前端状态中移除该模型，确保 UI 立即更新
      setModels(prevModels => prevModels.filter(m => m.model_id !== modelId));
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '删除失败' });
    }
  };

  // 统计信息
  const getStats = () => {
    const configured = models.filter(m => m.is_configured).length;
    const enabled = models.filter(m => m.is_enabled).length;
    const totalRequests = models.reduce((sum, m) => sum + m.total_requests, 0);
    const totalTokens = models.reduce((sum, m) => sum + m.total_tokens, 0);

    return { configured, enabled, totalRequests, totalTokens };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  const providerGroups = getProviderGroups();
  const stats = getStats();

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">LLM 模型配置</h1>
          <p className="mt-1 text-sm text-gray-500">
            配置各个 AI 模型的 API Key 和参数
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
        >
          ➕ 新增模型
        </button>
      </div>

      {/* 统计信息 */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">总模型数</dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">{models.length}</dd>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">已配置</dt>
            <dd className="mt-1 text-3xl font-semibold text-green-600">{stats.configured}</dd>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">总请求数</dt>
            <dd className="mt-1 text-3xl font-semibold text-blue-600">{stats.totalRequests}</dd>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">总 Token 数</dt>
            <dd className="mt-1 text-3xl font-semibold text-purple-600">
              {(stats.totalTokens / 1000).toFixed(1)}K
            </dd>
          </div>
        </div>
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

      {/* Provider 卡片列表 */}
      <div className="space-y-4">
        {/* 调试信息 */}
        {models.length === 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-yellow-800 mb-2">⚠️ 调试信息</h3>
            <p className="text-sm text-yellow-700">
              未加载到任何模型数据。请检查浏览器控制台（F12）查看详细错误信息。
            </p>
            <p className="text-xs text-yellow-600 mt-2">
              models.length = {models.length}, providerGroups.length = {providerGroups.length}
            </p>
          </div>
        )}

        {providerGroups.length === 0 && models.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-700">
              已加载 {models.length} 个模型，但所有提供商的模型数量为 0（被过滤了）。
            </p>
          </div>
        )}

        {providerGroups.map((provider) => {
          const isExpanded = expandedProviders[provider.id];
          const configuredCount = provider.models.filter(m => m.is_configured).length;
          const totalCount = provider.models.length;

          return (
            <div key={provider.id} className="bg-white shadow rounded-lg overflow-hidden">
              {/* Provider 头部（可点击折叠/展开） */}
              <button
                onClick={() => toggleProvider(provider.id)}
                className="w-full px-6 py-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="text-left">
                    <h3 className="text-lg font-medium text-gray-900">{provider.name}</h3>
                    <p className="text-sm text-gray-500">{provider.description}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {configuredCount}/{totalCount} 已配置
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <a
                    href={provider.docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    获取 API Key
                  </a>
                  {isExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                  )}
                </div>
              </button>

              {/* 模型列表（展开时显示） */}
              {isExpanded && (
                <div className="px-6 py-4">
                  <div className="space-y-4">
                    {provider.models.map((model) => (
                      <div
                        key={model.model_id}
                        className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                      >
                        {/* 模型信息 */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <h4 className="text-base font-medium text-gray-900">{model.model_name}</h4>
                              {model.is_configured && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                  已配置
                                </span>
                              )}
                              {!model.is_enabled && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                  已禁用
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-500 mt-1">{model.description}</p>
                            <p className="text-xs text-gray-400 mt-1 font-mono">{model.model_id}</p>
                          </div>

                          {/* 操作按钮 */}
                          <div className="flex items-center space-x-2">
                            {/* 删除按钮 */}
                            <button
                              onClick={() => handleDeleteModel(model.model_id, model.model_name)}
                              className="text-red-600 hover:text-red-800 p-1"
                              title="删除模型"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>

                            {/* 启用/禁用开关 */}
                            <button
                              onClick={() => toggleModelEnabled(model.model_id, model.is_enabled)}
                              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                                model.is_enabled ? 'bg-blue-600' : 'bg-gray-200'
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                  model.is_enabled ? 'translate-x-5' : 'translate-x-0'
                                }`}
                              />
                            </button>
                          </div>
                        </div>

                        {/* 使用统计 */}
                        {model.total_requests > 0 && (
                          <div className="mb-3 flex items-center space-x-4 text-xs text-gray-500">
                            <span>请求: {model.total_requests}</span>
                            <span>Tokens: {(model.total_tokens / 1000).toFixed(1)}K</span>
                            {model.last_used_at && (
                              <span>最后使用: {new Date(model.last_used_at).toLocaleString('zh-CN')}</span>
                            )}
                          </div>
                        )}

                        {/* API Key 配置 */}
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-gray-700">
                            API Key
                            {model.api_key_preview && (
                              <span className="ml-2 text-gray-400 font-mono text-xs">
                                当前: {model.api_key_preview}
                              </span>
                            )}
                          </label>
                          <div className="flex space-x-2">
                            <input
                              type="password"
                              value={modelApiKeys[model.model_id] || ''}
                              onChange={(e) =>
                                setModelApiKeys(prev => ({ ...prev, [model.model_id]: e.target.value }))
                              }
                              placeholder="输入新的 API Key..."
                              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            />
                            <button
                              onClick={() => saveModelConfig(model.model_id)}
                              disabled={
                                savingModel === model.model_id ||
                                !modelApiKeys[model.model_id]?.trim()
                              }
                              className="px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {savingModel === model.model_id ? '保存中...' : '保存'}
                            </button>
                            <button
                              onClick={() => testModel(model.model_id)}
                              disabled={!model.is_configured || testingModel === model.model_id}
                              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {testingModel === model.model_id ? '测试中...' : '测试'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 说明文档 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">💡 使用说明</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>每个模型可以单独配置 API Key，实现精细化管理和成本追踪</li>
          <li>点击提供商名称可以展开/收起模型列表</li>
          <li>配置后可以点击"测试"按钮验证连接是否正常</li>
          <li>使用右上角的开关可以启用/禁用特定模型</li>
          <li>系统会自动记录每个模型的使用次数和 Token 消耗</li>
          <li>点击右上角"新增模型"按钮可以添加自定义模型（支持 <a href="https://docs.litellm.ai/docs/providers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-medium">100+ LiteLLM 兼容模型</a>）</li>
        </ul>
      </div>

      {/* 新增模型弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 py-8">
            {/* 背景遮罩 */}
            <div
              className="fixed inset-0 bg-black opacity-50"
              onClick={() => setShowCreateModal(false)}
            />

            {/* 弹窗内容 */}
            <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">新增 LLM 模型</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* LiteLLM 配置说明 */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-blue-900 mb-2">LiteLLM 模型配置说明</h4>
                    <div className="text-xs text-blue-800 space-y-1">
                      <p><strong>Model ID 格式：</strong><code className="bg-blue-100 px-1.5 py-0.5 rounded font-mono">provider/model-name</code></p>
                      <p className="mt-2"><strong>常见示例：</strong></p>
                      <ul className="list-disc list-inside ml-2 space-y-0.5">
                        <li><code className="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-[11px]">anthropic/claude-3-opus-20240229</code></li>
                        <li><code className="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-[11px]">openai/gpt-4-turbo-preview</code></li>
                        <li><code className="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-[11px]">gemini/gemini-1.5-pro</code></li>
                        <li><code className="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-[11px]">qwen/qwen-turbo</code></li>
                      </ul>
                      <p className="mt-2">
                        💡 <strong>注意：</strong>系统会自动添加提供商前缀，您也可以输入完整格式
                      </p>
                      <p className="mt-1">
                        📚 <a href="https://docs.litellm.ai/docs/providers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline font-medium">查看完整的模型列表 →</a>
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {/* Model ID */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model ID <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={createFormData.model_id}
                    onChange={(e) => setCreateFormData({ ...createFormData, model_id: e.target.value })}
                    placeholder={
                      createFormData.provider === 'anthropic' ? 'claude-3-opus-20240229 或 anthropic/claude-3-opus-20240229' :
                      createFormData.provider === 'openai' ? 'gpt-4-turbo-preview 或 openai/gpt-4-turbo-preview' :
                      createFormData.provider === 'gemini' ? 'gemini-1.5-pro 或 gemini/gemini-1.5-pro' :
                      createFormData.provider === 'qwen' ? 'qwen-turbo 或 qwen/qwen-turbo' :
                      createFormData.provider === 'volcengine' ? 'doubao-pro-4k 或 volcengine/doubao-pro-4k' :
                      'provider/model-name 格式'
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {createFormData.provider === 'anthropic' && '例如：claude-3-opus-20240229、claude-3-sonnet-20240229、claude-3-haiku-20240307'}
                    {createFormData.provider === 'openai' && '例如：gpt-4-turbo-preview、gpt-4、gpt-3.5-turbo'}
                    {createFormData.provider === 'gemini' && '例如：gemini-1.5-pro、gemini-1.5-flash、gemini-pro'}
                    {createFormData.provider === 'qwen' && '例如：qwen-turbo、qwen-plus、qwen-max'}
                    {createFormData.provider === 'volcengine' && '例如：doubao-pro-4k、doubao-lite-4k'}
                    {!['anthropic', 'openai', 'gemini', 'qwen', 'volcengine'].includes(createFormData.provider) &&
                      '模型 ID 应为 LiteLLM 格式，如 provider/model-name'}
                  </p>
                </div>

                {/* Provider */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    提供商 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={createFormData.provider}
                    onChange={(e) => setCreateFormData({ ...createFormData, provider: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    <option value="anthropic">Anthropic (Claude)</option>
                    <option value="openai">OpenAI (GPT)</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="qwen">阿里千问 (Qwen)</option>
                    <option value="volcengine">火山引擎 (Doubao)</option>
                    <option value="zhipu">智谱 AI (GLM)</option>
                    <option value="other">其他</option>
                  </select>
                </div>

                {/* Model Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    显示名称 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={createFormData.model_name}
                    onChange={(e) => setCreateFormData({ ...createFormData, model_name: e.target.value })}
                    placeholder="如：Claude Opus 4.5"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    描述（可选）
                  </label>
                  <textarea
                    value={createFormData.description}
                    onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                    placeholder="模型的简短描述..."
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key（可选）
                  </label>
                  <input
                    type="password"
                    value={createFormData.api_key}
                    onChange={(e) => setCreateFormData({ ...createFormData, api_key: e.target.value })}
                    placeholder="创建时可以留空，之后再配置"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                {/* 操作按钮 */}
                <div className="flex justify-end space-x-3 pt-4 border-t">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreateModel}
                    disabled={creating || !createFormData.model_id || !createFormData.provider || !createFormData.model_name}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {creating ? '创建中...' : '创建模型'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
