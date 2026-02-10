// src/app/admin/settings/feishu/page.tsx
// 飞书配置页面
//
// 功能说明：
// 1. 飞书机器人启用/禁用
// 2. App ID / App Secret 配置
// 3. 连接测试

'use client';

import { useState, useEffect } from 'react';
import { feishuApi, FeishuConfig, FeishuWorkerStatus } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Separator } from '@/components/ui/separator';

export default function FeishuSettingsPage() {
  const [config, setConfig] = useState<FeishuConfig | null>(null);
  const [workerStatus, setWorkerStatus] = useState<FeishuWorkerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 表单状态
  const [enabled, setEnabled] = useState(false);
  const [appId, setAppId] = useState('');
  const [appSecret, setAppSecret] = useState('');
  const [encryptKey, setEncryptKey] = useState('');
  const [verificationToken, setVerificationToken] = useState('');

  // 加载配置
  const loadConfig = async () => {
    try {
      setError(null);
      const [data, status] = await Promise.all([
        feishuApi.getConfig(),
        feishuApi.getWorkerStatus(),
      ]);
      setConfig(data);
      setWorkerStatus(status);
      setEnabled(data.enabled);
      setAppId(data.app_id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  // 保存配置
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updateData: Record<string, any> = { enabled };

      // 只在有输入时更新
      if (appId && appId !== config?.app_id) {
        updateData.app_id = appId;
      }
      if (appSecret) {
        updateData.app_secret = appSecret;
      }
      if (encryptKey) {
        updateData.encrypt_key = encryptKey;
      }
      if (verificationToken) {
        updateData.verification_token = verificationToken;
      }

      await feishuApi.updateConfig(updateData);
      setSuccess('配置保存成功');

      // 清空敏感字段
      setAppSecret('');
      setEncryptKey('');
      setVerificationToken('');

      // 重新加载配置
      await loadConfig();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 测试连接
  const handleTest = async () => {
    setTesting(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await feishuApi.testConnection();
      if (result.success) {
        setSuccess(result.message || '连接测试成功');
      } else {
        setError(result.error || '连接测试失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '测试失败');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold">飞书配置</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          配置飞书机器人，实现与飞书的消息互通
        </p>
      </div>

      {/* 提示信息 */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4">
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700">{success}</p>
        </div>
      )}

      {/* 配置表单 */}
      <Card>
        <CardContent className="space-y-6">
          {/* 启用开关 */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium">启用飞书机器人</h3>
              <p className="text-sm text-muted-foreground">
                启用后，飞书 Worker 将接收和处理飞书消息
              </p>
            </div>
            <Switch
              checked={enabled}
              onCheckedChange={setEnabled}
            />
          </div>

          <Separator />

          {/* Worker 运行状态 */}
          <div>
            <h3 className="text-lg font-medium mb-4">Worker 运行状态</h3>
            <div className={`p-4 rounded-lg border ${
              workerStatus?.worker_running
                ? 'bg-green-50 border-green-200'
                : 'bg-yellow-50 border-yellow-200'
            }`}>
              <div className="flex items-center">
                <span className={`inline-block w-3 h-3 rounded-full mr-3 ${
                  workerStatus?.worker_running ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'
                }`}></span>
                <div>
                  <p className={`font-medium ${
                    workerStatus?.worker_running ? 'text-green-800' : 'text-yellow-800'
                  }`}>
                    {workerStatus?.worker_running ? '长连接已建立' : 'Worker 未运行'}
                  </p>
                  <p className={`text-sm ${
                    workerStatus?.worker_running ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {workerStatus?.worker_running
                      ? '飞书消息可正常接收和回复'
                      : enabled && config?.configured
                        ? '请重启后端服务以启动 Worker'
                        : '请先完成配置并启用'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator />

          {/* 配置状态 */}
          <div>
            <h3 className="text-lg font-medium mb-4">配置状态</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  config?.configured ? 'bg-green-500' : 'bg-muted-foreground/30'
                }`}></span>
                <span className="text-sm text-muted-foreground">
                  基础配置：{config?.configured ? '已完成' : '未配置'}
                </span>
              </div>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  config?.app_secret_configured ? 'bg-green-500' : 'bg-muted-foreground/30'
                }`}></span>
                <span className="text-sm text-muted-foreground">
                  App Secret：{config?.app_secret_configured ? '已配置' : '未配置'}
                </span>
              </div>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  config?.encrypt_key_configured ? 'bg-green-500' : 'bg-muted-foreground/30'
                }`}></span>
                <span className="text-sm text-muted-foreground">
                  Encrypt Key：{config?.encrypt_key_configured ? '已配置' : '未配置'}
                </span>
              </div>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  config?.verification_token_configured ? 'bg-green-500' : 'bg-muted-foreground/30'
                }`}></span>
                <span className="text-sm text-muted-foreground">
                  Verification Token：{config?.verification_token_configured ? '已配置' : '未配置'}
                </span>
              </div>
            </div>
          </div>

          <Separator />

          {/* App ID */}
          <div>
            <Label className="mb-1">App ID</Label>
            <Input
              type="text"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              placeholder="cli_xxxxxxxx"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              在飞书开放平台 -&gt; 应用管理 -&gt; 凭证与基础信息中获取
            </p>
          </div>

          {/* App Secret */}
          <div>
            <Label className="mb-1">App Secret</Label>
            <Input
              type="password"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              placeholder={config?.app_secret_configured ? '••••••••（已配置，留空保持不变）' : '输入 App Secret'}
            />
          </div>

          {/* Encrypt Key（可选） */}
          <div>
            <Label className="mb-1">Encrypt Key（可选）</Label>
            <Input
              type="password"
              value={encryptKey}
              onChange={(e) => setEncryptKey(e.target.value)}
              placeholder={config?.encrypt_key_configured ? '••••••••（已配置，留空保持不变）' : '输入 Encrypt Key'}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              用于解密飞书回调消息，在事件订阅中配置
            </p>
          </div>

          {/* Verification Token（可选） */}
          <div>
            <Label className="mb-1">Verification Token（可选）</Label>
            <Input
              type="password"
              value={verificationToken}
              onChange={(e) => setVerificationToken(e.target.value)}
              placeholder={config?.verification_token_configured ? '••••••••（已配置，留空保持不变）' : '输入 Verification Token'}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              用于验证飞书回调请求，在事件订阅中获取
            </p>
          </div>
        </CardContent>

        {/* 操作按钮 */}
        <div className="px-6 py-4 bg-muted/50 border-t flex justify-between">
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={testing || !config?.configured}
          >
            {testing ? '测试中...' : '测试连接'}
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? '保存中...' : '保存配置'}
          </Button>
        </div>
      </Card>

      {/* 使用说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-800 mb-2">使用说明</h3>
        <ol className="text-sm text-blue-700 list-decimal list-inside space-y-1">
          <li>在飞书开放平台创建企业自建应用</li>
          <li>获取 App ID 和 App Secret</li>
          <li>在应用中添加「机器人」能力</li>
          <li>在「事件与回调」中选择「使用长连接接收事件」</li>
          <li>在此页面填写配置并保存，然后点击「启用」</li>
          <li>重启后端服务：<code className="bg-blue-100 px-1 rounded">./scripts/restart.sh</code></li>
          <li>服务启动后会自动建立飞书长连接</li>
        </ol>
      </div>

      {/* 注意事项 */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-amber-800 mb-2">注意事项</h3>
        <ul className="text-sm text-amber-700 list-disc list-inside space-y-1">
          <li>修改配置后需要重启后端服务才能生效</li>
          <li>飞书要求先建立长连接才能在开放平台完成事件订阅配置</li>
          <li>一个 Worker 实例对应一个飞书应用（机器人）</li>
          <li>多用户同时聊天通过 session 隔离，互不影响</li>
        </ul>
      </div>
    </div>
  );
}
