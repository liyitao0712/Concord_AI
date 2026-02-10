// src/app/admin/departments/page.tsx
// 部门管理页面（树形结构）
//
// 功能说明：
// 1. 部门树形展示（展开/折叠）
// 2. 创建/编辑/删除部门
// 3. 排序支持（上移/下移）
// 4. 选择父部门

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  departmentsApi,
  Department,
  DepartmentCreate,
  DepartmentUpdate,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useConfirm } from '@/components/ConfirmProvider';
import { usePermission } from '@/hooks/usePermission';
import { toast } from 'sonner';
import {
  Plus,
  Pencil,
  Trash2,
  ChevronRight,
  ChevronDown,
  ArrowUp,
  ArrowDown,
  Network,
  FolderOpen,
  Folder,
} from 'lucide-react';
import { FormDialog } from '@/components/FormDialog';
import { FormFooter } from '@/components/FormFooter';
import { ErrorAlert } from '@/components/ErrorAlert';

// ==================== 部门树节点组件 ====================

interface DepartmentTreeNodeProps {
  department: Department;
  level: number;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
  onEdit: (dept: Department) => void;
  onDelete: (dept: Department) => void;
  onMoveUp: (dept: Department) => void;
  onMoveDown: (dept: Department) => void;
  onAddChild: (parentId: string) => void;
  canEdit: boolean;
  isFirst: boolean;
  isLast: boolean;
}

