// src/app/admin/dashboard/page.tsx
// 牛批工作台
//
// 功能说明：
// 1. 顶部 Tab 导航切换不同看板
// 2. 邮件 Tab：邮件播报 + 邮件记录列表
// 3. 项目管理 Tab：项目 CRUD、任务、进度
// 4. 语音播报：使用浏览器 Web Speech API 或 AI TTS 逐条朗读摘要

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
import { PageLoading } from '@/components/LoadingSpinner';
import { ErrorAlert } from '@/components/ErrorAlert';
import { emailsApi, ttsApi, TTS_PROVIDER_OPTIONS, type BriefingItem, type TTSProvider } from '@/lib/api';
import {
  Newspaper,
  Mail,
  Clock,
  Building2,
  Factory,
  ArrowUpRight,
  Inbox,
  RefreshCw,
  Volume2,
  Square,
  Timer,
  ChevronDown,
  ChevronRight,
  Mic,
  FolderKanban,
} from 'lucide-react';

// 懒加载面板组件
const EmailsPanel = dynamic(
  () => import('@/app/(main)/emails/EmailsPanel').then(mod => ({ default: mod.EmailsPanel })),
  { loading: () => <PageLoading /> }
);
const ProjectsPanel = dynamic(
  () => import('@/app/(main)/projects/ProjectsPanel').then(mod => ({ default: mod.ProjectsPanel })),
  { loading: () => <PageLoading /> }
);

// 意图中文映射
const INTENT_MAP: Record<string, string> = {
  inquiry: '询价',
  quotation: '报价',
  order: '订单',
  payment: '付款',
  shipment: '发货',
  complaint: '投诉',
  negotiation: '谈判',
  sample: '样品',
  other: '其他',
};

// 紧急程度样式
const URGENCY_STYLE: Record<string, string> = {
  urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

// 情感样式
const SENTIMENT_STYLE: Record<string, string> = {
  positive: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
  negative: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

// 发件方类型图标
const SENDER_TYPE_ICON: Record<string, typeof Building2> = {
  customer: Building2,
  supplier: Factory,
};

// 获取中文语音（移动端 voices 异步加载，用 hook 处理）
function useChineseVoice() {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const pickVoice = () => {
      const voices = window.speechSynthesis.getVoices();
      const zh = voices.find((v) => v.lang.startsWith('zh')) ?? null;
      setVoice(zh);
    };

    // 桌面端可能同步可用，移动端需要等 voiceschanged
    pickVoice();
    window.speechSynthesis.addEventListener('voiceschanged', pickVoice);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', pickVoice);
    };
  }, []);

  return voice;
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="emails">
        <TabsList variant="line">
          <TabsTrigger value="emails" className="gap-1.5">
            <Mail className="h-4 w-4" />
            邮件
          </TabsTrigger>
          <TabsTrigger value="projects" className="gap-1.5">
            <FolderKanban className="h-4 w-4" />
            项目管理
          </TabsTrigger>
        </TabsList>

        {/* 邮件 Tab：播报 + 记录 */}
        <TabsContent value="emails" className="mt-4 space-y-6">
          <DailyBriefingPanel />
          <EmailsPanel />
        </TabsContent>

        {/* 项目管理 Tab */}
        <TabsContent value="projects" className="mt-4">
          <ProjectsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 邮件播报面板
