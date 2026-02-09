// src/app/admin/customers/page.tsx
// 客户管理页面
//
// 功能说明：
// 1. 客户列表（搜索、筛选、分页）
// 2. 创建/编辑/删除客户
// 3. 联系人管理（弹窗内 CRUD）

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  customersApi,
  contactsApi,
  customerSuggestionsApi,
  countriesApi,
  Customer,
  CustomerDetail,
  CustomerCreate,
  CustomerUpdate,
  Contact,
  ContactCreate,
  ContactUpdate,
  CustomerSuggestion,
  CustomerReviewData,
  Country,
  tradeTermsApi,
  TradeTerm,
  paymentMethodsApi,
  PaymentMethod,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
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
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useConfirm } from '@/components/ConfirmProvider';
import { toast } from 'sonner';
import { useDevice } from '@/lib/device';
import { usePermission } from '@/hooks/usePermission';
import {
  Plus,
  Search,
  Eye,
  Pencil,
  Trash2,
  X,
  Loader2,
  Sparkles,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Users,
} from 'lucide-react';

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

// 客户等级配置
const CUSTOMER_LEVELS: Record<string, { label: string; color: string }> = {
  potential: { label: '潜在', color: 'bg-gray-100 text-gray-800' },
  normal: { label: '普通', color: 'bg-blue-100 text-blue-800' },
  important: { label: '重要', color: 'bg-orange-100 text-orange-800' },
  vip: { label: 'VIP', color: 'bg-purple-100 text-purple-800' },
};

// select 样式统一
const selectClass = "px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ==================== 可折叠段落 ====================

function FormSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Collapsible defaultOpen={defaultOpen}>
      <CollapsibleTrigger asChild>
        <button type="button" className="w-full group text-left">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-foreground">{title}</h4>
            <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
          </div>
          <Separator className="mt-2" />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-3">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}

// ==================== 客户表单 ====================

