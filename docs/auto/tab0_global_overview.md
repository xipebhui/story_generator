# Tab 0: 全局概览

## 1. 前端方案

### 1.1 界面布局
- **位置**：作为第一个Tab，最先展示给用户
- **布局**：响应式网格布局，自适应不同屏幕尺寸
- **刷新机制**：不自动刷新，支持手动刷新

### 1.2 主要组件
```
┌─────────────────────────────────────────────────────────────────┐
│  全局概览                             [今日 | 本周 | 本月] [刷新]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  统计卡片区域（4个）                                               │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐      │
│  │Pipeline     │发布配置      │执行任务      │账号          │      │
│  │    12个     │    35个     │   1,256个    │   8组/45个   │      │
│  └─────────────┴─────────────┴─────────────┴─────────────┘      │
│                                                                  │
│  图表区域（2列）                                                  │
│  ┌──────────────────────┐        ┌──────────────────────┐       │
│  │ 执行成功率            │        │ 平台分布             │       │
│  │ ████████████░░ 94.5% │        │ YouTube:  78%       │       │
│  │ 今日: 45/48 成功      │        │ Bilibili: 22%       │       │
│  └──────────────────────┘        └──────────────────────┘       │
│                                                                  │
│  账号表现TOP5                     最近执行任务                    │
│  ┌──────────────────────┐        ┌──────────────────────┐       │
│  │1. yt_001 观看:12.3K   │        │task_001 ✅ 10分钟前 │       │
│  │2. yt_002 观看:10.1K   │        │task_002 🔄 进行中   │       │
│  └──────────────────────┘        └──────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 组件结构
```tsx
// components/AutoPublish/GlobalOverview.tsx
import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, List, Tag, Radio } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface OverviewStats {
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
  platformDistribution: {
    platform: string;
    count: number;
    percentage: number;
  }[];
  successRate: {
    today: number;
    week: number;
    month: number;
  };
}

interface TopAccount {
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

interface RecentTask {
  task_id: string;
  pipeline_name: string;
  account_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  duration?: number;
}
```

### 1.4 交互功能
- **统计卡片点击**：跳转到对应的Tab页面
- **时间范围切换**：今日/本周/本月数据切换
- **手动刷新**：点击刷新按钮立即更新
- **账号点击**：跳转到账号详情
- **任务点击**：跳转到任务详情

## 2. 需要的接口

### 2.1 获取概览统计
```http
GET /api/auto-publish/overview/stats

Query参数:
  - period: string (today/week/month) 默认today

响应示例:
{
  "pipelines": 12,
  "configs": 35,
  "tasks": {
    "total": 1256,
    "today": 48,
    "week": 336,
    "month": 1256,
    "success": 1180,
    "failed": 56,
    "running": 5,
    "pending": 15
  },
  "accounts": {
    "groups": 8,
    "total": 45,
    "active": 42
  },
  "successRate": {
    "today": 93.75,
    "week": 94.2,
    "month": 93.9
  }
}
```

### 2.2 获取平台分布
```http
GET /api/auto-publish/overview/platform-distribution

Query参数:
  - period: string (today/week/month) 默认today

响应示例:
[
  {
    "platform": "youtube",
    "count": 980,
    "percentage": 78.0
  },
  {
    "platform": "bilibili",
    "count": 276,
    "percentage": 22.0
  }
]
```

### 2.3 获取账号TOP榜
```http
GET /api/auto-publish/overview/top-accounts

Query参数:
  - limit: number (默认5，最大10)
  - period: string (today/week/month) 默认today
  - metric: string (views/likes/subscribers) 默认views

响应示例:
[
  {
    "account_id": "yt_001_novel",
    "account_name": "小说频道1",
    "platform": "youtube",
    "metrics": {
      "views": 12300,
      "likes": 456,
      "comments": 89,
      "subscribers_gained": 234
    }
  }
]
```

### 2.4 获取最近执行任务
```http
GET /api/auto-publish/overview/recent-tasks

Query参数:
  - limit: number (默认10，最大20)

响应示例:
[
  {
    "task_id": "task_20241225_001",
    "pipeline_name": "YouTube故事生成V3",
    "account_name": "小说频道1",
    "status": "completed",
    "created_at": "2024-12-25T10:30:00Z",
    "duration": 320
  }
]
```

## 3. 后端执行流程

### 3.1 统计数据获取流程
```python
# api_auto_publish.py
@router.get("/overview/stats")
async def get_overview_stats(
    period: str = Query("today", regex="^(today|week|month)$"),
    current_user = Depends(get_current_user)
):
    """获取概览统计数据"""
    db = get_db_manager()
    
    # 1. 计算时间范围
    now = datetime.now()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    else:  # month
        start_date = now - timedelta(days=30)
    
    # 2. 查询Pipeline总数
    pipeline_count = db.query(
        "SELECT COUNT(*) FROM pipeline_registry WHERE status = 'active'"
    )
    
    # 3. 查询配置总数
    config_count = db.query(
        "SELECT COUNT(*) FROM publish_configs WHERE is_active = 1"
    )
    
