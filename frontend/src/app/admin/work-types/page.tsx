// src/app/admin/work-types/page.tsx
// 工作类型管理页面
//
// 功能说明：
// 1. 工作类型树形列表展示
// 2. 创建/编辑/删除工作类型
// 3. 工作类型建议审批

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  workTypesApi,
  WorkType,
  WorkTypeTreeNode,
  WorkTypeCreate,
  WorkTypeUpdate,
  WorkTypeSuggestion,
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
            {tab.count !== undefined && tab.count > 0 && (
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

// ==================== 树形节点组件 ====================

function TreeNode({
  node,
  onEdit,
  onDelete,
  onToggle,
  level = 0,
}: {
  node: WorkTypeTreeNode;
  onEdit: (node: WorkTypeTreeNode) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string) => void;
  level?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <div
        className={`flex items-center justify-between py-3 px-4 hover:bg-gray-50 ${
          level > 0 ? 'border-l-2 border-gray-200 ml-6' : ''
        }`}
      >
        <div className="flex items-center space-x-3">
          {hasChildren ? (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg
                className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ) : (
            <span className="w-4" />
          )}

          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                {node.code}
              </span>
              <span className="font-medium text-gray-900">{node.name}</span>
              {node.is_system && (
                <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                  系统
                </span>
              )}
              {!node.is_active && (
                <span className="text-xs text-red-500 bg-red-50 px-1.5 py-0.5 rounded">
                  已禁用
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{node.description}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">
            使用 {node.usage_count} 次
          </span>
          <button
            onClick={() => onEdit(node)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            编辑
          </button>
          <button
            onClick={() => onToggle(node.id)}
            className={`text-sm ${node.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'}`}
          >
            {node.is_active ? '禁用' : '启用'}
          </button>
          {!node.is_system && (
            <button
              onClick={() => onDelete(node.id)}
              className="text-red-600 hover:text-red-800 text-sm"
            >
              删除
            </button>
          )}
        </div>
      </div>

      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              onEdit={onEdit}
              onDelete={onDelete}
              onToggle={onToggle}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== 主页面 ====================

export default function WorkTypesPage() {
  // Tab 状态
  const [activeTab, setActiveTab] = useState<'types' | 'suggestions'>('types');

  // 工作类型列表状态
  const [treeData, setTreeData] = useState<WorkTypeTreeNode[]>([]);
  const [flatList, setFlatList] = useState<WorkType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 建议列表状态
  const [suggestions, setSuggestions] = useState<WorkTypeSuggestion[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  // 创建/编辑弹窗
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingItem, setEditingItem] = useState<WorkType | WorkTypeTreeNode | null>(null);
  const [formData, setFormData] = useState<Partial<WorkTypeCreate>>({});
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  // 审批弹窗
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewingItem, setReviewingItem] = useState<WorkTypeSuggestion | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewing, setReviewing] = useState(false);

  // 加载工作类型列表
  const loadWorkTypes = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [treeResponse, listResponse] = await Promise.all([
        workTypesApi.tree({ is_active: undefined }),
        workTypesApi.list(),
      ]);
      setTreeData(treeResponse.items);
      setFlatList(listResponse.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    }

    setLoading(false);
  }, []);

  // 加载建议列表
  const loadSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);

    try {
      const response = await workTypesApi.listSuggestions({ status: 'pending' });
      setSuggestions(response.items);
      setPendingCount(response.total);
    } catch (e) {
      console.error('加载建议失败:', e);
    }

    setSuggestionsLoading(false);
  }, []);

  useEffect(() => {
    loadWorkTypes();
    loadSuggestions();
  }, [loadWorkTypes, loadSuggestions]);

  // 打开创建弹窗
  const handleCreate = () => {
    setEditingItem(null);
    setFormData({
      code: '',
      name: '',
      description: '',
      parent_id: undefined,
      examples: [],
      keywords: [],
      is_active: true,
    });
    setFormError('');
    setShowEditModal(true);
  };

  // 打开编辑弹窗
  const handleEdit = (item: WorkType | WorkTypeTreeNode) => {
    setEditingItem(item);
    setFormData({
      name: item.name,
      description: item.description,
      examples: [],
      keywords: [],
      is_active: item.is_active,
    });
    setFormError('');
    setShowEditModal(true);
  };

  // 保存
  const handleSave = async () => {
    setSaving(true);
    setFormError('');

    try {
      if (editingItem) {
        // 更新
        await workTypesApi.update(editingItem.id, formData as WorkTypeUpdate);
      } else {
        // 创建
        if (!formData.code || !formData.name || !formData.description) {
          throw new Error('请填写必填字段');
        }
        await workTypesApi.create(formData as WorkTypeCreate);
      }
      setShowEditModal(false);
      loadWorkTypes();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : '保存失败');
    }

    setSaving(false);
  };

  // 删除
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除此工作类型吗？')) return;

    try {
      await workTypesApi.delete(id);
      loadWorkTypes();
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  // 切换启用/禁用
  const handleToggle = async (id: string) => {
    const item = flatList.find((i) => i.id === id);
    if (!item) return;

    try {
      await workTypesApi.update(id, { is_active: !item.is_active });
      loadWorkTypes();
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 打开审批弹窗
  const handleReview = (item: WorkTypeSuggestion) => {
    setReviewingItem(item);
    setReviewNote('');
    setShowReviewModal(true);
  };

  // 批准
  const handleApprove = async () => {
    if (!reviewingItem) return;
    setReviewing(true);

    try {
      await workTypesApi.approveSuggestion(reviewingItem.id, reviewNote);
      setShowReviewModal(false);
      loadWorkTypes();
      loadSuggestions();
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }

    setReviewing(false);
  };

  // 拒绝
  const handleReject = async () => {
    if (!reviewingItem) return;
    setReviewing(true);

    try {
      await workTypesApi.rejectSuggestion(reviewingItem.id, reviewNote);
      setShowReviewModal(false);
      loadSuggestions();
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }

    setReviewing(false);
  };

  // 获取顶级类型列表（用于父级选择）
  const topLevelTypes = flatList.filter((i) => i.level === 1 && i.is_active);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">工作类型管理</h1>
        <p className="mt-1 text-sm text-gray-500">
          管理系统工作类型，AI 自动识别的新类型需要人工审批
        </p>
      </div>

      {/* Tab 切换 */}
      <Tabs
        tabs={[
          { id: 'types', label: '工作类型列表' },
          { id: 'suggestions', label: '待审批建议', count: pendingCount },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as 'types' | 'suggestions')}
      />

      {/* 工作类型列表 Tab */}
      {activeTab === 'types' && (
        <div className="bg-white rounded-lg shadow">
          {/* 工具栏 */}
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <div className="text-sm text-gray-500">
              共 {flatList.length} 个工作类型
            </div>
            <button
              onClick={handleCreate}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
            >
              + 新增工作类型
            </button>
          </div>

          {/* 列表 */}
          {loading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : error ? (
            <div className="p-8 text-center text-red-500">{error}</div>
          ) : treeData.length === 0 ? (
            <div className="p-8 text-center text-gray-500">暂无数据</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {treeData.map((node) => (
                <TreeNode
                  key={node.id}
                  node={node}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onToggle={handleToggle}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 待审批建议 Tab */}
      {activeTab === 'suggestions' && (
        <div className="bg-white rounded-lg shadow">
          {suggestionsLoading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : suggestions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">暂无待审批建议</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {suggestions.map((item) => (
                <div key={item.id} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-sm text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                          {item.suggested_code}
                        </span>
                        <span className="font-medium text-gray-900">
                          {item.suggested_name}
                        </span>
                        {item.suggested_parent_code && (
                          <span className="text-xs text-gray-500">
                            (父级: {item.suggested_parent_code})
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        {item.suggested_description}
                      </p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
                        <span>置信度: {(item.confidence * 100).toFixed(0)}%</span>
                        <span>来源: {item.trigger_source}</span>
                        <span>{formatDateTime(item.created_at)}</span>
                      </div>
                      {item.reasoning && (
                        <p className="text-sm text-gray-600 mt-2 bg-gray-50 p-2 rounded">
                          AI 推理: {item.reasoning}
                        </p>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleReview(item)}
                        className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                      >
                        审批
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 创建/编辑弹窗 */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title={editingItem ? '编辑工作类型' : '新增工作类型'}
      >
        <div className="space-y-4">
          {formError && (
            <div className="bg-red-50 text-red-600 p-3 rounded text-sm">
              {formError}
            </div>
          )}

          {/* Code（仅创建时可编辑） */}
          {!editingItem && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                标识码 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.code || ''}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="如 ORDER、ORDER_NEW"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">全大写英文，可包含数字和下划线</p>
            </div>
          )}

          {/* 名称 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="如 订单、新订单"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* 描述 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              描述 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="给 AI 的描述，帮助识别此工作类型"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* 父级（仅创建时可选） */}
          {!editingItem && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                父级工作类型
              </label>
              <select
                value={formData.parent_id || ''}
                onChange={(e) => setFormData({ ...formData, parent_id: e.target.value || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">无（顶级类型）</option>
                {topLevelTypes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} - {item.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">如选择父级，标识码需以父级标识码开头加下划线</p>
            </div>
          )}

          {/* 是否启用 */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active ?? true}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
            <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
              启用
            </label>
          </div>

          {/* 按钮 */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              onClick={() => setShowEditModal(false)}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </Modal>

      {/* 审批弹窗 */}
      <Modal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        title="审批工作类型建议"
        wide
      >
        {reviewingItem && (
          <div className="space-y-4">
            {/* 建议详情 */}
            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm text-blue-600 bg-blue-100 px-2 py-0.5 rounded">
                  {reviewingItem.suggested_code}
                </span>
                <span className="font-medium text-gray-900">
                  {reviewingItem.suggested_name}
                </span>
              </div>
              <p className="text-sm text-gray-600">{reviewingItem.suggested_description}</p>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">父级:</span>{' '}
                  <span className="text-gray-900">
                    {reviewingItem.suggested_parent_code || '无（顶级类型）'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">置信度:</span>{' '}
                  <span className="text-gray-900">
                    {(reviewingItem.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {reviewingItem.reasoning && (
                <div>
                  <span className="text-gray-500 text-sm">AI 推理:</span>
                  <p className="text-gray-900 text-sm mt-1">{reviewingItem.reasoning}</p>
                </div>
              )}

              {reviewingItem.trigger_content && (
                <div>
                  <span className="text-gray-500 text-sm">触发内容:</span>
                  <p className="text-gray-700 text-sm mt-1 bg-white p-2 rounded border">
                    {reviewingItem.trigger_content.substring(0, 500)}
                    {reviewingItem.trigger_content.length > 500 && '...'}
                  </p>
                </div>
              )}
            </div>

            {/* 审批备注 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                审批备注
              </label>
              <textarea
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                placeholder="可选，填写审批说明"
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* 按钮 */}
            <div className="flex justify-end space-x-3 pt-4">
              <button
                onClick={() => setShowReviewModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleReject}
                disabled={reviewing}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {reviewing ? '处理中...' : '拒绝'}
              </button>
              <button
                onClick={handleApprove}
                disabled={reviewing}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {reviewing ? '处理中...' : '批准'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