function DepartmentTreeNode({
  department,
  level,
  expandedIds,
  onToggleExpand,
  onEdit,
  onDelete,
  onMoveUp,
  onMoveDown,
  onAddChild,
  canEdit,
  isFirst,
  isLast,
}: DepartmentTreeNodeProps) {
  const hasChildren = department.children && department.children.length > 0;
  const isExpanded = expandedIds.has(department.id);

  return (
    <div>
      <div
        className="flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-md group"
        style={{ paddingLeft: `${level * 24 + 12}px` }}
      >
        {/* 展开/折叠按钮 */}
        <button
          onClick={() => onToggleExpand(department.id)}
          className="w-5 h-5 flex items-center justify-center text-muted-foreground hover:text-foreground"
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )
          ) : (
            <span className="w-4" />
          )}
        </button>

        {/* 图标 */}
        {hasChildren && isExpanded ? (
          <FolderOpen className="h-4 w-4 text-blue-500" />
        ) : (
          <Folder className="h-4 w-4 text-muted-foreground" />
        )}

        {/* 部门名称 */}
        <span className="font-medium text-sm flex-1">{department.name}</span>

        {/* 编码 */}
        {department.code && (
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            {department.code}
          </code>
        )}

        {/* 状态 */}
        <Badge
          variant={department.is_active ? 'default' : 'destructive'}
          className={`text-xs ${department.is_active ? 'bg-green-600' : ''}`}
        >
          {department.is_active ? '启用' : '禁用'}
        </Badge>

        {/* 操作按钮 */}
        {canEdit && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onMoveUp(department)}
              disabled={isFirst}
              title="上移"
            >
              <ArrowUp className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onMoveDown(department)}
              disabled={isLast}
              title="下移"
            >
              <ArrowDown className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onAddChild(department.id)}
              title="添加子部门"
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onEdit(department)}
              title="编辑"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => onDelete(department)}
              title="删除"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>

      {/* 子节点 */}
      {hasChildren && isExpanded && (
        <div>
          {department.children!.map((child, index) => (
            <DepartmentTreeNode
              key={child.id}
              department={child}
              level={level + 1}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
              onEdit={onEdit}
              onDelete={onDelete}
              onMoveUp={onMoveUp}
              onMoveDown={onMoveDown}
              onAddChild={onAddChild}
              canEdit={canEdit}
              isFirst={index === 0}
              isLast={index === department.children!.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== 扁平化部门树（用于下拉选择） ====================

function flattenDepartments(
  departments: Department[],
  level: number = 0,
): Array<{ id: string; name: string; level: number }> {
  const result: Array<{ id: string; name: string; level: number }> = [];
  for (const dept of departments) {
    result.push({ id: dept.id, name: dept.name, level });
    if (dept.children && dept.children.length > 0) {
      result.push(...flattenDepartments(dept.children, level + 1));
    }
  }
  return result;
}

// ==================== 主页面 ====================

export default function DepartmentsPage() {
  const { can } = usePermission();
  const confirm = useConfirm();
  const canEdit = can('setting', 'update');

  // 树形数据
  const [tree, setTree] = useState<Department[]>([]);
  const [flatList, setFlatList] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 展开状态
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // 模态框状态
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);

  // 表单状态
  const [formData, setFormData] = useState<DepartmentCreate>({
    name: '',
    code: '',
    parent_id: null,
    sort_order: 0,
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 加载部门树
  const loadTree = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [treeData, listData] = await Promise.all([
        departmentsApi.tree(),
        departmentsApi.list(),
      ]);
      setTree(treeData);
      setFlatList(listData);
      // 默认展开第一层
      const ids = new Set<string>();
      treeData.forEach((d) => ids.add(d.id));
      setExpandedIds((prev) => {
        // 保留之前展开的节点，同时展开根节点
        const merged = new Set(prev);
        ids.forEach((id) => merged.add(id));
        return merged;
      });
    } catch (err: any) {
      setError(err.message || '加载部门数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  // 切换展开
  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // 全部展开
  const expandAll = () => {
    const allIds = new Set<string>();
    const collect = (depts: Department[]) => {
      depts.forEach((d) => {
        allIds.add(d.id);
        if (d.children) collect(d.children);
      });
    };
    collect(tree);
    setExpandedIds(allIds);
  };

  // 全部折叠
  const collapseAll = () => {
    setExpandedIds(new Set());
  };

  // 打开创建模态框
  const openCreateModal = (parentId?: string) => {
    setEditingDept(null);
    setFormData({
      name: '',
      code: '',
      parent_id: parentId || null,
      sort_order: 0,
    });
    setFormError('');
    setShowFormModal(true);
  };

  // 打开编辑模态框
  const openEditModal = (dept: Department) => {
    setEditingDept(dept);
    setFormData({
      name: dept.name,
      code: dept.code || '',
      parent_id: dept.parent_id || null,
      sort_order: dept.sort_order,
    });
    setFormError('');
    setShowFormModal(true);
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);

    try {
      if (editingDept) {
        const updateData: DepartmentUpdate = {};
        if (formData.name !== editingDept.name) updateData.name = formData.name;
        if ((formData.code || '') !== (editingDept.code || '')) updateData.code = formData.code;
        if (formData.parent_id !== editingDept.parent_id) updateData.parent_id = formData.parent_id;
        if (formData.sort_order !== editingDept.sort_order) updateData.sort_order = formData.sort_order;
        await departmentsApi.update(editingDept.id, updateData);
        toast.success('部门已更新');
      } else {
        await departmentsApi.create(formData);
        toast.success('部门已创建');
      }
      setShowFormModal(false);
      loadTree();
    } catch (err: any) {
      setFormError(err.message || '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 删除部门
  const handleDelete = async (dept: Department) => {
    if (dept.children && dept.children.length > 0) {
      toast.error('该部门下有子部门，无法删除。请先删除子部门。');
      return;
    }

    const confirmed = await confirm({
      title: '删除部门',
      description: `确定要删除部门「${dept.name}」吗？此操作无法撤销。`,
      confirmText: '删除',
      variant: 'destructive',
    });
    if (!confirmed) return;

    try {
      await departmentsApi.delete(dept.id);
      toast.success('部门已删除');
      loadTree();
    } catch (err: any) {
      toast.error(err.message || '删除失败');
    }
  };

  // 上移/下移
  const handleMoveUp = async (dept: Department) => {
    // 找到同级部门
    const siblings = findSiblings(tree, dept.parent_id || null);
    const index = siblings.findIndex((s) => s.id === dept.id);
    if (index <= 0) return;

    // 交换排序值
    const items = [
      { id: siblings[index].id, sort_order: siblings[index - 1].sort_order, parent_id: dept.parent_id },
      { id: siblings[index - 1].id, sort_order: siblings[index].sort_order, parent_id: dept.parent_id },
    ];

    try {
      await departmentsApi.sort(items);
      loadTree();
    } catch (err: any) {
      toast.error(err.message || '排序失败');
    }
  };

  const handleMoveDown = async (dept: Department) => {
    const siblings = findSiblings(tree, dept.parent_id || null);
    const index = siblings.findIndex((s) => s.id === dept.id);
    if (index >= siblings.length - 1) return;

    const items = [
      { id: siblings[index].id, sort_order: siblings[index + 1].sort_order, parent_id: dept.parent_id },
      { id: siblings[index + 1].id, sort_order: siblings[index].sort_order, parent_id: dept.parent_id },
    ];

    try {
      await departmentsApi.sort(items);
      loadTree();
    } catch (err: any) {
      toast.error(err.message || '排序失败');
    }
  };

  // 查找同级部门
  function findSiblings(departments: Department[], parentId: string | null): Department[] {
    if (!parentId) return departments;
    for (const dept of departments) {
      if (dept.id === parentId) return dept.children || [];
      if (dept.children) {
        const found = findSiblings(dept.children, parentId);
        if (found.length > 0 || dept.children.some((c) => c.id === parentId)) {
          // 如果 parentId 在 dept.children 中直接匹配
          const parent = dept.children.find((c) => c.id === parentId);
          if (parent) return parent.children || [];
          return found;
        }
      }
    }
    return [];
  }

  // 可选的父部门列表（排除自身及其子节点）
  const getParentOptions = () => {
    const flattened = flattenDepartments(tree);
    if (!editingDept) return flattened;

    // 排除自身和所有子孙节点
    const excludeIds = new Set<string>();
    const collectChildren = (depts: Department[]) => {
      depts.forEach((d) => {
        excludeIds.add(d.id);
        if (d.children) collectChildren(d.children);
      });
    };
    // 从 flatList 中找到当前编辑的部门及其子节点
    excludeIds.add(editingDept.id);
    const findAndCollect = (depts: Department[]) => {
      for (const d of depts) {
        if (d.id === editingDept.id && d.children) {
          collectChildren(d.children);
          return;
        }
        if (d.children) findAndCollect(d.children);
      }
    };
    findAndCollect(tree);

    return flattened.filter((f) => !excludeIds.has(f.id));
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={expandAll}>
          全部展开
        </Button>
        <Button variant="outline" size="sm" onClick={collapseAll}>
          全部折叠
        </Button>
        {canEdit && (
          <Button onClick={() => openCreateModal()}>
            <Plus className="h-4 w-4 mr-1" />
            创建部门
          </Button>
        )}
      </div>

      {/* 错误提示 */}
      {error && <ErrorAlert message={error} onRetry={loadTree} />}

      {/* 部门树 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Network className="h-4 w-4" />
            部门结构
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center">
              <LoadingSpinner size="sm" text="加载中..." />
            </div>
          ) : tree.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              暂无部门，点击「创建部门」添加
            </div>
          ) : (
            <div className="space-y-0.5">
              {tree.map((dept, index) => (
                <DepartmentTreeNode
                  key={dept.id}
                  department={dept}
                  level={0}
                  expandedIds={expandedIds}
                  onToggleExpand={toggleExpand}
                  onEdit={openEditModal}
                  onDelete={handleDelete}
                  onMoveUp={handleMoveUp}
                  onMoveDown={handleMoveDown}
                  onAddChild={(parentId) => openCreateModal(parentId)}
                  canEdit={canEdit}
                  isFirst={index === 0}
                  isLast={index === tree.length - 1}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 创建/编辑部门模态框 */}
      <FormDialog
        open={showFormModal}
        onOpenChange={setShowFormModal}
        title={editingDept ? '编辑部门' : '创建部门'}
        description={editingDept ? '修改部门信息' : '填写信息以创建新部门'}
        size="sm"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="text-destructive text-sm">{formError}</div>
          )}
          <div>
            <Label>部门名称</Label>
            <Input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="例如：销售部"
              className="mt-1"
            />
          </div>
          <div>
            <Label>部门编码</Label>
            <Input
              type="text"
              value={formData.code || ''}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              placeholder="例如：SALES（选填）"
              className="mt-1"
            />
          </div>
          <div>
            <Label>上级部门</Label>
            <select
              value={formData.parent_id || ''}
              onChange={(e) =>
                setFormData({ ...formData, parent_id: e.target.value || null })
              }
              className="mt-1 block w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">无（顶级部门）</option>
              {getParentOptions().map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {'　'.repeat(opt.level)}{opt.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>排序值</Label>
            <Input
              type="number"
              value={formData.sort_order ?? 0}
              onChange={(e) =>
                setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })
              }
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">数值越小越靠前</p>
          </div>
          <FormFooter
            onCancel={() => setShowFormModal(false)}
            submitText={editingDept ? '保存' : '创建'}
            loading={submitting}
          />
        </form>
      </FormDialog>
    </div>
  );
}