function DailyBriefingPanel() {
  const [items, setItems] = useState<BriefingItem[]>([]);
  const [dateStr, setDateStr] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [collapsed, setCollapsed] = useState(true);

  // 语音播报状态
  const [playing, setPlaying] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(-1);
  const [ttsSupported, setTtsSupported] = useState(false);
  const playingRef = useRef(false); // ref 避免闭包陈旧
  const chineseVoice = useChineseVoice();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // TTS Provider 选择
  const [ttsProvider, setTtsProvider] = useState<TTSProvider>('browser');
  const [ttsLoading, setTtsLoading] = useState(false);

  // 定时刷新状态（0 = 关闭，单位秒）
  const AUTO_REFRESH_OPTIONS = [
    { label: '关闭', value: 0 },
    { label: '30秒', value: 30 },
    { label: '1分钟', value: 60 },
    { label: '2分钟', value: 120 },
    { label: '5分钟', value: 300 },
  ];
  const [autoRefreshSec, setAutoRefreshSec] = useState(0);
  const [countdown, setCountdown] = useState(0);

  // 客户端挂载后才检测 TTS 支持，避免 SSR 水合不匹配
  useEffect(() => {
    setTtsSupported('speechSynthesis' in window);
    // 读取 localStorage 中保存的 TTS provider
    const saved = localStorage.getItem('tts_provider') as TTSProvider | null;
    if (saved && TTS_PROVIDER_OPTIONS.some((o) => o.value === saved)) {
      setTtsProvider(saved);
    }
  }, []);

  const loadBriefing = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await emailsApi.todayBriefing();
      setItems(data.items);
      const d = new Date(data.date + 'T00:00:00');
      setDateStr(d.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long',
      }));
    } catch (e: any) {
      setError(e.message || '加载播报失败');
    }
    setLoading(false);
  }, []);

  // 静默刷新（不显示 loading 态，避免闪屏）
  const silentRefresh = useCallback(async () => {
    try {
      const data = await emailsApi.todayBriefing();
      setItems(data.items);
      const d = new Date(data.date + 'T00:00:00');
      setDateStr(d.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long',
      }));
    } catch {
      // 静默刷新失败不显示错误，下次重试
    }
  }, []);

  // 定时刷新 + 倒计时
  useEffect(() => {
    if (autoRefreshSec <= 0) {
      setCountdown(0);
      return;
    }
    setCountdown(autoRefreshSec);

    const countdownTimer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          silentRefresh();
          return autoRefreshSec; // 重置倒计时
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdownTimer);
  }, [autoRefreshSec, silentRefresh]);

  // 清理 AI 音频资源
  const cleanupAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute('src');
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  // 停止播报
  const stopSpeaking = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch { /* ignore */ }
    cleanupAudio();
    setPlaying(false);
    setSpeakingIndex(-1);
    playingRef.current = false;
    setTtsLoading(false);
  }, [cleanupAudio]);

  // 播报单条
  const speakItem = useCallback((text: string, voice: SpeechSynthesisVoice | null, onEnd: () => void) => {
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      if (voice) utterance.voice = voice;
      utterance.lang = 'zh-CN';
      utterance.rate = 1.1;
      utterance.onend = onEnd;
      utterance.onerror = () => onEnd();
      window.speechSynthesis.speak(utterance);
    } catch {
      // 移动端某些浏览器可能抛异常，直接跳过
      onEnd();
    }
  }, []);

  // 构建完整播报文本
  const buildFullText = useCallback(() => {
    const lines = [`邮件播报，共${items.length}封。`];
    items.forEach((item, i) => {
      const sender = item.sender_company || item.sender_name || item.sender;
      const content = item.broadcast || item.summary;
      lines.push(`第${i + 1}封，来自${sender}。${content}`);
    });
    return lines.join('\n');
  }, [items]);

  // 使用浏览器 TTS 播报
  const startBrowserSpeaking = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch { /* ignore */ }

    setPlaying(true);
    playingRef.current = true;

    const queue: { text: string; index: number }[] = [
      { text: `邮件播报，共${items.length}封`, index: -1 },
    ];
    items.forEach((item, i) => {
      const sender = item.sender_company || item.sender_name || item.sender;
      const content = item.broadcast || item.summary;
      queue.push({ text: `第${i + 1}封，来自${sender}。${content}`, index: i });
    });

    let current = 0;
    const speakNext = () => {
      if (!playingRef.current || current >= queue.length) {
        setPlaying(false);
        setSpeakingIndex(-1);
        playingRef.current = false;
        return;
      }
      const { text, index } = queue[current];
      setSpeakingIndex(index);
      current++;
      speakItem(text, chineseVoice, speakNext);
    };
    speakNext();
  }, [items, speakItem, chineseVoice]);

  // 使用 AI TTS 播报
  const startAiSpeaking = useCallback(async (provider: TTSProvider) => {
    setTtsLoading(true);
    setPlaying(true);
    playingRef.current = true;
    setSpeakingIndex(-2); // -2 表示全部高亮（AI 模式）

    try {
      const text = buildFullText();
      const blob = await ttsApi.synthesize(text, provider);
      if (!playingRef.current) return; // 用户已点停止

      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        cleanupAudio();
        setPlaying(false);
        setSpeakingIndex(-1);
        playingRef.current = false;
      };

      audio.onerror = () => {
        cleanupAudio();
        setPlaying(false);
        setSpeakingIndex(-1);
        playingRef.current = false;
      };

      setTtsLoading(false);
      await audio.play();
    } catch (e: any) {
      console.warn(`[TTS] AI 播报失败 (${provider}):`, e.message);
      setTtsLoading(false);
      cleanupAudio();
      // 自动 fallback 到浏览器 TTS
      if (ttsSupported) {
        startBrowserSpeaking();
      } else {
        setPlaying(false);
        setSpeakingIndex(-1);
        playingRef.current = false;
      }
    }
  }, [buildFullText, cleanupAudio, ttsSupported, startBrowserSpeaking]);

  // 开始播报（根据 provider 分发）
  const startSpeaking = useCallback(() => {
    if (items.length === 0) return;

    if (ttsProvider === 'browser') {
      startBrowserSpeaking();
    } else {
      startAiSpeaking(ttsProvider);
    }
  }, [items, ttsProvider, startBrowserSpeaking, startAiSpeaking]);

  // 组件卸载时停止播报
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      cleanupAudio();
    };
  }, [cleanupAudio]);

  useEffect(() => {
    loadBriefing();
  }, [loadBriefing]);

  if (loading) return <PageLoading />;

  if (error) {
    return <ErrorAlert message={error} onRetry={loadBriefing} />;
  }

  return (
    <div className="space-y-4">
      {/* 日期标题栏 */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border-blue-200 dark:border-blue-800">
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-3">
              {/* 折叠/展开按钮 */}
              <button
                onClick={() => setCollapsed((v) => !v)}
                className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                title={collapsed ? '展开播报' : '折叠播报'}
              >
                {collapsed ? (
                  <ChevronRight className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                )}
              </button>
              <div className="flex items-center gap-2 cursor-pointer" onClick={() => setCollapsed((v) => !v)}>
                <Newspaper className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <div>
                  <h2 className="text-lg font-semibold">{dateStr}</h2>
                  <p className="text-sm text-muted-foreground">
                    共 {items.length} 封邮件已分析
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* TTS Provider 选择器 */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-1 text-sm px-2.5 py-1.5 rounded-md border border-input bg-background hover:bg-muted transition-colors">
                    <Mic className="h-3.5 w-3.5" />
                    <span className="max-w-[80px] truncate">
                      {TTS_PROVIDER_OPTIONS.find((o) => o.value === ttsProvider)?.label || '浏览器语音'}
                    </span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="min-w-[130px]">
                  {TTS_PROVIDER_OPTIONS.map((opt) => (
                    <DropdownMenuItem
                      key={opt.value}
                      onClick={() => {
                        setTtsProvider(opt.value);
                        localStorage.setItem('tts_provider', opt.value);
                      }}
                      className={ttsProvider === opt.value ? 'text-blue-600 font-medium' : ''}
                    >
                      {opt.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              {/* 语音播报按钮 */}
              <Button
                variant={playing ? 'default' : 'outline'}
                size="sm"
                onClick={playing ? stopSpeaking : startSpeaking}
                disabled={items.length === 0 || ttsLoading}
                className={`gap-1.5 ${playing && !ttsLoading ? 'animate-pulse' : ''}`}
              >
                {ttsLoading ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    合成中
                  </>
                ) : playing ? (
                  <>
                    <Square className="h-3.5 w-3.5" />
                    停止
                  </>
                ) : (
                  <>
                    <Volume2 className="h-3.5 w-3.5" />
                    播放
                  </>
                )}
              </Button>
              {/* 刷新 + 定时刷新 */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={loadBriefing}
                  className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  刷新
                </button>
                {/* 定时刷新下拉 */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className={`flex items-center gap-1 text-sm px-2 py-1 rounded-md transition-colors ${
                        autoRefreshSec > 0
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                          : 'text-muted-foreground hover:bg-muted'
                      }`}
                      title="定时刷新"
                    >
                      <Timer className="h-3.5 w-3.5" />
                      {autoRefreshSec > 0 ? (
                        <span className="tabular-nums text-xs">{countdown}s</span>
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      )}
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="min-w-[100px]">
                    {AUTO_REFRESH_OPTIONS.map((opt) => (
                      <DropdownMenuItem
                        key={opt.value}
                        onClick={() => setAutoRefreshSec(opt.value)}
                        className={autoRefreshSec === opt.value ? 'text-blue-600 font-medium' : ''}
                      >
                        {opt.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 播报列表（折叠时隐藏） */}
      {!collapsed && (
        items.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <Inbox className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-muted-foreground">今日暂无已分析的邮件</p>
              <p className="text-xs text-muted-foreground mt-1">
                对邮件执行 AI 分析后，结果会在此展示
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => (
              <BriefingCard
                key={item.analysis_id}
                item={item}
                isSpeaking={speakingIndex === index || speakingIndex === -2}
              />
            ))}
          </div>
        )
      )}
    </div>
  );
}

// 单条播报卡片
function BriefingCard({ item, isSpeaking }: { item: BriefingItem; isSpeaking: boolean }) {
  const SenderIcon = SENDER_TYPE_ICON[item.sender_type ?? ''] ?? Mail;
  const displayName = item.sender_company || item.sender_name || item.sender;
  const time = new Date(item.received_at).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const cardRef = useRef<HTMLDivElement>(null);

  // 正在播报时自动滚动到可视区域
  useEffect(() => {
    if (isSpeaking && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isSpeaking]);

  return (
    <Card
      ref={cardRef}
      className={`transition-all duration-300 ${
        isSpeaking
          ? 'border-l-4 border-l-blue-500 bg-blue-50/50 dark:bg-blue-950/20 shadow-md'
          : 'hover:shadow-md'
      }`}
    >
      <CardContent className="py-4">
        <div className="flex gap-3">
          {/* 左侧图标 */}
          <div className="flex-shrink-0 mt-0.5">
            <div className={`p-2 rounded-lg ${
              item.sender_type === 'customer'
                ? 'bg-purple-100 dark:bg-purple-900/30'
                : item.sender_type === 'supplier'
                ? 'bg-amber-100 dark:bg-amber-900/30'
                : 'bg-slate-100 dark:bg-slate-800'
            }`}>
              <SenderIcon className={`h-4 w-4 ${
                item.sender_type === 'customer'
                  ? 'text-purple-600 dark:text-purple-400'
                  : item.sender_type === 'supplier'
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-slate-600 dark:text-slate-400'
              }`} />
            </div>
          </div>

          {/* 右侧内容 */}
          <div className="flex-1 min-w-0">
            {/* 第一行：发件方 + 时间 */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-medium truncate">{displayName}</span>
                {item.sender_type && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex-shrink-0">
                    {item.sender_type === 'customer' ? '客户' :
                     item.sender_type === 'supplier' ? '供应商' :
                     item.sender_type}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0">
                <Clock className="h-3 w-3" />
                {time}
              </div>
            </div>

            {/* 第二行：邮件主题 */}
            <p className="text-sm text-muted-foreground truncate mb-1.5">
              {item.subject}
            </p>

            {/* 第三行：摘要（broadcast 优先，否则用 summary） */}
            <p className="text-sm leading-relaxed">
              {item.broadcast || item.summary}
            </p>

            {/* 第四行：标签 */}
            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
              {item.intent && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {INTENT_MAP[item.intent] || item.intent}
                </Badge>
              )}
              {item.urgency && (
                <Badge className={`text-[10px] px-1.5 py-0 border-0 ${URGENCY_STYLE[item.urgency] || ''}`}>
                  {item.urgency === 'urgent' ? '紧急' :
                   item.urgency === 'high' ? '重要' :
                   item.urgency === 'medium' ? '一般' : '低'}
                </Badge>
              )}
              {item.sentiment && (
                <Badge className={`text-[10px] px-1.5 py-0 border-0 ${SENTIMENT_STYLE[item.sentiment] || ''}`}>
                  {item.sentiment === 'positive' ? '积极' :
                   item.sentiment === 'negative' ? '消极' : '中性'}
                </Badge>
              )}
              {/* 跳转邮件详情 */}
              <a
                href={`/emails?highlight=${item.email_id}`}
                className="ml-auto text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
              >
                查看邮件
                <ArrowUpRight className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
