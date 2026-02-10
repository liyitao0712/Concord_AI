// lib/design-tokens.ts
// 全局设计规范常量
//
// 功能说明：
// 统一管理状态颜色、弹窗尺寸、表格间距等设计规范，
// 消除各页面硬编码的样式字符串。

// ==================== 状态颜色 ====================

/** 通用状态颜色映射（含 dark mode） */
export const STATUS_COLORS = {
  // 通用活跃/停用
  active: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
  inactive: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',

  // 客户/供应商等级
  potential: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  normal: 'bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400',
  important: 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400',
  vip: 'bg-purple-50 text-purple-700 dark:bg-purple-950/30 dark:text-purple-400',
  strategic: 'bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400',

  // 紧急程度
  urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',

  // 情感
  positive: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
  negative: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',

  // 流程状态
  draft: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  pending: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400',
  confirmed: 'bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400',
  completed: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
  cancelled: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400',

  // 产品状态
  discontinued: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',

  // 审批
  approved: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
  rejected: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400',

  // Worker 状态
  running: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
  stopped: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  error: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400',
} as const;

export type StatusColorKey = keyof typeof STATUS_COLORS;

// ==================== 弹窗尺寸 ====================

/** 弹窗尺寸规范 */
export const DIALOG_SIZES = {
  /** 确认框、重置密码、单字段编辑 */
  sm: 'sm:max-w-lg',
  /** 用户/角色/部门创建编辑 */
  md: 'sm:max-w-3xl',
  /** 供应商/合同编辑 */
  lg: 'sm:max-w-4xl',
  /** 客户4列表单、产品详情、带明细行的单据 */
  xl: 'sm:max-w-5xl',
} as const;

export type DialogSize = keyof typeof DIALOG_SIZES;

// ==================== 表格 ====================

/** 表格单元格统一间距 */
export const TABLE_CELL_PADDING = 'px-4 py-3';
/** 表头统一间距 */
export const TABLE_HEAD_PADDING = 'px-4';

// ==================== 搜索 ====================

/** 搜索输入防抖时间（毫秒） */
export const SEARCH_DEBOUNCE_MS = 300;

// ==================== 分页 ====================

/** 默认每页条数 */
export const DEFAULT_PAGE_SIZE = 20;
