// src/app/admin/customers/page.tsx
// 客户管理页面
//
// 功能说明：
// 1. 客户列表（搜索、筛选、分页）
// 2. 创建/编辑/删除客户
// 3. 联系人管理（弹窗内 CRUD）

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  customersApi,
  contactsApi,
  Customer,
  CustomerDetail,
  CustomerCreate,
  CustomerUpdate,
  Contact,
  ContactCreate,
  ContactUpdate,
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

// 客户等级配置
const CUSTOMER_LEVELS: Record<string, { label: string; color: string }> = {
  potential: { label: '潜在', color: 'bg-gray-100 text-gray-800' },
  normal: { label: '普通', color: 'bg-blue-100 text-blue-800' },
  important: { label: '重要', color: 'bg-orange-100 text-orange-800' },
  vip: { label: 'VIP', color: 'bg-purple-100 text-purple-800' },
};

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

// ==================== 客户表单 ====================

function CustomerForm({
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  initial?: Partial<Customer>;
  onSubmit: (data: CustomerCreate | CustomerUpdate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
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

  const inputClass = "w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本信息 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3 pb-2 border-b">基本信息</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>公司全称 *</label>
            <input
              type="text"
              required
              className={inputClass}
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>简称/别名</label>
            <input
              type="text"
              className={inputClass}
              value={form.short_name || ''}
              onChange={e => setForm({ ...form, short_name: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>国家</label>
            <input
              type="text"
              className={inputClass}
              value={form.country || ''}
              onChange={e => setForm({ ...form, country: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>地区/洲</label>
            <input
              type="text"
              className={inputClass}
              value={form.region || ''}
              onChange={e => setForm({ ...form, region: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>行业</label>
            <input
              type="text"
              className={inputClass}
              value={form.industry || ''}
              onChange={e => setForm({ ...form, industry: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>客户等级</label>
            <select
              className={inputClass}
              value={form.customer_level}
              onChange={e => setForm({ ...form, customer_level: e.target.value })}
            >
              {Object.entries(CUSTOMER_LEVELS).map(([value, { label }]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 公司规模 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3 pb-2 border-b">业务信息</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>公司规模</label>
            <select
              className={inputClass}
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
            <label className={labelClass}>年营收范围</label>
            <select
              className={inputClass}
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
            <label className={labelClass}>客户来源</label>
            <select
              className={inputClass}
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
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 text-blue-600 rounded"
                checked={form.is_active}
                onChange={e => setForm({ ...form, is_active: e.target.checked })}
              />
              <span className="text-sm text-gray-700">活跃客户</span>
            </label>
          </div>
        </div>
      </div>

      {/* 联系信息 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3 pb-2 border-b">联系信息</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>公司邮箱</label>
            <input
              type="email"
              className={inputClass}
              value={form.email || ''}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>公司电话</label>
            <input
              type="text"
              className={inputClass}
              value={form.phone || ''}
              onChange={e => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>公司网站</label>
            <input
              type="text"
              className={inputClass}
              value={form.website || ''}
              onChange={e => setForm({ ...form, website: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>公司地址</label>
            <input
              type="text"
              className={inputClass}
              value={form.address || ''}
              onChange={e => setForm({ ...form, address: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* 贸易信息 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3 pb-2 border-b">贸易信息</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>付款条款</label>
            <input
              type="text"
              className={inputClass}
              placeholder="如: T/T 30 days, L/C at sight"
              value={form.payment_terms || ''}
              onChange={e => setForm({ ...form, payment_terms: e.target.value })}
            />
          </div>
          <div>
            <label className={labelClass}>贸易术语 (Incoterms)</label>
            <select
              className={inputClass}
              value={form.shipping_terms || ''}
              onChange={e => setForm({ ...form, shipping_terms: e.target.value })}
            >
              <option value="">未设置</option>
              <option value="FOB">FOB</option>
              <option value="CIF">CIF</option>
              <option value="EXW">EXW</option>
              <option value="CFR">CFR</option>
              <option value="DDP">DDP</option>
              <option value="DAP">DAP</option>
            </select>
          </div>
        </div>
      </div>

      {/* 标签和备注 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3 pb-2 border-b">其他</h4>
        <div className="space-y-4">
          <div>
            <label className={labelClass}>标签</label>
            <div className="flex items-center gap-2 mb-2">
              <input
                type="text"
                className={inputClass}
                placeholder="输入标签后按回车或点击添加"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
              />
              <button
                type="button"
                onClick={addTag}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 whitespace-nowrap"
              >
                添加
              </button>
            </div>
            {form.tags && form.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {form.tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="ml-1 text-blue-600 hover:text-blue-800"
                    >
                      x
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className={labelClass}>备注</label>
            <textarea
              rows={3}
              className={inputClass}
              value={form.notes || ''}
              onChange={e => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* 按钮 */}
      <div className="flex justify-end space-x-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={loading || !form.name.trim()}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '保存中...' : '保存'}
        </button>
      </div>
    </form>
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
      alert('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
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
      alert('更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (contact: Contact) => {
    if (!confirm(`确定要删除联系人「${contact.name}」吗？`)) return;
    try {
      await contactsApi.delete(contact.id);
      await loadContacts();
    } catch (err) {
      alert('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  if (!customer) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`${customer.name} - 联系人管理`} wide>
      {/* 工具栏 */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-500">共 {contacts.length} 位联系人</span>
        <button
          onClick={() => { setCreating(true); setEditing(null); }}
          className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          添加联系人
        </button>
      </div>

      {/* 创建表单 */}
      {creating && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg border">
          <h4 className="text-sm font-medium text-gray-900 mb-3">新建联系人</h4>
          <ContactForm
            customerId={customer.id}
            onSubmit={(data) => handleCreate(data as ContactCreate)}
            onCancel={() => setCreating(false)}
            loading={saving}
          />
        </div>
      )}

      {/* 联系人列表 */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">加载中...</div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-8 text-gray-500">暂无联系人</div>
      ) : (
        <div className="space-y-3">
          {contacts.map(contact => (
            <div key={contact.id} className="border rounded-lg p-4">
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
                      <span className="font-medium text-gray-900">{contact.name}</span>
                      {contact.is_primary && (
                        <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">主联系人</span>
                      )}
                      {!contact.is_active && (
                        <span className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">已停用</span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 space-y-0.5">
                      {contact.title && <div>{contact.title}{contact.department ? ` - ${contact.department}` : ''}</div>}
                      {contact.email && <div>邮箱: {contact.email}</div>}
                      {contact.phone && <div>座机: {contact.phone}</div>}
                      {contact.mobile && <div>手机: {contact.mobile}</div>}
                      {contact.notes && <div className="text-gray-400 mt-1">{contact.notes}</div>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => { setEditing(contact); setCreating(false); }}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(contact)}
                      className="text-sm text-red-600 hover:text-red-800"
                    >
                      删除
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Modal>
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

  const inputClass = "w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">姓名 *</label>
          <input
            type="text"
            required
            className={inputClass}
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">职位</label>
          <input
            type="text"
            className={inputClass}
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">部门</label>
          <input
            type="text"
            className={inputClass}
            value={form.department}
            onChange={e => setForm({ ...form, department: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">邮箱</label>
          <input
            type="email"
            className={inputClass}
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">座机</label>
          <input
            type="text"
            className={inputClass}
            value={form.phone}
            onChange={e => setForm({ ...form, phone: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">手机</label>
          <input
            type="text"
            className={inputClass}
            value={form.mobile}
            onChange={e => setForm({ ...form, mobile: e.target.value })}
          />
        </div>
      </div>
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 text-blue-600 rounded"
            checked={form.is_primary}
            onChange={e => setForm({ ...form, is_primary: e.target.checked })}
          />
          <span className="text-sm text-gray-700">主联系人</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 text-blue-600 rounded"
            checked={form.is_active}
            onChange={e => setForm({ ...form, is_active: e.target.checked })}
          />
          <span className="text-sm text-gray-700">活跃</span>
        </label>
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">备注</label>
        <input
          type="text"
          className={inputClass}
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
        />
      </div>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={loading || !form.name.trim()}
          className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '保存中...' : '保存'}
        </button>
      </div>
    </form>
  );
}

// ==================== 主页面 ====================

export default function CustomersPage() {
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
  const [saving, setSaving] = useState(false);

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

  // CRUD 操作
  const handleCreate = async (data: CustomerCreate | CustomerUpdate) => {
    setSaving(true);
    try {
      await customersApi.create(data as CustomerCreate);
      setShowCreate(false);
      await loadCustomers();
    } catch (err) {
      alert('创建失败: ' + (err instanceof Error ? err.message : '未知错误'));
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
      alert('更新失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (customer: Customer) => {
    const msg = customer.contact_count > 0
      ? `确定要删除客户「${customer.name}」吗？\n该客户有 ${customer.contact_count} 个联系人，将一并删除。`
      : `确定要删除客户「${customer.name}」吗？`;
    if (!confirm(msg)) return;
    try {
      await customersApi.delete(customer.id);
      await loadCustomers();
    } catch (err) {
      alert('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">客户管理</h1>
          <p className="mt-1 text-sm text-gray-500">管理公司客户及联系人信息</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          新建客户
        </button>
      </div>

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow-sm border p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="搜索公司名称、简称、邮箱..."
              className="w-full px-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
            />
          </div>
          <select
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filterLevel}
            onChange={e => { setFilterLevel(e.target.value); setPage(1); }}
          >
            <option value="">全部等级</option>
            {Object.entries(CUSTOMER_LEVELS).map(([value, { label }]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filterActive}
            onChange={e => { setFilterActive(e.target.value); setPage(1); }}
          >
            <option value="">全部状态</option>
            <option value="true">活跃</option>
            <option value="false">停用</option>
          </select>
        </div>
      </div>

      {/* 客户列表 */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">公司名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">国家</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">等级</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">联系人</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">加载中...</td>
              </tr>
            ) : customers.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  {search || filterLevel || filterActive ? '没有匹配的客户' : '暂无客户数据'}
                </td>
              </tr>
            ) : (
              customers.map(customer => {
                const level = CUSTOMER_LEVELS[customer.customer_level] || CUSTOMER_LEVELS.normal;
                return (
                  <tr key={customer.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{customer.name}</div>
                      {customer.short_name && (
                        <div className="text-xs text-gray-500">{customer.short_name}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {customer.country || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${level.color}`}>
                        {level.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setContactsCustomer(customer)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {customer.contact_count} 人
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                        customer.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {customer.is_active ? '活跃' : '停用'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDateTime(customer.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <button
                        onClick={() => setEditingCustomer(customer)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(customer)}
                        className="text-sm text-red-600 hover:text-red-800"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-t">
            <div className="text-sm text-gray-500">
              共 {total} 条，第 {page}/{totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1 text-sm border rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 text-sm border rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 创建客户弹窗 */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="新建客户" wide>
        <CustomerForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={saving}
        />
      </Modal>

      {/* 编辑客户弹窗 */}
      <Modal
        isOpen={!!editingCustomer}
        onClose={() => setEditingCustomer(null)}
        title={`编辑客户 - ${editingCustomer?.name || ''}`}
        wide
      >
        {editingCustomer && (
          <CustomerForm
            initial={editingCustomer}
            onSubmit={handleUpdate}
            onCancel={() => setEditingCustomer(null)}
            loading={saving}
          />
        )}
      </Modal>

      {/* 联系人管理弹窗 */}
      <ContactsModal
        isOpen={!!contactsCustomer}
        onClose={() => setContactsCustomer(null)}
        customer={contactsCustomer}
      />
    </div>
  );
}
