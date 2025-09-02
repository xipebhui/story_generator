// 模拟数据用于测试全局概览组件
import { OverviewStats, TaskTimeDistribution, TopAccount, RecentTask } from '../../types/autoPublish';

export const mockOverviewStats: OverviewStats = {
  pipelines: 12,
  configs: 35,
  tasks: {
    total: 1256,
    today: 48,
    week: 336,
    month: 1256,
    success: 1180,
    failed: 56,
    running: 5,
    pending: 15
  },
  accounts: {
    groups: 8,
    total: 45,
    active: 42
  },
  successRate: {
    today: 93.75,
    week: 94.2,
    month: 93.9
  }
};

export const mockTimeDistribution: TaskTimeDistribution[] = [
  {
    timeRange: '00-06',
    count: 245,
    percentage: 25.0
  },
  {
    timeRange: '06-12',
    count: 294,
    percentage: 30.0
  },
  {
    timeRange: '12-18',
    count: 196,
    percentage: 20.0
  },
  {
    timeRange: '18-24',
    count: 245,
    percentage: 25.0
  }
];

export const mockTopAccounts: TopAccount[] = [
  {
    account_id: 'yt_001_novel',
    account_name: '故事频道1号',
    platform: 'YouTube',
    metrics: {
      views: 12300,
      likes: 456,
      comments: 89,
      subscribers_gained: 234
    }
  },
  {
    account_id: 'yt_002_novel',
    account_name: '故事频道2号',
    platform: 'YouTube',
    metrics: {
      views: 10100,
      likes: 389,
      comments: 67,
      subscribers_gained: 198
    }
  },
  {
    account_id: 'yt_003_novel',
    account_name: '故事频道3号',
    platform: 'YouTube',
    metrics: {
      views: 8900,
      likes: 324,
      comments: 56,
      subscribers_gained: 165
    }
  },
  {
    account_id: 'yt_004_novel',
    account_name: '故事频道4号',
    platform: 'YouTube',
    metrics: {
      views: 7800,
      likes: 287,
      comments: 45,
      subscribers_gained: 134
    }
  },
  {
    account_id: 'yt_005_novel',
    account_name: '故事频道5号',
    platform: 'YouTube',
    metrics: {
      views: 6700,
      likes: 251,
      comments: 38,
      subscribers_gained: 109
    }
  }
];

export const mockRecentTasks: RecentTask[] = [
  {
    task_id: 'task_20241225_001',
    pipeline_name: 'YouTube故事生成V3',
    account_name: '故事频道1号',
    status: 'completed',
    created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    duration: 320
  },
  {
    task_id: 'task_20241225_002',
    pipeline_name: 'YouTube故事生成V3',
    account_name: '故事频道2号',
    status: 'running',
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString()
  },
  {
    task_id: 'task_20241225_003',
    pipeline_name: 'YouTube新闻汇总V1',
    account_name: '故事频道3号',
    status: 'failed',
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    duration: 180
  },
  {
    task_id: 'task_20241225_004',
    pipeline_name: 'YouTube故事生成V3',
    account_name: '故事频道4号',
    status: 'pending',
    created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString()
  },
  {
    task_id: 'task_20241225_005',
    pipeline_name: 'YouTube教程制作V2',
    account_name: '故事频道5号',
    status: 'completed',
    created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    duration: 450
  }
];