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
  emailsApi,
  EmailDetail,
  WorkType,
  WorkTypeTreeNode,
  WorkTypeCreate,
  WorkTypeUpdate,
  WorkTypeSuggestion,
} from '@/lib/api';
import { toast } from 'sonner';
import { useConfirm } from '@/components/ConfirmProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { LoadingSpinner, PageLoading } from '@/components/LoadingSpinner';
import { ChevronRight, Plus, Pencil, Ban, CheckCircle2, Trash2, Lightbulb } from 'lucide-react';

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
        className={`flex items-center justify-between py-3 px-4 hover:bg-muted/50 ${
          level > 0 ? 'border-l-2 border ml-6' : ''
        }`}
      >
        <div className="flex items-center space-x-3">
          {hasChildren ? (
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => setExpanded(!expanded)}
            >
              <ChevronRight
                className={`size-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
              />
            </Button>
          ) : (
            <span className="w-4" />
          )}

          <div>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="font-mono text-sm px-2 py-0.5">
                {node.code}
              </Badge>
              <span className="font-medium text-foreground">{node.name}</span>
              {node.is_system && (
                <Badge variant="secondary" className="text-xs">
                  系统
                </Badge>
              )}
              {!node.is_active && (
                <Badge className="text-xs bg-red-50 text-red-500 border-red-200">
                  已禁用
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">{node.description}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-muted-foreground">
            使用 {node.usage_count} 次
          </span>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => onEdit(node)}
            className="text-blue-600 hover:text-blue-800"
          >
            编辑
          </Button>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => onToggle(node.id)}
            className={node.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'}
          >
            {node.is_active ? '禁用' : '启用'}
          </Button>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => onDelete(node.id)}
            className="text-red-600 hover:text-red-800"
          >
            删除
          </Button>
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
  const confirmDialog = useConfirm();

  // Tab 状态
  const [activeTab, setActiveTab] = useState<string>('types');

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
  // 关键词/示例用 string 状态，避免实时 split 破坏 IME 输入
  const [keywordsText, setKeywordsText] = useState('');
  const [examplesText, setExamplesText] = useState('');

  // 审批弹窗
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewingItem, setReviewingItem] = useState<WorkTypeSuggestion | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [reviewFormData, setReviewFormData] = useState<Partial<WorkTypeCreate>>({});
  const [reviewFormError, setReviewFormError] = useState('');
  const [reviewKeywordsText, setReviewKeywordsText] = useState('');
  const [reviewExamplesText, setReviewExamplesText] = useState('');

  // 邮件原文预览
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailDetail, setEmailDetail] = useState<EmailDetail | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

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
    setKeywordsText('');
    setExamplesText('');
    setFormError('');
    setShowEditModal(true);
  };

  // 打开编辑弹窗
  const handleEdit = (item: WorkType | WorkTypeTreeNode) => {
    // 从 flatList 获取完整数据（TreeNode 不含 examples/keywords）
    const fullItem = flatList.find((i) => i.id === item.id);
    setEditingItem(item);
    setFormData({
      code: item.code,
      name: item.name,
      description: item.description,
      examples: fullItem?.examples || [],
      keywords: fullItem?.keywords || [],
      is_active: item.is_active,
    });
    setKeywordsText((fullItem?.keywords || []).join(', '));
    setExamplesText((fullItem?.examples || []).join(', '));
    setFormError('');
    setShowEditModal(true);
  };

  // 将逗号分隔文本转为数组（支持中英文逗号）
  const splitTags = (text: string) =>
    text.split(/[,，]/).map((s) => s.trim()).filter(Boolean);

  // 保存
  const handleSave = async () => {
    setSaving(true);
    setFormError('');

    // 提交时才从文本解析为数组
    const submitData = {
      ...formData,
      keywords: splitTags(keywordsText),
      examples: splitTags(examplesText),
    };

    try {
      if (editingItem) {
        // 更新
        await workTypesApi.update(editingItem.id, submitData as WorkTypeUpdate);
      } else {
        // 创建
        if (!submitData.code || !submitData.name || !submitData.description) {
          throw new Error('请填写必填字段');
        }
        await workTypesApi.create(submitData as WorkTypeCreate);
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
    const confirmed = await confirmDialog({
      title: '确认删除',
      description: '确定要删除此工作类型吗？',
      variant: 'destructive',
      confirmText: '删除',
    });
    if (!confirmed) return;

    try {
      await workTypesApi.delete(id);
      loadWorkTypes();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '删除失败');
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
      toast.error(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 打开审批弹窗（预填 AI 建议数据）
  const handleReview = (item: WorkTypeSuggestion) => {
    setReviewingItem(item);
    setReviewNote('');
    setReviewFormError('');
    setReviewFormData({
      code: item.suggested_code,
      name: item.suggested_name,
      description: item.suggested_description,
      parent_id: item.suggested_parent_id || undefined,
      keywords: item.suggested_keywords || [],
      examples: item.suggested_examples || [],
      is_active: true,
    });
    setReviewKeywordsText((item.suggested_keywords || []).join(', '));
    setReviewExamplesText((item.suggested_examples || []).join(', '));
    setShowReviewModal(true);
  };

  // 批准
  const handleApprove = async () => {
    if (!reviewingItem) return;
    setReviewFormError('');

    if (!reviewFormData.code || !reviewFormData.name || !reviewFormData.description) {
      setReviewFormError('请填写标识码、名称和描述');
      return;
    }

    setReviewing(true);

    try {
      await workTypesApi.approveSuggestion(reviewingItem.id, {
        note: reviewNote || undefined,
        code: reviewFormData.code,
        name: reviewFormData.name,
        description: reviewFormData.description,
        parent_id: reviewFormData.parent_id || undefined,
        keywords: splitTags(reviewKeywordsText),
        examples: splitTags(reviewExamplesText),
      });
      setShowReviewModal(false);
      loadWorkTypes();
      loadSuggestions();
    } catch (e) {
      setReviewFormError(e instanceof Error ? e.message : '操作失败');
    }

    setReviewing(false);
  };

  // 拒绝
  const handleReject = async () => {
    if (!reviewingItem) return;
    setReviewing(true);

    try {
      await workTypesApi.rejectSuggestion(reviewingItem.id, reviewNote || undefined);
      setShowReviewModal(false);
      loadSuggestions();
    } catch (e) {
      setReviewFormError(e instanceof Error ? e.message : '操作失败');
    }

    setReviewing(false);
  };

  // 查看来源邮件原文
  const handleViewEmail = async (emailId: string) => {
    setEmailLoading(true);
    setEmailDetail(null);
    setShowEmailModal(true);

    try {
      const detail = await emailsApi.get(emailId);
      setEmailDetail(detail);
    } catch (e) {
      setEmailDetail(null);
      toast.error(e instanceof Error ? e.message : '加载邮件失败');
      setShowEmailModal(false);
    }

    setEmailLoading(false);
  };

  // 获取顶级类型列表（用于父级选择）
  const topLevelTypes = flatList.filter((i) => i.level === 1 && i.is_active);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">工作类型管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          管理系统工作类型，AI 自动识别的新类型需要人工审批
        </p>
      </div>

      {/* Tab 切换 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="types">
            工作类型列表
          </TabsTrigger>
          <TabsTrigger value="suggestions">
            待审批建议
            {pendingCount > 0 && (
              <Badge className="ml-2 bg-blue-100 text-blue-600 border-blue-200">
                {pendingCount}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* 工作类型列表 Tab */}
        <TabsContent value="types">
          <Card className="p-0">
            {/* 工具栏 */}
            <div className="p-4 border-b flex justify-between items-center">
              <div className="text-sm text-muted-foreground">
                共 {flatList.length} 个工作类型
              </div>
              <Button onClick={handleCreate}>
                <Plus className="size-4" />
                新增工作类型
              </Button>
            </div>

            {/* 列表 */}
            {loading ? (
              <div className="p-8 text-center">
                <LoadingSpinner text="加载中..." />
              </div>
            ) : error ? (
              <div className="p-8 text-center text-red-500">{error}</div>
            ) : treeData.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">暂无数据</div>
            ) : (
              <div className="divide-y">
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
          </Card>
        </TabsContent>

        {/* 待审批建议 Tab */}
        <TabsContent value="suggestions">
          <Card className="p-0">
            {suggestionsLoading ? (
              <div className="p-8 text-center">
                <LoadingSpinner text="加载中..." />
              </div>
            ) : suggestions.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">暂无待审批建议</div>
            ) : (
              <div className="divide-y">
                {suggestions.map((item) => (
                  <div key={item.id} className="p-4 hover:bg-muted/50">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center space-x-2">
                          <Badge className="font-mono text-sm bg-blue-50 text-blue-600 border-blue-200 px-2 py-0.5">
                            {item.suggested_code}
                          </Badge>
                          <span className="font-medium text-foreground">
                            {item.suggested_name}
                          </span>
                          {item.suggested_parent_code && (
                            <span className="text-xs text-muted-foreground">
                              (父级: {item.suggested_parent_code})
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {item.suggested_description}
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                          <span>置信度: {(item.confidence * 100).toFixed(0)}%</span>
                          <span>来源: {item.trigger_source}</span>
                          <span>{formatDateTime(item.created_at)}</span>
                        </div>
                        {item.reasoning && (
                          <p className="text-sm text-muted-foreground mt-2 bg-muted p-2 rounded">
                            AI 推理: {item.reasoning}
                          </p>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        <Button
                          size="sm"
                          onClick={() => handleReview(item)}
                        >
                          审批
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* 创建/编辑弹窗 */}
      <Dialog open={showEditModal} onOpenChange={(open) => !open && setShowEditModal(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{editingItem ? '编辑工作类型' : '新增工作类型'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {formError && (
              <div className="bg-red-50 text-red-600 p-3 rounded text-sm">
                {formError}
              </div>
            )}

            {/* Code */}
            <div>
              <Label className="mb-1">
                标识码 <span className="text-red-500">*</span>
              </Label>
              <Input
                type="text"
                value={formData.code || ''}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="如 ORDER、ORDER_NEW"
              />
              <p className="text-xs text-muted-foreground mt-1">全大写英文，可包含数字和下划线</p>
            </div>

            {/* 名称 */}
            <div>
              <Label className="mb-1">
                名称 <span className="text-red-500">*</span>
              </Label>
              <Input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="如 订单、新订单"
              />
            </div>

            {/* 描述 */}
            <div>
              <Label className="mb-1">
                描述 <span className="text-red-500">*</span>
              </Label>
              <Textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="给 AI 的描述，帮助识别此工作类型"
                rows={3}
              />
            </div>

            {/* 父级（仅创建时可选） */}
            {!editingItem && (
              <div>
                <Label className="mb-1">
                  父级工作类型
                </Label>
                <select
                  value={formData.parent_id || ''}
                  onChange={(e) => setFormData({ ...formData, parent_id: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">无（顶级类型）</option>
                  {topLevelTypes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} - {item.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground mt-1">如选择父级，标识码需以父级标识码开头加下划线</p>
              </div>
            )}

            {/* 关键词 */}
            <div>
              <Label className="mb-1">
                关键词
              </Label>
              <Input
                type="text"
                value={keywordsText}
                onChange={(e) => setKeywordsText(e.target.value)}
                placeholder="用逗号分隔，如: 订单, order, PO"
              />
              <p className="text-xs text-muted-foreground mt-1">辅助 AI 匹配的关键词，支持中英文逗号分隔</p>
            </div>

            {/* 示例 */}
            <div>
              <Label className="mb-1">
                示例文本
              </Label>
              <Input
                type="text"
                value={examplesText}
                onChange={(e) => setExamplesText(e.target.value)}
                placeholder="用逗号分隔，如: 我想下单, 订单确认, PO"
              />
              <p className="text-xs text-muted-foreground mt-1">帮助 AI 识别此类型的示例短语，支持中英文逗号分隔</p>
            </div>

            {/* 是否启用 */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active ?? true}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 text-primary border-input rounded"
              />
              <label htmlFor="is_active" className="ml-2 text-sm text-muted-foreground">
                启用
              </label>
            </div>

            {/* 按钮 */}
            <div className="flex justify-end space-x-3 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowEditModal(false)}
              >
                取消
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 审批弹窗（复用新增表单样式，AI 数据预填可编辑） */}
      <Dialog open={showReviewModal} onOpenChange={(open) => !open && setShowReviewModal(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>审批工作类型建议</DialogTitle>
          </DialogHeader>
          {reviewingItem && (
            <div className="space-y-4">
              {/* AI 分析信息 */}
              <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-blue-800">AI 建议</span>
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-blue-600">
                      置信度: {(reviewingItem.confidence * 100).toFixed(0)}%
                    </span>
                    {reviewingItem.trigger_email_id && (
                      <Button
                        variant="link"
                        size="xs"
                        onClick={() => handleViewEmail(reviewingItem.trigger_email_id!)}
                        className="text-xs text-blue-700 hover:text-blue-900"
                      >
                        查看来源邮件
                      </Button>
                    )}
                  </div>
                </div>
                {reviewingItem.reasoning && (
                  <p className="text-sm text-blue-700 mt-1">{reviewingItem.reasoning}</p>
                )}
                {reviewingItem.trigger_content && (
                  <details className="mt-2">
                    <summary className="text-xs text-blue-600 cursor-pointer">查看触发内容</summary>
                    <p className="text-xs text-blue-700 mt-1 bg-background p-2 rounded border border-blue-100">
                      {reviewingItem.trigger_content.substring(0, 500)}
                      {reviewingItem.trigger_content.length > 500 && '...'}
                    </p>
                  </details>
                )}
              </div>

              {reviewFormError && (
                <div className="bg-red-50 text-red-600 p-3 rounded text-sm">
                  {reviewFormError}
                </div>
              )}

              {/* 表单字段（与新增工作类型一致） */}
              <div>
                <Label className="mb-1">
                  标识码 <span className="text-red-500">*</span>
                </Label>
                <Input
                  type="text"
                  value={reviewFormData.code || ''}
                  onChange={(e) => setReviewFormData({ ...reviewFormData, code: e.target.value.toUpperCase() })}
                  placeholder="如 ORDER、ORDER_NEW"
                />
                <p className="text-xs text-muted-foreground mt-1">全大写英文，可包含数字和下划线</p>
              </div>

              <div>
                <Label className="mb-1">
                  名称 <span className="text-red-500">*</span>
                </Label>
                <Input
                  type="text"
                  value={reviewFormData.name || ''}
                  onChange={(e) => setReviewFormData({ ...reviewFormData, name: e.target.value })}
                  placeholder="如 订单、新订单"
                />
              </div>

              <div>
                <Label className="mb-1">
                  描述 <span className="text-red-500">*</span>
                </Label>
                <Textarea
                  value={reviewFormData.description || ''}
                  onChange={(e) => setReviewFormData({ ...reviewFormData, description: e.target.value })}
                  placeholder="给 AI 的描述，帮助识别此工作类型"
                  rows={3}
                />
              </div>

              <div>
                <Label className="mb-1">
                  父级工作类型
                </Label>
                <select
                  value={reviewFormData.parent_id || ''}
                  onChange={(e) => setReviewFormData({ ...reviewFormData, parent_id: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">无（顶级类型）</option>
                  {topLevelTypes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} - {item.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label className="mb-1">
                  关键词
                </Label>
                <Input
                  type="text"
                  value={reviewKeywordsText}
                  onChange={(e) => setReviewKeywordsText(e.target.value)}
                  placeholder="用逗号分隔，如: 订单, order, PO"
                />
                <p className="text-xs text-muted-foreground mt-1">辅助 AI 匹配的关键词，支持中英文逗号分隔</p>
              </div>

              <div>
                <Label className="mb-1">
                  示例文本
                </Label>
                <Input
                  type="text"
                  value={reviewExamplesText}
                  onChange={(e) => setReviewExamplesText(e.target.value)}
                  placeholder="用逗号分隔，如: 我想下单, 订单确认, PO"
                />
                <p className="text-xs text-muted-foreground mt-1">帮助 AI 识别此类型的示例短语，支持中英文逗号分隔</p>
              </div>

              {/* 审批备注 */}
              <div>
                <Label className="mb-1">
                  审批备注
                </Label>
                <Textarea
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  placeholder="可选，填写审批说明"
                  rows={2}
                />
              </div>

              {/* 按钮 */}
              <div className="flex justify-end space-x-3 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowReviewModal(false)}
                >
                  取消
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleReject}
                  disabled={reviewing}
                >
                  {reviewing ? '处理中...' : '拒绝'}
                </Button>
                <Button
                  onClick={handleApprove}
                  disabled={reviewing}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {reviewing ? '处理中...' : '批准'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 邮件原文预览弹窗 */}
      <Dialog open={showEmailModal} onOpenChange={(open) => !open && setShowEmailModal(false)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>来源邮件原文</DialogTitle>
          </DialogHeader>
          {emailLoading ? (
            <div className="p-8 text-center">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : emailDetail ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">发件人:</span>{' '}
                  <span className="text-foreground">
                    {emailDetail.sender_name ? `${emailDetail.sender_name} <${emailDetail.sender}>` : emailDetail.sender}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">时间:</span>{' '}
                  <span className="text-foreground">{formatDateTime(emailDetail.received_at)}</span>
                </div>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">收件人:</span>{' '}
                <span className="text-foreground">{emailDetail.recipients.join(', ')}</span>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">主题:</span>{' '}
                <span className="font-medium text-foreground">{emailDetail.subject}</span>
              </div>

              <div className="border-t pt-4">
                <div className="bg-muted p-4 rounded-lg text-sm text-foreground whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {emailDetail.body_text || '（无正文内容）'}
                </div>
              </div>

              {emailDetail.attachments && emailDetail.attachments.length > 0 && (
                <div className="text-sm">
                  <span className="text-muted-foreground">附件 ({emailDetail.attachments.length}):</span>
                  <div className="mt-1 space-y-1">
                    {emailDetail.attachments.map((att, idx) => (
                      <div key={idx} className="text-foreground bg-muted px-2 py-1 rounded text-xs">
                        {att.filename} ({(att.size_bytes / 1024).toFixed(1)} KB)
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <Button
                  variant="outline"
                  onClick={() => setShowEmailModal(false)}
                >
                  关闭
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">无法加载邮件内容</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
