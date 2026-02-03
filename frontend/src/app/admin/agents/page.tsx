'use client';

import { useState, useEffect } from 'react';
import { llmModelsApi, promptsApi, agentsConfigApi, type LLMModelConfig, type PromptItem } from '@/lib/api';

interface AgentConfig {
  name: string;
  display_name: string;
  description: string;
  prompt_name: string;
  system_prompt_name: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  tools?: string[];
}

const AGENTS: AgentConfig[] = [
  {
    name: 'chat_agent',
    display_name: '对话助手',
    description: '通用聊天助手，处理用户对话和查询',
    prompt_name: 'chat_agent',
    system_prompt_name: 'chat_agent_system',
  },
  {
    name: 'email_summarizer',
    display_name: '邮件摘要生成器',
    description: '生成邮件摘要和关键要点',
    prompt_name: 'email_summarizer',
    system_prompt_name: 'email_summarizer_system',
  },
  {
    name: 'work_type_analyzer',
    display_name: '工作类型分析器',
    description: '分析邮件内容判断工作类型，匹配现有类型或建议新类型',
    prompt_name: 'work_type_analyzer',
    system_prompt_name: 'work_type_analyzer_system',
  },
];

export default function AgentsPage() {
  const [models, setModels] = useState<LLMModelConfig[]>([]);
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 当前正在编辑的 Agent
  const [editingAgent, setEditingAgent] = useState<string | null>(null);
  const [editModel, setEditModel] = useState('');
  const [editTemperature, setEditTemperature] = useState(0.7);
  const [editMaxTokens, setEditMaxTokens] = useState(4096);

  // System Prompt 编辑
  const [editSystemPromptContent, setEditSystemPromptContent] = useState('');
  // User Prompt 编辑
  const [editPromptContent, setEditPromptContent] = useState('');
  const [editPromptDisplayName, setEditPromptDisplayName] = useState('');
  const [editPromptDescription, setEditPromptDescription] = useState('');
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [resettingPrompt, setResettingPrompt] = useState(false);

  // 选项卡
  const [activeTab, setActiveTab] = useState<'config' | 'prompt'>('config');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [modelsData, promptsData] = await Promise.all([
        llmModelsApi.list({ is_enabled: true }),
        promptsApi.list({ is_active: true }),
      ]);
      setModels(modelsData.items);
      setPrompts(promptsData.items);
    } catch (error) {
      console.error('加载数据失败:', error);
      setMessage({ type: 'error', text: '加载数据失败' });
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = async (agent: AgentConfig) => {
    setEditingAgent(agent.name);
    setActiveTab('config');

    // 加载 Agent 配置
    try {
      const config = await agentsConfigApi.getConfig(agent.name);
      setEditModel(config.model || '');
      setEditTemperature(config.temperature || 0.7);
      setEditMaxTokens(config.max_tokens || 4096);
    } catch (error) {
      console.error('加载 Agent 配置失败:', error);
      setEditModel('');
      setEditTemperature(0.7);
      setEditMaxTokens(4096);
    }

    // 加载 System Prompt
    const systemPrompt = prompts.find(p => p.name === agent.system_prompt_name);
    setEditSystemPromptContent(systemPrompt?.content || '');

    // 加载 User Prompt
    const userPrompt = prompts.find(p => p.name === agent.prompt_name);
    if (userPrompt) {
      setEditPromptContent(userPrompt.content);
      setEditPromptDisplayName(userPrompt.display_name || '');
      setEditPromptDescription(userPrompt.description || '');
    } else {
      setEditPromptContent('');
      setEditPromptDisplayName('');
      setEditPromptDescription('');
    }
  };

  const closeEditModal = () => {
    setEditingAgent(null);
    setEditModel('');
    setEditTemperature(0.7);
    setEditMaxTokens(4096);
    setEditSystemPromptContent('');
    setEditPromptContent('');
    setEditPromptDisplayName('');
    setEditPromptDescription('');
    setActiveTab('config');
  };

  const saveAgentConfig = async () => {
    if (!editingAgent) return;

    try {
      await agentsConfigApi.updateConfig(editingAgent, {
        model: editModel || undefined,
        temperature: editTemperature,
        max_tokens: editMaxTokens,
      });
      setMessage({ type: 'success', text: 'Agent 配置已保存' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '保存失败' });
    }
  };

  const savePrompt = async () => {
    if (!editingAgent) return;

    const agent = AGENTS.find(a => a.name === editingAgent);
    if (!agent) return;

    setSavingPrompt(true);
    try {
      // 保存 System Prompt
      if (editSystemPromptContent) {
        await promptsApi.update(agent.system_prompt_name, {
          content: editSystemPromptContent,
        });
      }

      // 保存 User Prompt
      await promptsApi.update(agent.prompt_name, {
        content: editPromptContent,
        display_name: editPromptDisplayName || undefined,
        description: editPromptDescription || undefined,
      });

      setMessage({ type: 'success', text: 'Prompt 已保存' });
      await loadData();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '保存失败' });
    } finally {
      setSavingPrompt(false);
    }
  };

  const resetPromptToDefault = async (promptName: string, type: 'system' | 'user') => {
    if (!confirm(`确定要重置${type === 'system' ? 'System' : 'User'} Prompt 为默认值吗？当前内容将被覆盖。`)) {
      return;
    }

    setResettingPrompt(true);
    try {
      const updated = await promptsApi.resetToDefault(promptName);
      if (type === 'system') {
        setEditSystemPromptContent(updated.content);
      } else {
        setEditPromptContent(updated.content);
      }
      setMessage({ type: 'success', text: `${type === 'system' ? 'System' : 'User'} Prompt 已重置为默认值` });
      await loadData();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '重置失败' });
    } finally {
      setResettingPrompt(false);
    }
  };

  const getPromptForAgent = (agentName: string): PromptItem | null => {
    return prompts.find(p => p.name === agentName) || null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  const availableModels = models.filter(m => m.is_configured);
  const currentAgent = AGENTS.find(a => a.name === editingAgent);
  const currentPrompt = currentAgent ? getPromptForAgent(currentAgent.prompt_name) : null;
  const currentSystemPrompt = currentAgent ? getPromptForAgent(currentAgent.system_prompt_name) : null;

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Agent 管理</h1>
        <p className="mt-1 text-sm text-gray-500">
          配置 AI Agent 的模型、参数和 Prompt
        </p>
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

      {/* Agent 列表 */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {AGENTS.map((agent) => {
            const prompt = getPromptForAgent(agent.prompt_name);
            const systemPrompt = getPromptForAgent(agent.system_prompt_name);
            const modelConfig = agent.model ? models.find(m => m.model_id === agent.model) : null;

            return (
              <li key={agent.name}>
                <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-base font-medium text-gray-900">{agent.display_name}</p>
                        <div className="ml-2 flex-shrink-0 flex space-x-2">
                          {prompt ? (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              User Prompt
                            </p>
                          ) : (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                              User Prompt 未配置
                            </p>
                          )}
                          {systemPrompt ? (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                              System Prompt
                            </p>
                          ) : (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                              System Prompt 未配置
                            </p>
                          )}
                          {modelConfig ? (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                              {modelConfig.model_name}
                            </p>
                          ) : (
                            <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-600">
                              使用默认模型
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="mt-2">
                        <p className="text-sm text-gray-500">{agent.description}</p>
                      </div>
                      <div className="mt-2 sm:flex sm:justify-between">
                        <div className="sm:flex space-x-4 text-sm text-gray-500">
                          <p className="flex items-center">
                            <span className="font-medium">Prompt:</span>
                            <span className="ml-1 font-mono text-xs">{agent.prompt_name}</span>
                          </p>
                          {prompt && (
                            <p className="flex items-center text-xs text-gray-400">
                              v{prompt.version} · 更新于 {new Date(prompt.updated_at).toLocaleDateString('zh-CN')}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="ml-5 flex-shrink-0">
                      <button
                        onClick={() => openEditModal(agent)}
                        className="px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                      >
                        编辑配置
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      {/* 编辑模态框 */}
      {editingAgent && currentAgent && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 py-8">
            <div
              className="fixed inset-0 bg-black opacity-50"
              onClick={closeEditModal}
            />
            <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full p-6 max-h-[90vh] overflow-y-auto">
              {/* 标题 */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    {currentAgent.display_name}
                  </h3>
                  <p className="text-sm text-gray-500">{currentAgent.description}</p>
                </div>
                <button
                  onClick={closeEditModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* 标签页 */}
              <div className="border-b border-gray-200 mb-4">
                <nav className="-mb-px flex space-x-8">
                  <button
                    onClick={() => setActiveTab('config')}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'config'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    基本配置
                  </button>
                  <button
                    onClick={() => setActiveTab('prompt')}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'prompt'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Prompt 编辑
                    {currentPrompt && (
                      <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">
                        v{currentPrompt.version}
                      </span>
                    )}
                  </button>
                </nav>
              </div>

              {/* 基本配置标签页 */}
              {activeTab === 'config' && (
                <div className="space-y-4">
                  {/* 模型选择 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      LLM 模型
                    </label>
                    <select
                      value={editModel}
                      onChange={(e) => setEditModel(e.target.value)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                    >
                      <option value="">使用默认模型</option>
                      {availableModels.map((model) => (
                        <option key={model.model_id} value={model.model_id}>
                          {model.model_name} ({model.provider})
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                      留空则使用系统默认模型
                    </p>
                  </div>

                  {/* Temperature */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Temperature
                    </label>
                    <div className="mt-1 flex items-center space-x-4">
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={editTemperature}
                        onChange={(e) => setEditTemperature(parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-mono text-gray-600 w-12 text-right">
                        {editTemperature.toFixed(1)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      控制输出的随机性，越高越随机（0-2）
                    </p>
                  </div>

                  {/* Max Tokens */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Max Tokens
                    </label>
                    <input
                      type="number"
                      min="100"
                      max="100000"
                      step="100"
                      value={editMaxTokens}
                      onChange={(e) => setEditMaxTokens(parseInt(e.target.value))}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      最大输出 Token 数量
                    </p>
                  </div>

                  {/* 保存按钮 */}
                  <div className="pt-4 border-t border-gray-200">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                      <p className="text-sm text-yellow-800">
                        Agent 配置功能正在开发中，目前仅支持 Prompt 编辑
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Prompt 编辑标签页 */}
              {activeTab === 'prompt' && (
                <div className="space-y-6">
                  {/* System Prompt 区域 */}
                  <div className="border border-purple-200 rounded-lg p-4 bg-purple-50/30">
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-purple-800">
                        System Prompt
                        {currentSystemPrompt && (
                          <span className="ml-2 text-xs font-normal text-purple-500">
                            v{currentSystemPrompt.version}
                          </span>
                        )}
                      </label>
                      <button
                        onClick={() => resetPromptToDefault(currentAgent.system_prompt_name, 'system')}
                        disabled={resettingPrompt}
                        className="px-3 py-1 text-xs border border-orange-300 rounded-md text-orange-700 bg-white hover:bg-orange-50 disabled:opacity-50"
                      >
                        {resettingPrompt ? '重置中...' : '重置为默认'}
                      </button>
                    </div>
                    <p className="text-xs text-purple-600 mb-2">
                      定义 Agent 的角色和全局行为规范，通常不包含变量
                    </p>
                    <textarea
                      value={editSystemPromptContent}
                      onChange={(e) => setEditSystemPromptContent(e.target.value)}
                      rows={6}
                      className="block w-full border-purple-200 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500 sm:text-sm font-mono text-xs"
                      placeholder="System Prompt..."
                    />
                  </div>

                  {/* User Prompt 区域 */}
                  <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/30">
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-blue-800">
                        User Prompt
                        {currentPrompt && (
                          <span className="ml-2 text-xs font-normal text-blue-500">
                            v{currentPrompt.version}
                          </span>
                        )}
                      </label>
                      <button
                        onClick={() => resetPromptToDefault(currentAgent.prompt_name, 'user')}
                        disabled={resettingPrompt}
                        className="px-3 py-1 text-xs border border-orange-300 rounded-md text-orange-700 bg-white hover:bg-orange-50 disabled:opacity-50"
                      >
                        {resettingPrompt ? '重置中...' : '重置为默认'}
                      </button>
                    </div>

                    {/* 显示名称 */}
                    <div className="mb-3">
                      <input
                        type="text"
                        value={editPromptDisplayName}
                        onChange={(e) => setEditPromptDisplayName(e.target.value)}
                        placeholder="显示名称（可选）"
                        className="block w-full border-blue-200 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      />
                    </div>

                    {/* 可用变量提示 */}
                    {currentPrompt?.variables && Object.keys(currentPrompt.variables).length > 0 && (
                      <div className="mb-2 p-2 bg-blue-100/50 border border-blue-200 rounded-md">
                        <p className="text-xs text-blue-800">
                          可用变量：
                          {Object.entries(currentPrompt.variables).map(([key, desc]) => (
                            <span key={key} className="ml-2">
                              <code className="px-1.5 py-0.5 bg-blue-100 rounded text-blue-900">
                                {`{{${key}}}`}
                              </code>
                              <span className="text-blue-600 ml-1">{String(desc)}</span>
                            </span>
                          ))}
                        </p>
                      </div>
                    )}

                    {/* User Prompt 内容 */}
                    <textarea
                      value={editPromptContent}
                      onChange={(e) => setEditPromptContent(e.target.value)}
                      rows={16}
                      className="block w-full border-blue-200 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm font-mono text-xs"
                      placeholder="User Prompt 内容..."
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      使用 {'{{变量名}}'} 格式定义变量，例如：{'{{content}}'}
                    </p>
                  </div>

                  {/* Prompt 信息 */}
                  {currentPrompt && (
                    <div className="bg-gray-50 rounded-md p-3 text-xs text-gray-600">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="font-medium">User Prompt 版本:</span> v{currentPrompt.version}
                        </div>
                        <div>
                          <span className="font-medium">System Prompt 版本:</span> v{currentSystemPrompt?.version || '-'}
                        </div>
                        <div>
                          <span className="font-medium">分类:</span> {currentPrompt.category}
                        </div>
                        <div>
                          <span className="font-medium">更新时间:</span>{' '}
                          {new Date(currentPrompt.updated_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 保存按钮 */}
                  <div className="pt-4 border-t border-gray-200 flex justify-end">
                    <button
                      onClick={savePrompt}
                      disabled={savingPrompt}
                      className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {savingPrompt ? '保存中...' : '保存 Prompt'}
                    </button>
                  </div>
                </div>
              )}

              {/* 底部按钮 */}
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={closeEditModal}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
