// 自动发布系统相关类型定义

// 概览统计数据
export interface OverviewStats {
  pipelines: number;
  configs: number;
  tasks: {
    total: number;
    today: number;
    week: number;
    month: number;
    success: number;
    failed: number;
    running: number;
    pending: number;
  };
  accounts: {
    groups: number;
    total: number;
    active: number;
  };
  successRate: {
    today: number;
    week: number;
    month: number;
  };
}

// 任务时间分布
export interface TaskTimeDistribution {
  timeRange: string;
  count: number;
  percentage: number;
}

// 顶级账号
export interface TopAccount {
  account_id: string;
  account_name: string;
  platform: string;
  metrics: {
    views: number;
    likes: number;
    comments: number;
    subscribers_gained: number;
  };
}

// 最近任务
export interface RecentTask {
  task_id: string;
  pipeline_name: string;
  account_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  duration?: number;
}

// 时间范围类型
export type PeriodType = 'today' | 'week' | 'month';

// 指标类型
export type MetricType = 'views' | 'likes' | 'subscribers';