    # 4. 查询任务统计
    task_stats = db.query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) as period_count,
            SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN pipeline_status = 'running' THEN 1 ELSE 0 END) as running,
            SUM(CASE WHEN pipeline_status = 'pending' THEN 1 ELSE 0 END) as pending
        FROM auto_publish_tasks
        WHERE created_at >= ?
    """, (start_date, start_date))
    
    # 5. 查询账号统计
    account_stats = db.query("""
        SELECT 
            (SELECT COUNT(*) FROM account_groups WHERE is_active = 1) as groups,
            (SELECT COUNT(*) FROM accounts WHERE is_active = 1) as total,
            (SELECT COUNT(DISTINCT account_id) FROM auto_publish_tasks 
             WHERE created_at >= ?) as active
        FROM dual
    """, (start_date,))
    
    # 6. 计算成功率
    success_rate = (task_stats['success'] / task_stats['period_count'] * 100 
                   if task_stats['period_count'] > 0 else 0)
    
    return {
        "pipelines": pipeline_count,
        "configs": config_count,
        "tasks": task_stats,
        "accounts": account_stats,
        "successRate": success_rate
    }
```

### 3.2 平台分布获取流程
```python
@router.get("/overview/platform-distribution")
async def get_platform_distribution(
    period: str = Query("today"),
    current_user = Depends(get_current_user)
):
    """获取平台分布数据"""
    db = get_db_manager()
    
    # 计算时间范围
    start_date = calculate_start_date(period)
    
    # 查询平台分布
    results = db.query("""
        SELECT 
            JSON_EXTRACT(pr.supported_platforms, '$[0]') as platform,
            COUNT(apt.task_id) as count
        FROM auto_publish_tasks apt
        JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
        WHERE apt.created_at >= ?
        GROUP BY platform
    """, (start_date,))
    
    # 计算百分比
    total = sum(r['count'] for r in results)
    for r in results:
        r['percentage'] = round(r['count'] / total * 100, 1) if total > 0 else 0
    
    return results
```

## 4. 数据模型

使用现有数据模型，无需新增：
- `pipeline_registry` - Pipeline注册表
- `publish_configs` - 发布配置
- `auto_publish_tasks` - 执行任务
- `account_groups` - 账号组
- `accounts` - 账号表

## 5. 数据库交互

### 5.1 核心SQL查询

```sql
-- Pipeline总数
SELECT COUNT(*) as count 
FROM pipeline_registry 
WHERE status = 'active';

-- 配置总数
SELECT COUNT(*) as count 
FROM publish_configs 
WHERE is_active = 1;

-- 任务统计（支持时间范围）
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 ELSE 0 END) as today,
    SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as week,
    SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as month,
    SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success,
    SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed,
    SUM(CASE WHEN pipeline_status = 'running' THEN 1 ELSE 0 END) as running,
    SUM(CASE WHEN pipeline_status = 'pending' THEN 1 ELSE 0 END) as pending
FROM auto_publish_tasks
WHERE created_at >= ?;

-- 平台分布
SELECT 
    CASE 
        WHEN supported_platforms LIKE '%youtube%' THEN 'youtube'
        WHEN supported_platforms LIKE '%bilibili%' THEN 'bilibili'
        ELSE 'other'
    END as platform,
    COUNT(apt.task_id) as count
FROM auto_publish_tasks apt
JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
WHERE apt.created_at >= ?
GROUP BY platform;

-- TOP账号（基于任务成功数）
SELECT 
    a.account_id,
    a.account_name,
    a.platform,
    COUNT(apt.task_id) as task_count,
    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_count,
    JSON_EXTRACT(apt.metadata, '$.performance.views') as views
FROM accounts a
JOIN auto_publish_tasks apt ON a.account_id = apt.account_id
WHERE apt.created_at >= ?
  AND apt.pipeline_status = 'completed'
GROUP BY a.account_id
ORDER BY success_count DESC, views DESC
LIMIT ?;

-- 最近执行任务
SELECT 
    apt.task_id,
    pr.pipeline_name,
    a.account_name,
    apt.pipeline_status as status,
    apt.created_at,
    TIMESTAMPDIFF(SECOND, apt.started_at, apt.completed_at) as duration
FROM auto_publish_tasks apt
JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
JOIN accounts a ON apt.account_id = a.account_id
ORDER BY apt.created_at DESC
LIMIT ?;
```

## 6. 前端实现要点

### 6.1 自动刷新机制
```tsx
useEffect(() => {
  // 初始加载
  loadOverviewData();
  
  // 设置自动刷新
  const interval = setInterval(() => {
    loadOverviewData();
  }, 30000); // 30秒
  
  return () => clearInterval(interval);
}, [period]);
```

### 6.2 跳转功能
```tsx
const handleCardClick = (target: string) => {
  switch(target) {
    case 'pipeline':
      navigate('/auto-publish?tab=pipeline');
      break;
    case 'config':
      navigate('/auto-publish?tab=config');
      break;
    case 'task':
      navigate('/auto-publish?tab=task');
      break;
    case 'account':
      navigate('/auto-publish?tab=account');
      break;
  }
};
```

### 6.3 响应式布局
```tsx
<Row gutter={[16, 16]}>
  <Col xs={24} sm={12} md={6}>
    <Card hoverable onClick={() => handleCardClick('pipeline')}>
      <Statistic title="Pipeline" value={stats.pipelines} suffix="个" />
    </Card>
  </Col>
  {/* 其他卡片... */}
</Row>
```

## 7. 测试要点

### 7.1 功能测试
- [ ] 数据加载是否正常
- [ ] 时间范围切换是否生效
- [ ] 自动刷新是否工作
- [ ] 跳转功能是否正确

### 7.2 性能测试
- [ ] 大数据量下的加载速度
- [ ] 内存泄漏检查（自动刷新）
- [ ] API响应时间

### 7.3 兼容性测试
- [ ] 不同屏幕尺寸的响应式布局
- [ ] 不同浏览器的兼容性

## 8. 部署注意事项

1. **缓存策略**：概览数据可以适当缓存，减少数据库压力
2. **权限控制**：确保用户只能看到有权限的数据
3. **错误处理**：API调用失败时的友好提示
4. **性能优化**：考虑使用Redis缓存热点数据