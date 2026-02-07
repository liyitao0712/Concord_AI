'use client';

import { useState, useEffect } from 'react';
import { llmModelsApi, promptsApi, agentsConfigApi, type LLMModelConfig, type PromptItem, type AgentListItem } from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { PageLoading } from '@/components/LoadingSpinner';

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentListItem[]>([]);
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
  const [activeTab, setActiveTab] = useState<string>('config');

  const confirm = useConfirm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [agentsData, modelsData, promptsData] = await Promise.all([
        agentsConfigApi.list(),
        llmModelsApi.list({ is_enabled: true }),
        promptsApi.list({ is_active: true }),
      ]);
      setAgents(agentsData);
      setModels(modelsData.items);
      setPrompts(promptsData.items);
    } catch (error) {
      console.error('加载数据失败:', error);
      setMessage({ type: 'error', text: '加载数据失败' });
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = async (agent: AgentListItem) => {
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

    const agent = agents.find(a => a.name === editingAgent);
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
    const confirmed = await confirm({
      title: '确认重置',
      description: `确定要重置${type === 'system' ? 'System' : 'User'} Prompt 为默认值吗？当前内容将被覆盖。`,
      variant: 'destructive',
    });
    if (!confirmed) return;

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

  const getPromptForAgent = (promptName: string): PromptItem | null => {
    return prompts.find(p => p.name === promptName) || null;
  };

  if (loading) {
    return <PageLoading />;
  }

  const availableModels = models.filter(m => m.is_configured);
  const currentAgent = agents.find(a => a.name === editingAgent);
  const currentPrompt = currentAgent ? getPromptForAgent(currentAgent.prompt_name) : null;
  const currentSystemPrompt = currentAgent ? getPromptForAgent(currentAgent.system_prompt_name) : null;

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold">Agent 管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          配置 AI Agent 的模型、参数和 Prompt（Agent 列表从后端自动加载，新增 Agent 无需修改前端）
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
      <Card className="py-0 overflow-hidden">
        <ul className="divide-y">
          {agents.map((agent) => {
            const prompt = getPromptForAgent(agent.prompt_name);
            const systemPrompt = getPromptForAgent(agent.system_prompt_name);
            const modelConfig = agent.model ? models.find(m => m.model_id === agent.model) : null;

            return (
              <li key={agent.name}>
                <div className="px-4 py-4 sm:px-6 hover:bg-muted/50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-base font-medium">{agent.display_name || agent.name}</p>
                        <div className="ml-2 flex-shrink-0 flex space-x-2">
                          {prompt ? (
                            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                              User Prompt
                            </Badge>
                          ) : (
                            <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
                              User Prompt 未配置
                            </Badge>
                          )}
                          {systemPrompt ? (
                            <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100">
                              System Prompt
                            </Badge>
                          ) : (
                            <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
                              System Prompt 未配置
                            </Badge>
                          )}
                          {modelConfig ? (
                            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">
                              {modelConfig.model_name}
                            </Badge>
                          ) : (
                            <Badge variant="secondary">
                              使用默认模型
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="mt-2">
                        <p className="text-sm text-muted-foreground">{agent.description}</p>
                      </div>
                      <div className="mt-2 sm:flex sm:justify-between">
                        <div className="sm:flex space-x-4 text-sm text-muted-foreground">
                          <p className="flex items-center">
                            <span className="font-medium">Prompt:</span>
                            <span className="ml-1 font-mono text-xs">{agent.prompt_name}</span>
                          </p>
                          {prompt && (
                            <p className="flex items-center text-xs text-muted-foreground">
                              v{prompt.version} · 更新于 {new Date(prompt.updated_at).toLocaleDateString('zh-CN')}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="ml-5 flex-shrink-0">
                      <Button variant="outline" onClick={() => openEditModal(agent)}>
                        编辑配置
                      </Button>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {/* 编辑模态框 */}
      <Dialog open={!!editingAgent && !!currentAgent} onOpenChange={(open) => { if (!open) closeEditModal(); }}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-4xl">
          {/* 标题 */}
          <DialogHeader>
            <DialogTitle>
              {currentAgent?.display_name || currentAgent?.name}
            </DialogTitle>
            <p className="text-sm text-muted-foreground">{currentAgent?.description}</p>
          </DialogHeader>

          {/* 标签页 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="config">基本配置</TabsTrigger>
              <TabsTrigger value="prompt">
                Prompt 编辑
                {currentPrompt && (
                  <Badge className="ml-2 bg-green-100 text-green-800 hover:bg-green-100" variant="secondary">
                    v{currentPrompt.version}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* 基本配置标签页 */}
            <TabsContent value="config">
              <div className="space-y-4">
                {/* 模型选择 */}
                <div>
                  <Label>LLM 模型</Label>
                  <select
                    value={editModel}
                    onChange={(e) => setEditModel(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    <option value="">使用默认模型</option>
                    {availableModels.map((model) => (
                      <option key={model.model_id} value={model.model_id}>
                        {model.model_name} ({model.provider})
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-muted-foreground">
                    留空则使用系统默认模型
                  </p>
                </div>

                {/* Temperature */}
                <div>
                  <Label>Temperature</Label>
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
                    <span className="text-sm font-mono text-muted-foreground w-12 text-right">
                      {editTemperature.toFixed(1)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    控制输出的随机性，越高越随机（0-2）
                  </p>
                </div>

                {/* Max Tokens */}
                <div>
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    min="100"
                    max="100000"
                    step="100"
                    value={editMaxTokens}
                    onChange={(e) => setEditMaxTokens(parseInt(e.target.value))}
                    className="mt-1"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    最大输出 Token 数量
                  </p>
                </div>

                {/* 保存按钮 */}
                <div className="pt-4 border-t">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                    <p className="text-sm text-yellow-800">
                      Agent 配置功能正在开发中，目前仅支持 Prompt 编辑
                    </p>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Prompt 编辑标签页 */}
            <TabsContent value="prompt">
              <div className="space-y-6">
                {/* System Prompt 区域 */}
                <div className="border border-purple-200 rounded-lg p-4 bg-purple-50/30">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-purple-800">
                      System Prompt
                      {currentSystemPrompt && (
                        <span className="ml-2 text-xs font-normal text-purple-500">
                          v{currentSystemPrompt.version}
                        </span>
                      )}
                    </Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => currentAgent && resetPromptToDefault(currentAgent.system_prompt_name, 'system')}
                      disabled={resettingPrompt}
                      className="border-orange-300 text-orange-700 hover:bg-orange-50"
                    >
                      {resettingPrompt ? '重置中...' : '重置为默认'}
                    </Button>
                  </div>
                  <p className="text-xs text-purple-600 mb-2">
                    定义 Agent 的角色和全局行为规范。支持 {'{{company_name}}'} 等系统变量自动注入
                  </p>
                  <Textarea
                    value={editSystemPromptContent}
                    onChange={(e) => setEditSystemPromptContent(e.target.value)}
                    rows={6}
                    className="border-purple-200 focus-visible:ring-purple-500 font-mono text-xs"
                    placeholder="System Prompt..."
                  />
                </div>

                {/* User Prompt 区域 */}
                <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/30">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-blue-800">
                      User Prompt
                      {currentPrompt && (
                        <span className="ml-2 text-xs font-normal text-blue-500">
                          v{currentPrompt.version}
                        </span>
                      )}
                    </Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => currentAgent && resetPromptToDefault(currentAgent.prompt_name, 'user')}
                      disabled={resettingPrompt}
                      className="border-orange-300 text-orange-700 hover:bg-orange-50"
                    >
                      {resettingPrompt ? '重置中...' : '重置为默认'}
                    </Button>
                  </div>

                  {/* 显示名称 */}
                  <div className="mb-3">
                    <Input
                      type="text"
                      value={editPromptDisplayName}
                      onChange={(e) => setEditPromptDisplayName(e.target.value)}
                      placeholder="显示名称（可选）"
                      className="border-blue-200"
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
                  <Textarea
                    value={editPromptContent}
                    onChange={(e) => setEditPromptContent(e.target.value)}
                    rows={16}
                    className="border-blue-200 focus-visible:ring-blue-500 font-mono text-xs"
                    placeholder="User Prompt 内容..."
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    使用 {'{{变量名}}'} 格式定义变量，例如：{'{{content}}'}
                  </p>
                </div>

                {/* Prompt 信息 */}
                {currentPrompt && (
                  <div className="bg-muted rounded-md p-3 text-xs text-muted-foreground">
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
                <div className="pt-4 border-t flex justify-end">
                  <Button
                    onClick={savePrompt}
                    disabled={savingPrompt}
                  >
                    {savingPrompt ? '保存中...' : '保存 Prompt'}
                  </Button>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          {/* 底部按钮 */}
          <DialogFooter>
            <Button variant="outline" onClick={closeEditModal}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