function CustomerForm({
  initial,
  onSubmit,
  onCancel,
  loading,
  onDraftCreated,
}: {
  initial?: Partial<Customer>;
  onSubmit: (data: CustomerCreate | CustomerUpdate) => void;
  onCancel: () => void;
  loading: boolean;
  onDraftCreated?: () => void;
}) {
  const isCreateMode = !initial;
  const [form, setForm] = useState<CustomerCreate>({
    name: initial?.name || '',
    short_name: initial?.short_name || '',
    country: initial?.country || '',
    region: initial?.region || '',
    industry: initial?.industry || '',
    company_size: initial?.company_size || '',
    annual_revenue: initial?.annual_revenue || '',
    customer_level: initial?.customer_level || 'normal',
    email: initial?.email || '',
    phone: initial?.phone || '',
    website: initial?.website || '',
    address: initial?.address || '',
    payment_terms: initial?.payment_terms || '',
    shipping_terms: initial?.shipping_terms || '',
    is_active: initial?.is_active ?? true,
    source: initial?.source || '',
    notes: initial?.notes || '',
    tags: initial?.tags || [],
  });
  const [tagInput, setTagInput] = useState('');
  const [tradeTerms, setTradeTerms] = useState<TradeTerm[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [aiQuery, setAiQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  // 国家搜索状态
  const [countrySearch, setCountrySearch] = useState(form.country || '');
  const [countryOptions, setCountryOptions] = useState<Country[]>([]);
  const [countryDefaultOptions, setCountryDefaultOptions] = useState<Country[]>([]); // 初始热门列表缓存
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [countryLoading, setCountryLoading] = useState(false);
  // 国家是否合法（空 = 合法，有值必须从下拉选择）
  const [countryValid, setCountryValid] = useState(true);
  const countryRef = useRef<HTMLDivElement>(null);
  const countrySearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 加载贸易术语和付款方式
  useEffect(() => {
    tradeTermsApi.list({ page_size: 50, is_current: true }).then(resp => {
      setTradeTerms(resp.items);
    }).catch(() => {});
    paymentMethodsApi.list({ page_size: 50 }).then(resp => {
      setPaymentMethods(resp.items);
    }).catch(() => {});
  }, []);

  // 加载热门国家列表（按使用次数排序）
  const loadDefaultCountries = useCallback(async () => {
    if (countryDefaultOptions.length > 0) {
      // 已缓存，直接使用
      setCountryOptions(countryDefaultOptions);
      return;
    }
    setCountryLoading(true);
    try {
      const resp = await countriesApi.list({ sort_by: 'usage', page_size: 50 });
      setCountryDefaultOptions(resp.items);
      setCountryOptions(resp.items);
    } catch {
      setCountryOptions([]);
    }
    setCountryLoading(false);
  }, [countryDefaultOptions]);

  // 国家搜索（防抖）
  useEffect(() => {
    if (countrySearchTimer.current) clearTimeout(countrySearchTimer.current);
    if (!countrySearch.trim()) {
      // 无搜索词时回显热门列表
      if (countryDefaultOptions.length > 0) {
        setCountryOptions(countryDefaultOptions);
      }
      return;
    }
    countrySearchTimer.current = setTimeout(async () => {
      setCountryLoading(true);
      try {
        const resp = await countriesApi.list({ search: countrySearch.trim(), sort_by: 'usage', page_size: 20 });
        setCountryOptions(resp.items);
      } catch {
        setCountryOptions([]);
      }
      setCountryLoading(false);
    }, 300);
    return () => { if (countrySearchTimer.current) clearTimeout(countrySearchTimer.current); };
  }, [countrySearch, countryDefaultOptions]);

  // 点击外部关闭国家下拉
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (countryRef.current && !countryRef.current.contains(e.target as Node)) {
        setShowCountryDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);
  const [aiError, setAiError] = useState('');

  // AI 草稿创建（异步：立即创建客户，后台 AI 搜索）
  const handleAiLookup = async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiError('');
    try {
      await customersApi.aiCreateDraft(aiQuery.trim());
      toast.success('已创建草稿客户，AI 正在后台搜索中...');
      onDraftCreated?.();
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'AI 草稿创建失败');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 清理空字符串为 undefined（用于 update）
    const cleaned: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(form)) {
      if (value === '' || value === null) {
        // 保留 name（必填）和 is_active（布尔）
        if (key === 'name' || key === 'is_active' || key === 'customer_level') {
          cleaned[key] = value;
        }
      } else {
        cleaned[key] = value;
      }
    }
    onSubmit(cleaned as unknown as CustomerCreate);
  };

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.tags!.includes(tag)) {
      setForm({ ...form, tags: [...(form.tags || []), tag] });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setForm({ ...form, tags: (form.tags || []).filter(t => t !== tag) });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* AI 客户检索 */}
      {isCreateMode && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <Label className="mb-1">AI 智能建档</Label>
          <div className="flex items-center gap-2">
            <Input
              type="text"
              className="flex-1"
              placeholder="输入公司名称，AI 将在后台自动搜索并创建草稿客户"
              value={aiQuery}
              onChange={e => setAiQuery(e.target.value)}
            />
            <Button
              type="button"
              onClick={handleAiLookup}
              disabled={aiLoading || !aiQuery.trim()}
              className="bg-purple-600 hover:bg-purple-700 whitespace-nowrap"
            >
              {aiLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  创建中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  AI 创建草稿
                </>
              )}
            </Button>
          </div>
          {aiError && (
            <p className="mt-1 text-xs text-destructive">{aiError}</p>
          )}
        </div>
      )}

      {/* 基本信息 */}
      <FormSection title="基本信息">
        <div className="grid grid-cols-4 gap-4">
          {/* 公司全称 50% + 简称 25% + 客户等级 25% */}
          <div className="col-span-2">
            <Label className="mb-1">公司全称 *</Label>
            <Input
              type="text"
              required
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div className="col-span-1">
            <Label className="mb-1">简称</Label>
            <Input
              type="text"
              value={form.short_name || ''}
              onChange={e => setForm({ ...form, short_name: e.target.value })}
            />
          </div>
          <div className="col-span-1">
            <Label className="mb-1">客户等级</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.customer_level}
              onChange={e => setForm({ ...form, customer_level: e.target.value })}
            >
              {Object.entries(CUSTOMER_LEVELS).map(([value, { label }]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          {/* 国家 25% + 地区 25% + 行业 50% */}
          <div ref={countryRef} className="col-span-1 relative">
            <Label className="mb-1">国家</Label>
            <Input
              type="text"
              placeholder="搜索国家..."
              value={countrySearch}
              className={!countryValid ? 'border-red-400 focus-visible:ring-red-400' : ''}
              onChange={e => {
                const val = e.target.value;
                setCountrySearch(val);
                setForm({ ...form, country: val });
                setCountryValid(!val.trim());
                setShowCountryDropdown(true);
              }}
              onFocus={() => {
                loadDefaultCountries();
                setShowCountryDropdown(true);
              }}
            />
            {!countryValid && (
              <p className="text-xs text-red-500 mt-1">请从下拉列表中选择</p>
            )}
            {showCountryDropdown && (countryLoading || countryOptions.length > 0) && (
              <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-popover border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {countryLoading ? (
                  <div className="px-3 py-2 text-sm text-muted-foreground">搜索中...</div>
                ) : (
                  countryOptions.map(c => (
                    <button
                      key={c.id}
                      type="button"
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors ${
                        form.country === c.name_zh ? 'text-blue-600 font-medium bg-blue-50 dark:bg-blue-950/20' : ''
                      }`}
                      onClick={() => {
                        setForm({ ...form, country: c.name_zh, region: c.full_name_zh || form.region });
                        setCountrySearch(c.name_zh);
                        setCountryValid(true);
                        setShowCountryDropdown(false);
                      }}
                    >
                      <span>{c.name_zh}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{c.name_en}</span>
                      <span className="ml-1 text-xs text-muted-foreground/60">({c.iso_code_2})</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
          <div className="col-span-1">
            <Label className="mb-1">地区</Label>
            <Input
              type="text"
              value={form.region || ''}
              onChange={e => setForm({ ...form, region: e.target.value })}
            />
          </div>
          <div className="col-span-2">
            <Label className="mb-1">行业</Label>
            <Input
              type="text"
              value={form.industry || ''}
              onChange={e => setForm({ ...form, industry: e.target.value })}
            />
          </div>
        </div>
      </FormSection>

      {/* 业务信息 */}
      <FormSection title="业务信息">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">公司规模</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.company_size || ''}
              onChange={e => setForm({ ...form, company_size: e.target.value })}
            >
              <option value="">未设置</option>
              <option value="small">小型</option>
              <option value="medium">中型</option>
              <option value="large">大型</option>
              <option value="enterprise">企业级</option>
            </select>
          </div>
          <div>
            <Label className="mb-1">年营收范围</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.annual_revenue || ''}
              onChange={e => setForm({ ...form, annual_revenue: e.target.value })}
            >
              <option value="">未设置</option>
              <option value="<1M">{'< $1M'}</option>
              <option value="1M-10M">$1M - $10M</option>
              <option value="10M-50M">$10M - $50M</option>
              <option value=">50M">{'> $50M'}</option>
            </select>
          </div>
          <div>
            <Label className="mb-1">客户来源</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.source || ''}
              onChange={e => setForm({ ...form, source: e.target.value })}
            >
              <option value="">未设置</option>
              <option value="email">邮件</option>
              <option value="exhibition">展会</option>
              <option value="referral">转介绍</option>
              <option value="website">网站</option>
              <option value="other">其他</option>
            </select>
          </div>
          <div className="flex items-end">
            <div className="flex items-center space-x-2 cursor-pointer">
              <Checkbox
                id="is_active"
                checked={form.is_active}
                onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })}
              />
              <Label htmlFor="is_active" className="cursor-pointer">活跃客户</Label>
            </div>
          </div>
        </div>
      </FormSection>

      {/* 联系信息 */}
      <FormSection title="联系信息">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">公司邮箱</Label>
            <Input
              type="email"
              value={form.email || ''}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司电话</Label>
            <Input
              type="text"
              value={form.phone || ''}
              onChange={e => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司网站</Label>
            <Input
              type="text"
              value={form.website || ''}
              onChange={e => setForm({ ...form, website: e.target.value })}
            />
          </div>
          <div>
            <Label className="mb-1">公司地址</Label>
            <Input
              type="text"
              value={form.address || ''}
              onChange={e => setForm({ ...form, address: e.target.value })}
            />
          </div>
        </div>
      </FormSection>

      {/* 贸易信息 */}
      <FormSection title="贸易信息">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1">付款条款</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.payment_terms || ''}
              onChange={e => setForm({ ...form, payment_terms: e.target.value })}
            >
              <option value="">请选择付款方式</option>
              {paymentMethods.map(pm => (
                <option key={pm.id} value={pm.code}>{pm.code} - {pm.name_zh}</option>
              ))}
            </select>
          </div>
          <div>
            <Label className="mb-1">贸易术语 (Incoterms)</Label>
            <select
              className={`w-full ${selectClass}`}
              value={form.shipping_terms || ''}
              onChange={e => setForm({ ...form, shipping_terms: e.target.value })}
            >
              <option value="">未设置</option>
              {tradeTerms.map(t => (
                <option key={t.id} value={t.code}>
                  {t.code} - {t.name_zh}
                </option>
              ))}
            </select>
          </div>
        </div>
      </FormSection>

      {/* 其他 */}
      <FormSection title="其他">
        <div className="space-y-4">
          <div>
            <Label className="mb-1">标签</Label>
            <div className="flex items-center gap-2 mb-2">
              <Input
                type="text"
                placeholder="输入标签后按回车或点击添加"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addTag}
                className="whitespace-nowrap"
              >
                添加
              </Button>
            </div>
            {form.tags && form.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {form.tags.map(tag => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="bg-blue-100 text-blue-800"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="ml-1 hover:text-blue-900"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <Label className="mb-1">备注</Label>
            <Textarea
              rows={3}
              value={form.notes || ''}
              onChange={e => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </FormSection>

      {/* 按钮 */}
      <Separator />
      <div className="flex justify-end space-x-3 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="submit"
          disabled={loading || !form.name.trim() || !countryValid}
        >
          {loading ? '保存中...' : '保存'}
        </Button>
      </div>
    </form>
  );
}

// ==================== 客户详情弹窗 ====================

function CustomerDetailModal({
  isOpen,
  onClose,
  customer,
}: {
  isOpen: boolean;
  onClose: () => void;
  customer: Customer | null;
}) {
  const { can } = usePermission();
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [creatingContact, setCreatingContact] = useState(false);
  const [savingContact, setSavingContact] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!customer) return;
    setLoading(true);
    try {
      const d = await customersApi.get(customer.id);
      setDetail(d);
    } catch (err) {
      console.error('加载客户详情失败:', err);
    } finally {
      setLoading(false);
    }
  }, [customer]);

  useEffect(() => {
    if (isOpen && customer) {
      loadDetail();
      setCreatingContact(false);
    } else {
      setDetail(null);
    }
  }, [isOpen, customer, loadDetail]);

  const handleCreateContact = async (data: ContactCreate) => {
    setSavingContact(true);
    try {
      await contactsApi.create(data);
      setCreatingContact(false);
      await loadDetail();
    } catch (err) {
      toast.error('创建联系人失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSavingContact(false);
    }
  };

  if (!customer) return null;

  const data = detail || customer;
  const level = CUSTOMER_LEVELS[data.customer_level] || CUSTOMER_LEVELS.normal;

  const COMPANY_SIZE_LABELS: Record<string, string> = {
    small: '小型',
    medium: '中型',
    large: '大型',
    enterprise: '企业级',
  };

  const REVENUE_LABELS: Record<string, string> = {
    '<1M': '< $1M',
    '1M-10M': '$1M - $10M',
    '10M-50M': '$10M - $50M',
    '>50M': '> $50M',
  };

  const SOURCE_LABELS: Record<string, string> = {
    email: '邮件',
    exhibition: '展会',
    referral: '转介绍',
    website: '网站',
    other: '其他',
  };

  // 只读字段：模拟 Label + Input 的视觉，但用文本展示
  const ReadonlyField = ({ label, value, className }: { label: string; value?: React.ReactNode; className?: string }) => (
    <div className={className}>
      <Label className="mb-1">{label}</Label>
      <div className="px-3 py-2 border border-input rounded-md bg-muted/50 text-sm min-h-[38px] flex items-center">
        {value || <span className="text-muted-foreground">-</span>}
      </div>
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{`客户详情 - ${data.name}`}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : (
          <div className="space-y-6">
            {/* 基本信息 — 与表单一致：grid-cols-4 */}
            <FormSection title="基本信息">
              <div className="grid grid-cols-4 gap-4">
                <ReadonlyField className="col-span-2" label="公司全称" value={data.name} />
                <ReadonlyField className="col-span-1" label="简称" value={data.short_name} />
                <ReadonlyField className="col-span-1" label="客户等级" value={
                  <Badge variant="secondary" className={level.color}>{level.label}</Badge>
                } />
                <ReadonlyField className="col-span-1" label="国家" value={data.country} />
                <ReadonlyField className="col-span-1" label="地区" value={data.region} />
                <ReadonlyField className="col-span-2" label="行业" value={data.industry} />
              </div>
            </FormSection>

            {/* 业务信息 — 与表单一致：grid-cols-2 */}
            <FormSection title="业务信息">
              <div className="grid grid-cols-2 gap-4">
                <ReadonlyField label="公司规模" value={data.company_size ? (COMPANY_SIZE_LABELS[data.company_size] || data.company_size) : undefined} />
                <ReadonlyField label="年营收范围" value={data.annual_revenue ? (REVENUE_LABELS[data.annual_revenue] || data.annual_revenue) : undefined} />
                <ReadonlyField label="客户来源" value={data.source ? (SOURCE_LABELS[data.source] || data.source) : undefined} />
                <div className="flex items-end">
                  <div className="flex items-center space-x-2">
                    <Checkbox id="detail-is-active" checked={data.is_active} disabled />
                    <Label htmlFor="detail-is-active" className="text-muted-foreground">活跃客户</Label>
                  </div>
                </div>
              </div>
            </FormSection>

            {/* 联系信息 — 与表单一致：grid-cols-2 */}
            <FormSection title="联系信息">
              <div className="grid grid-cols-2 gap-4">
                <ReadonlyField label="公司邮箱" value={data.email} />
                <ReadonlyField label="公司电话" value={data.phone} />
                <ReadonlyField label="公司网站" value={data.website} />
                <ReadonlyField label="公司地址" value={data.address} />
              </div>
            </FormSection>

            {/* 贸易信息 — 与表单一致：grid-cols-2 */}
            <FormSection title="贸易信息">
              <div className="grid grid-cols-2 gap-4">
                <ReadonlyField label="付款条款" value={data.payment_terms} />
                <ReadonlyField label="贸易术语 (Incoterms)" value={data.shipping_terms} />
              </div>
            </FormSection>

            {/* 其他 — 与表单一致：标签 + 备注 */}
            <FormSection title="其他">
              <div className="space-y-4">
                <div>
                  <Label className="mb-1">标签</Label>
                  {data.tags && data.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-2 mt-1">
                      {data.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="bg-blue-100 text-blue-800">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <div className="px-3 py-2 border border-input rounded-md bg-muted/50 text-sm text-muted-foreground min-h-[38px] flex items-center">-</div>
                  )}
                </div>
                <div>
                  <Label className="mb-1">备注</Label>
                  <div className="px-3 py-2 border border-input rounded-md bg-muted/50 text-sm min-h-[76px] whitespace-pre-wrap">
                    {data.notes || <span className="text-muted-foreground">-</span>}
                  </div>
                </div>
              </div>
            </FormSection>

            {/* 联系人列表 */}
            <FormSection title={`联系人 (${detail?.contacts?.length ?? data.contact_count})`}>
              <div className="flex justify-end mb-2">
                {can('customer', 'create') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCreatingContact(true)}
                  disabled={creatingContact}
                >
                  <Plus className="h-4 w-4" />
                  添加联系人
                </Button>
                )}
              </div>
              {creatingContact && (
                <Card className="py-4 mb-2">
                  <CardContent>
                    <h4 className="text-sm font-medium text-foreground mb-3">新建联系人</h4>
                    <ContactForm
                      customerId={customer.id}
                      onSubmit={(data) => handleCreateContact(data as ContactCreate)}
                      onCancel={() => setCreatingContact(false)}
                      loading={savingContact}
                    />
                  </CardContent>
                </Card>
              )}
              {detail?.contacts && detail.contacts.length > 0 ? (
                <div className="space-y-2">
                  {detail.contacts.map(contact => (
                    <Card key={contact.id} className="py-3">
                      <CardContent className="p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm text-foreground">{contact.name}</span>
                          {contact.is_primary && (
                            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">主联系人</Badge>
                          )}
                          {!contact.is_active && (
                            <Badge variant="secondary" className="bg-gray-200 text-muted-foreground">已停用</Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-x-6 text-xs text-muted-foreground mt-1">
                          <div>职位: {contact.title || '-'}</div>
                          <div>部门: {contact.department || '-'}</div>
                          <div>邮箱: {contact.email || '-'}</div>
                          <div>座机: {contact.phone || '-'}</div>
                          <div>手机: {contact.mobile || '-'}</div>
                        </div>
                        {contact.notes && (
                          <div className="text-xs text-muted-foreground mt-1">备注: {contact.notes}</div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                !creatingContact && <p className="text-sm text-muted-foreground">暂无联系人</p>
              )}
            </FormSection>

            {/* 时间信息 */}
            <Separator />
            <div className="text-xs text-muted-foreground flex gap-6">
              <span>创建时间: {formatDateTime(data.created_at)}</span>
              <span>更新时间: {data.updated_at ? formatDateTime(data.updated_at) : '-'}</span>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==================== 联系人管理弹窗 ====================

function ContactsModal({
  isOpen,
  onClose,
  customer,
}: {
  isOpen: boolean;
  onClose: () => void;
  customer: Customer | null;
}) {
  const { can } = usePermission();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Contact | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadContacts = useCallback(async () => {
    if (!customer) return;
    setLoading(true);
    try {
      const res = await contactsApi.list({ customer_id: customer.id, page_size: 100 });
      setContacts(res.items);
    } catch (err) {
      console.error('加载联系人失败:', err);
    } finally {
      setLoading(false);
    }
  }, [customer]);

  useEffect(() => {
    if (isOpen && customer) {
      loadContacts();
      setEditing(null);
      setCreating(false);
    }
  }, [isOpen, customer, loadContacts]);

  const handleCreate = async (data: ContactCreate) => {
    setSaving(true);
    try {
      await contactsApi.create(data);
      await loadContacts();
      setCreating(false);
    } catch (err) {
      toast.error('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (id: string, data: ContactUpdate) => {
    setSaving(true);
    try {
      await contactsApi.update(id, data);
      await loadContacts();
      setEditing(null);
    } catch (err) {
      toast.error('更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const confirm = useConfirm();

  const handleDelete = async (contact: Contact) => {
    const confirmed = await confirm({
      title: '删除联系人',
      description: `确定要删除联系人「${contact.name}」吗？`,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await contactsApi.delete(contact.id);
      await loadContacts();
    } catch (err) {
      toast.error('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  if (!customer) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{`${customer.name} - 联系人管理`}</DialogTitle>
        </DialogHeader>
        {/* 工具栏 */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">共 {contacts.length} 位联系人</span>
          {can('customer', 'create') && (
          <Button
            size="sm"
            onClick={() => { setCreating(true); setEditing(null); }}
          >
            <Plus className="h-4 w-4" />
            添加联系人
          </Button>
          )}
        </div>

        {/* 创建表单 */}
        {creating && (
          <Card className="py-4">
            <CardContent>
              <h4 className="text-sm font-medium text-foreground mb-3">新建联系人</h4>
              <ContactForm
                customerId={customer.id}
                onSubmit={(data) => handleCreate(data as ContactCreate)}
                onCancel={() => setCreating(false)}
                loading={saving}
              />
            </CardContent>
          </Card>
        )}

        {/* 联系人列表 */}
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner text="加载中..." />
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">暂无联系人</div>
        ) : (
          <div className="space-y-3">
            {contacts.map(contact => (
              <Card key={contact.id} className="py-4">
                <CardContent>
                  {editing?.id === contact.id ? (
                    <ContactForm
                      customerId={customer.id}
                      initial={contact}
                      onSubmit={(data) => handleUpdate(contact.id, data as ContactUpdate)}
                      onCancel={() => setEditing(null)}
                      loading={saving}
                    />
                  ) : (
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-foreground">{contact.name}</span>
                          {contact.is_primary && (
                            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">主联系人</Badge>
                          )}
                          {!contact.is_active && (
                            <Badge variant="secondary" className="bg-gray-100 text-muted-foreground">已停用</Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground space-y-0.5">
                          {contact.title && <div>{contact.title}{contact.department ? ` - ${contact.department}` : ''}</div>}
                          {contact.email && <div>邮箱: {contact.email}</div>}
                          {contact.phone && <div>座机: {contact.phone}</div>}
                          {contact.mobile && <div>手机: {contact.mobile}</div>}
                          {contact.notes && <div className="text-muted-foreground/60 mt-1">{contact.notes}</div>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        {can('customer', 'update') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setEditing(contact); setCreating(false); }}
                        >
                          <Pencil className="h-4 w-4" />
                          编辑
                        </Button>
                        )}
                        {can('customer', 'delete') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(contact)}
                        >
                          <Trash2 className="h-4 w-4" />
                          删除
                        </Button>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==================== 联系人表单 ====================

function ContactForm({
  customerId,
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  customerId: string;
  initial?: Partial<Contact>;
  onSubmit: (data: ContactCreate | ContactUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    title: initial?.title || '',
    department: initial?.department || '',
    email: initial?.email || '',
    phone: initial?.phone || '',
    mobile: initial?.mobile || '',
    is_primary: initial?.is_primary ?? false,
    is_active: initial?.is_active ?? true,
    notes: initial?.notes || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, unknown> = { ...form };
    if (!initial) {
      // 创建模式，需要 customer_id
      data.customer_id = customerId;
    }
    // 清理空字符串
    for (const key of Object.keys(data)) {
      if (data[key] === '' && key !== 'name') {
        delete data[key];
      }
    }
    onSubmit(data as unknown as ContactCreate);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <Label className="text-xs mb-1">姓名 *</Label>
          <Input
            type="text"
            required
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <Label className="text-xs mb-1">职位</Label>
          <Input
            type="text"
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <Label className="text-xs mb-1">部门</Label>
          <Input
            type="text"
            value={form.department}
            onChange={e => setForm({ ...form, department: e.target.value })}
          />
        </div>
        <div>
          <Label className="text-xs mb-1">邮箱</Label>
          <Input
            type="email"
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
          />
        </div>
        <div>
          <Label className="text-xs mb-1">座机</Label>
          <Input
            type="text"
            value={form.phone}
            onChange={e => setForm({ ...form, phone: e.target.value })}
          />
        </div>
        <div>
          <Label className="text-xs mb-1">手机</Label>
          <Input
            type="text"
            value={form.mobile}
            onChange={e => setForm({ ...form, mobile: e.target.value })}
          />
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-1.5 cursor-pointer">
          <Checkbox
            id={`contact-primary-${initial?.id || 'new'}`}
            checked={form.is_primary}
            onCheckedChange={(checked) => setForm({ ...form, is_primary: !!checked })}
          />
          <Label htmlFor={`contact-primary-${initial?.id || 'new'}`} className="cursor-pointer text-sm">主联系人</Label>
        </div>
        <div className="flex items-center gap-1.5 cursor-pointer">
          <Checkbox
            id={`contact-active-${initial?.id || 'new'}`}
            checked={form.is_active}
            onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })}
          />
          <Label htmlFor={`contact-active-${initial?.id || 'new'}`} className="cursor-pointer text-sm">活跃</Label>
        </div>
      </div>
      <div>
        <Label className="text-xs mb-1">备注</Label>
        <Input
          type="text"
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="submit"
          size="sm"
          disabled={loading || !form.name.trim()}
        >
          {loading ? '保存中...' : '保存'}
        </Button>
      </div>
    </form>
  );
}

// ==================== 建议审批状态配置 ====================

const SUGGESTION_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: '待审批', color: 'bg-yellow-100 text-yellow-800' },
  approved: { label: '已通过', color: 'bg-green-100 text-green-800' },
  rejected: { label: '已拒绝', color: 'bg-red-100 text-red-800' },
};

const SUGGESTION_TYPE: Record<string, { label: string; color: string }> = {
  new_customer: { label: '新客户', color: 'bg-blue-100 text-blue-800' },
  new_contact: { label: '新联系人', color: 'bg-purple-100 text-purple-800' },
};

// ==================== 建议审批弹窗 ====================

function SuggestionReviewModal({
  isOpen,
  onClose,
  suggestion,
  onApproved,
}: {
  isOpen: boolean;
  onClose: () => void;
  suggestion: CustomerSuggestion | null;
  onApproved: () => void;
}) {
  const [form, setForm] = useState<CustomerReviewData>({});
  const [loading, setLoading] = useState(false);
  const confirm = useConfirm();

  useEffect(() => {
    if (suggestion) {
      setForm({
        company_name: suggestion.suggested_company_name,
        short_name: suggestion.suggested_short_name || '',
        country: suggestion.suggested_country || '',
        region: suggestion.suggested_region || '',
        industry: suggestion.suggested_industry || '',
        website: suggestion.suggested_website || '',
        customer_level: suggestion.suggested_customer_level,
        tags: suggestion.suggested_tags || [],
        contact_name: suggestion.suggested_contact_name || '',
        contact_email: suggestion.suggested_contact_email || '',
        contact_title: suggestion.suggested_contact_title || '',
        contact_phone: suggestion.suggested_contact_phone || '',
        contact_department: suggestion.suggested_contact_department || '',
        note: '',
      });
    }
  }, [suggestion]);

  if (!suggestion) return null;

  const handleApprove = async () => {
    setLoading(true);
    try {
      await customerSuggestionsApi.approve(suggestion.id, form);
      onApproved();
      onClose();
    } catch (err) {
      toast.error('审批失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    const confirmed = await confirm({
      title: '拒绝建议',
      description: '确定要拒绝此建议吗？',
      variant: 'destructive',
    });
    if (!confirmed) return;
    setLoading(true);
    try {
      await customerSuggestionsApi.reject(suggestion.id, form.note);
      onApproved();
      onClose();
    } catch (err) {
      toast.error('拒绝失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const typeInfo = SUGGESTION_TYPE[suggestion.suggestion_type] || SUGGESTION_TYPE.new_customer;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>审核客户建议</DialogTitle>
        </DialogHeader>

        {/* AI 分析信息 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-4 mb-2">
            <Badge variant="secondary" className={typeInfo.color}>
              {typeInfo.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              置信度: <strong className="text-blue-700">{(suggestion.confidence * 100).toFixed(0)}%</strong>
            </span>
            {suggestion.email_domain && (
              <span className="text-sm text-muted-foreground">域名: {suggestion.email_domain}</span>
            )}
          </div>
          {suggestion.reasoning && (
            <p className="text-sm text-foreground mt-2">{suggestion.reasoning}</p>
          )}
          {suggestion.trigger_content && (
            <details className="mt-2">
              <summary className="text-xs text-muted-foreground cursor-pointer">查看触发内容</summary>
              <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">{suggestion.trigger_content}</p>
            </details>
          )}
        </div>

        {/* 可编辑表单 */}
        <div className="space-y-6">
          {/* 客户信息 */}
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3">客户信息</h4>
            <Separator className="mb-3" />
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="mb-1">公司名称</Label>
                <Input
                  type="text"
                  value={form.company_name || ''}
                  onChange={e => setForm({ ...form, company_name: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">简称</Label>
                <Input
                  type="text"
                  value={form.short_name || ''}
                  onChange={e => setForm({ ...form, short_name: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">国家</Label>
                <Input
                  type="text"
                  value={form.country || ''}
                  onChange={e => setForm({ ...form, country: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">地区</Label>
                <Input
                  type="text"
                  value={form.region || ''}
                  onChange={e => setForm({ ...form, region: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">行业</Label>
                <Input
                  type="text"
                  value={form.industry || ''}
                  onChange={e => setForm({ ...form, industry: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">网站</Label>
                <Input
                  type="text"
                  value={form.website || ''}
                  onChange={e => setForm({ ...form, website: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">客户等级</Label>
                <select
                  className={`w-full ${selectClass}`}
                  value={form.customer_level || 'potential'}
                  onChange={e => setForm({ ...form, customer_level: e.target.value })}
                >
                  {Object.entries(CUSTOMER_LEVELS).map(([value, { label }]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* 联系人信息 */}
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3">联系人信息</h4>
            <Separator className="mb-3" />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">姓名</Label>
                <Input
                  type="text"
                  value={form.contact_name || ''}
                  onChange={e => setForm({ ...form, contact_name: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">邮箱</Label>
                <Input
                  type="email"
                  value={form.contact_email || ''}
                  onChange={e => setForm({ ...form, contact_email: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">职位</Label>
                <Input
                  type="text"
                  value={form.contact_title || ''}
                  onChange={e => setForm({ ...form, contact_title: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">部门</Label>
                <Input
                  type="text"
                  value={form.contact_department || ''}
                  onChange={e => setForm({ ...form, contact_department: e.target.value })}
                />
              </div>
              <div>
                <Label className="mb-1">电话</Label>
                <Input
                  type="text"
                  value={form.contact_phone || ''}
                  onChange={e => setForm({ ...form, contact_phone: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* 审核备注 */}
          <div>
            <Label className="mb-1">审核备注</Label>
            <Textarea
              rows={2}
              placeholder="可选，填写审核意见..."
              value={form.note || ''}
              onChange={e => setForm({ ...form, note: e.target.value })}
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <Separator />
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleReject}
            disabled={loading}
          >
            {loading ? '处理中...' : '拒绝'}
          </Button>
          <Button
            onClick={handleApprove}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700"
          >
            {loading ? '处理中...' : '通过'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ==================== 待审批客户 Tab ====================

function CustomerSuggestionsTab() {
  const [suggestions, setSuggestions] = useState<CustomerSuggestion[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const [reviewingSuggestion, setReviewingSuggestion] = useState<CustomerSuggestion | null>(null);
  const pageSize = 20;

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await customerSuggestionsApi.list({
        page,
        page_size: pageSize,
        status: filterStatus || undefined,
      });
      setSuggestions(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('加载客户建议失败:', err);
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      {/* 状态筛选 */}
      <Card className="py-4 mb-6">
        <CardContent>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">状态筛选:</span>
            <div className="flex items-center gap-2">
              {[
                { value: 'pending', label: '待审批' },
                { value: 'approved', label: '已通过' },
                { value: 'rejected', label: '已拒绝' },
                { value: '', label: '全部' },
              ].map(opt => (
                <Button
                  key={opt.value}
                  size="sm"
                  variant={filterStatus === opt.value ? 'default' : 'outline'}
                  onClick={() => { setFilterStatus(opt.value); setPage(1); }}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 建议列表 */}
      <Card className="py-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="px-6">公司名称</TableHead>
              <TableHead className="px-6">联系人</TableHead>
              <TableHead className="px-6">类型</TableHead>
              <TableHead className="px-6">置信度</TableHead>
              <TableHead className="px-6">状态</TableHead>
              <TableHead className="px-6">创建时间</TableHead>
              <TableHead className="px-6 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="px-6 py-12 text-center">
                  <LoadingSpinner text="加载中..." />
                </TableCell>
              </TableRow>
            ) : suggestions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="px-6 py-12 text-center text-muted-foreground">暂无建议数据</TableCell>
              </TableRow>
            ) : (
              suggestions.map(s => {
                const statusInfo = SUGGESTION_STATUS[s.status] || SUGGESTION_STATUS.pending;
                const typeInfo = SUGGESTION_TYPE[s.suggestion_type] || SUGGESTION_TYPE.new_customer;
                return (
                  <TableRow key={s.id}>
                    <TableCell className="px-6 py-4">
                      <div className="text-sm font-medium text-foreground">{s.suggested_company_name}</div>
                      {s.suggested_country && (
                        <div className="text-xs text-muted-foreground">{s.suggested_country}</div>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <div className="text-sm text-foreground">{s.suggested_contact_name || '-'}</div>
                      {s.suggested_contact_email && (
                        <div className="text-xs text-muted-foreground">{s.suggested_contact_email}</div>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <Badge variant="secondary" className={typeInfo.color}>
                        {typeInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <span className={`text-sm font-medium ${
                        s.confidence >= 0.8 ? 'text-green-600' :
                        s.confidence >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(s.confidence * 100).toFixed(0)}%
                      </span>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <Badge variant="secondary" className={statusInfo.color}>
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                      {formatDateTime(s.created_at)}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-right">
                      {s.status === 'pending' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setReviewingSuggestion(s)}
                        >
                          审核
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setReviewingSuggestion(s)}
                        >
                          查看
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t">
            <div className="text-sm text-muted-foreground">
              共 {total} 条，第 {page}/{totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                下一页
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* 审核弹窗 */}
      <SuggestionReviewModal
        isOpen={!!reviewingSuggestion}
        onClose={() => setReviewingSuggestion(null)}
        suggestion={reviewingSuggestion}
        onApproved={loadSuggestions}
      />
    </>
  );
}

// ==================== 移动端客户卡片 ====================

function CustomerCard({
  customer,
  onView,
  onEdit,
  onDelete,
  onContacts,
}: {
  customer: Customer;
  onView: (c: Customer) => void;
  onEdit: (c: Customer) => void;
  onDelete: (c: Customer) => void;
  onContacts: (c: Customer) => void;
}) {
  const { can } = usePermission();
  const level = CUSTOMER_LEVELS[customer.customer_level] || CUSTOMER_LEVELS.normal;

  return (
    <Card className="p-4 space-y-2">
      {/* 第一行：公司名称 + 等级/状态 */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-sm font-medium text-foreground">{customer.name}</span>
            {customer.ai_status === 'searching' && (
              <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-xs gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                AI 搜索中
              </Badge>
            )}
            {customer.ai_status === 'completed' && (
              <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-xs">AI</Badge>
            )}
            {customer.ai_status === 'failed' && (
              <Badge variant="secondary" className="bg-red-100 text-red-700 text-xs">AI 失败</Badge>
            )}
          </div>
          {customer.short_name && (
            <div className="text-xs text-muted-foreground truncate">{customer.short_name}</div>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <Badge variant="secondary" className={level.color}>{level.label}</Badge>
          <Badge variant="secondary" className={
            customer.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-muted-foreground'
          }>
            {customer.is_active ? '活跃' : '停用'}
          </Badge>
        </div>
      </div>

      {/* 第二行：国家 + 联系人 + 时间 */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{customer.country || '-'}</span>
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-0.5">
            <Users className="h-3 w-3" />
            {customer.contact_count} 人
          </span>
          <span>{formatDateTime(customer.created_at)}</span>
        </span>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2 pt-1 border-t">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(customer)}
          className="flex-1 text-blue-600 hover:text-blue-900 h-8 text-xs"
        >
          <Eye className="h-3.5 w-3.5 mr-1" />
          查看
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onContacts(customer)}
          className="flex-1 text-purple-600 hover:text-purple-900 h-8 text-xs"
        >
          <Users className="h-3.5 w-3.5 mr-1" />
          联系人
        </Button>
        {can('customer', 'update') && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(customer)}
          className="flex-1 text-orange-600 hover:text-orange-900 h-8 text-xs"
        >
          <Pencil className="h-3.5 w-3.5 mr-1" />
          编辑
        </Button>
        )}
        {can('customer', 'delete') && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(customer)}
          className="flex-1 text-destructive hover:text-destructive h-8 text-xs"
        >
          <Trash2 className="h-3.5 w-3.5 mr-1" />
          删除
        </Button>
        )}
      </div>
    </Card>
  );
}

// ==================== 主页面 ====================

export default function CustomersPage() {
  const { isMobile } = useDevice();
  const { can } = usePermission();

  // Tab 状态
  const [activeTab, setActiveTab] = useState<string>('list');

  // 数据状态
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 筛选/搜索
  const [search, setSearch] = useState('');
  const [filterLevel, setFilterLevel] = useState('');
  const [filterActive, setFilterActive] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 弹窗状态
  const [showCreate, setShowCreate] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [contactsCustomer, setContactsCustomer] = useState<Customer | null>(null);
  const [viewingCustomer, setViewingCustomer] = useState<Customer | null>(null);
  const [saving, setSaving] = useState(false);

  const confirm = useConfirm();

  // 加载客户列表
  const loadCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (search) params.search = search;
      if (filterLevel) params.customer_level = filterLevel;
      if (filterActive === 'true') params.is_active = true;
      if (filterActive === 'false') params.is_active = false;

      const res = await customersApi.list(params as Parameters<typeof customersApi.list>[0]);
      setCustomers(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('加载客户列表失败:', err);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterLevel, filterActive]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  // 搜索防抖
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // 当有 AI 搜索中的客户时，自动轮询刷新
  const hasSearching = customers.some(c => c.ai_status === 'searching');
  useEffect(() => {
    if (!hasSearching) return;
    const timer = setInterval(() => {
      loadCustomers();
    }, 8000);
    return () => clearInterval(timer);
  }, [hasSearching, loadCustomers]);

  // CRUD 操作
  const handleCreate = async (data: CustomerCreate | CustomerUpdate) => {
    setSaving(true);
    try {
      await customersApi.create(data as CustomerCreate);
      setShowCreate(false);
      await loadCustomers();
    } catch (err) {
      toast.error('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (data: CustomerCreate | CustomerUpdate) => {
    if (!editingCustomer) return;
    setSaving(true);
    try {
      await customersApi.update(editingCustomer.id, data as CustomerUpdate);
      setEditingCustomer(null);
      await loadCustomers();
    } catch (err) {
      toast.error('更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (customer: Customer) => {
    const msg = customer.contact_count > 0
      ? `确定要删除客户「${customer.name}」吗？该客户有 ${customer.contact_count} 个联系人，将一并删除。`
      : `确定要删除客户「${customer.name}」吗？`;
    const confirmed = await confirm({
      title: '删除客户',
      description: msg,
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await customersApi.delete(customer.id);
      await loadCustomers();
    } catch (err) {
      toast.error('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-foreground">客户管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理公司客户及联系人信息</p>
        </div>
        {activeTab === 'list' && can('customer', 'create') && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            新建客户
          </Button>
        )}
      </div>

      {/* Tab 切换 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="list">客户列表</TabsTrigger>
          <TabsTrigger value="suggestions">待审批客户</TabsTrigger>
        </TabsList>

        <TabsContent value="suggestions">
          <CustomerSuggestionsTab />
        </TabsContent>

        <TabsContent value="list">
          {/* 搜索和筛选 */}
          <Card className="p-4 mb-6">
            <div className="flex flex-col md:flex-row gap-3 md:gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="搜索公司名称、简称、邮箱..."
                  className="pl-9"
                  value={searchInput}
                  onChange={e => setSearchInput(e.target.value)}
                />
              </div>
              <div className="flex gap-3">
                <select
                  className={`flex-1 md:flex-none ${selectClass}`}
                  value={filterLevel}
                  onChange={e => { setFilterLevel(e.target.value); setPage(1); }}
                >
                  <option value="">全部等级</option>
                  {Object.entries(CUSTOMER_LEVELS).map(([value, { label }]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
                <select
                  className={`flex-1 md:flex-none ${selectClass}`}
                  value={filterActive}
                  onChange={e => { setFilterActive(e.target.value); setPage(1); }}
                >
                  <option value="">全部状态</option>
                  <option value="true">活跃</option>
                  <option value="false">停用</option>
                </select>
              </div>
            </div>
          </Card>

          {/* 客户列表 */}
          {isMobile ? (
            /* ==================== 移动端：卡片列表 ==================== */
            <div className="space-y-3">
              {loading ? (
                <div className="py-8 text-center">
                  <LoadingSpinner text="加载中..." />
                </div>
              ) : customers.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  {search || filterLevel || filterActive ? '没有匹配的客户' : '暂无客户数据'}
                </div>
              ) : (
                customers.map(customer => (
                  <CustomerCard
                    key={customer.id}
                    customer={customer}
                    onView={setViewingCustomer}
                    onEdit={setEditingCustomer}
                    onDelete={handleDelete}
                    onContacts={setContactsCustomer}
                  />
                ))
              )}

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-muted-foreground">{page}/{totalPages} 页，共 {total} 条</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>上一页</Button>
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>下一页</Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ==================== 桌面端：表格 ==================== */
            <Card className="py-0 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="px-6">公司名称</TableHead>
                    <TableHead className="px-6">国家</TableHead>
                    <TableHead className="px-6">等级</TableHead>
                    <TableHead className="px-6">联系人</TableHead>
                    <TableHead className="px-6">状态</TableHead>
                    <TableHead className="px-6">创建时间</TableHead>
                    <TableHead className="px-6 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="px-6 py-12 text-center">
                        <LoadingSpinner text="加载中..." />
                      </TableCell>
                    </TableRow>
                  ) : customers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="px-6 py-12 text-center text-muted-foreground">
                        {search || filterLevel || filterActive ? '没有匹配的客户' : '暂无客户数据'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    customers.map(customer => {
                      const level = CUSTOMER_LEVELS[customer.customer_level] || CUSTOMER_LEVELS.normal;
                      return (
                        <TableRow key={customer.id}>
                          <TableCell className="px-6 py-4">
                            <button
                              onClick={() => setViewingCustomer(customer)}
                              className="text-left group"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-foreground group-hover:text-primary">{customer.name}</span>
                                {customer.ai_status === 'searching' && (
                                  <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-xs gap-1">
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                    AI 搜索中
                                  </Badge>
                                )}
                                {customer.ai_status === 'completed' && (
                                  <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-xs">
                                    AI
                                  </Badge>
                                )}
                                {customer.ai_status === 'failed' && (
                                  <Badge variant="secondary" className="bg-red-100 text-red-700 text-xs">
                                    AI 失败
                                  </Badge>
                                )}
                              </div>
                              {customer.short_name && (
                                <div className="text-xs text-muted-foreground">{customer.short_name}</div>
                              )}
                            </button>
                          </TableCell>
                          <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                            {customer.country || '-'}
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            <Badge variant="secondary" className={level.color}>
                              {level.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setContactsCustomer(customer)}
                            >
                              <Users className="h-4 w-4" />
                              {customer.contact_count} 人
                            </Button>
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            <Badge variant="secondary" className={
                              customer.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-muted-foreground'
                            }>
                              {customer.is_active ? '活跃' : '停用'}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-6 py-4 text-sm text-muted-foreground">
                            {formatDateTime(customer.created_at)}
                          </TableCell>
                          <TableCell className="px-6 py-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                onClick={() => setViewingCustomer(customer)}
                                title="查看"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              {can('customer', 'update') && (
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                onClick={() => setEditingCustomer(customer)}
                                title="编辑"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              )}
                              {can('customer', 'delete') && (
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                className="text-destructive hover:text-destructive"
                                onClick={() => handleDelete(customer)}
                                title="删除"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-3 border-t">
                  <div className="text-sm text-muted-foreground">
                    共 {total} 条，第 {page}/{totalPages} 页
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      上一页
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      下一页
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* 创建客户弹窗 */}
          <Dialog open={showCreate} onOpenChange={(open) => { if (!open) setShowCreate(false); }}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
              <DialogHeader>
                <DialogTitle>新建客户</DialogTitle>
              </DialogHeader>
              <CustomerForm
                onSubmit={handleCreate}
                onCancel={() => setShowCreate(false)}
                loading={saving}
                onDraftCreated={() => {
                  setShowCreate(false);
                  loadCustomers();
                }}
              />
            </DialogContent>
          </Dialog>

          {/* 编辑客户弹窗 */}
          <Dialog open={!!editingCustomer} onOpenChange={(open) => { if (!open) setEditingCustomer(null); }}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
              <DialogHeader>
                <DialogTitle>{`编辑客户 - ${editingCustomer?.name || ''}`}</DialogTitle>
              </DialogHeader>
              {editingCustomer && (
                <CustomerForm
                  initial={editingCustomer}
                  onSubmit={handleUpdate}
                  onCancel={() => setEditingCustomer(null)}
                  loading={saving}
                />
              )}
            </DialogContent>
          </Dialog>

          {/* 客户详情弹窗 */}
          <CustomerDetailModal
            isOpen={!!viewingCustomer}
            onClose={() => setViewingCustomer(null)}
            customer={viewingCustomer}
          />

          {/* 联系人管理弹窗 */}
          <ContactsModal
            isOpen={!!contactsCustomer}
            onClose={() => setContactsCustomer(null)}
            customer={contactsCustomer}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
