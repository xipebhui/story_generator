# Tab 3: 执行记录管理

> 参考：[global_context.md](./global_context.md) - 全局上下文和规范

## 1. 前端方案

### 1.1 界面布局
```
┌─────────────────────────────────────────────────────────────────┐
│  执行记录                     [状态▼] [日期范围] [账号▼] [刷新]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  任务列表（表格）                                                 │
│  ┌────────┬────────┬──────────┬────────┬────────┬──────────────┐│
│  │任务ID  │配置名称│Pipeline  │状态    │执行时间│操作           ││
│  ├────────┼────────┼──────────┼────────┼────────┼──────────────┤│
│  │task_001│每日故事│story_v3  │✅完成  │10分钟前│查看 数据 重试  ││
│  │task_002│测试配置│meta_gen  │🔄运行中│进行中  │查看 停止       ││
│  │task_003│每日故事│story_v3  │❌失败  │1小时前 │查看 日志 重试  ││
│  └────────┴────────┴──────────┴────────┴────────┴──────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 组件结构
```tsx
// components/AutoPublish/TaskExecutionManager.tsx
import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Drawer, Descriptions, Tag, Space, Tabs,
  Upload, message, Timeline, Row, Col, Statistic, List, Badge,
  Alert, Collapse, Typography, Tooltip, Modal, Progress
} from 'antd';
import {
  EyeOutlined, ReloadOutlined, UploadOutlined, BarChartOutlined,
  PlayCircleOutlined, TeamOutlined, FileTextOutlined, ClockCircleOutlined
} from '@ant-design/icons';

interface TaskExecution {
  task_id: string;
  config_id: string;
  config_name: string;
  group_id: string;
  group_name: string;
  account_id: string;
  account_name?: string;
  pipeline_id: string;
  pipeline_name: string;
  pipeline_config?: any;
  pipeline_status: 'pending' | 'running' | 'completed' | 'failed';
  pipeline_result?: any;
  publish_status: 'pending' | 'published' | 'failed';
  publish_result?: any;
  priority: number;
  retry_count: number;
  error_message?: string;
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  metadata?: TaskMetadata;
}

interface TaskMetadata {
  subtitle_file?: string;
  video_url?: string;
  thumbnail_url?: string;
  performance?: PerformanceData;
  logs?: string[];
}

// 重要：账号组执行详情
interface GroupExecutionDetail {
  config_id: string;
  config_name: string;
  group_id: string;
  group_name: string;
  execution_time: string;
  total_accounts: number;
  accounts: AccountExecution[];
  summary: {
    total: number;
    success: number;
    failed: number;
    running: number;
    pending: number;
    avg_duration: number;
    total_views: number;
    total_likes: number;
  };
}

interface AccountExecution {
  account_id: string;
  account_name: string;
  platform: string;
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  video_url?: string;
  duration?: number;
  error_message?: string;
  performance: PerformanceData;
}

interface PerformanceData {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  watch_time_minutes: number;
  ctr: number;  // 点击率
  retention_rate: number;  // 完播率
  subscriber_gained: number;
  revenue?: number;
}
```

### 1.3 任务详情抽屉（显示账号组所有账号数据）

```tsx
const TaskDetail: React.FC<{ task: TaskExecution }> = ({ task }) => {
  const [groupExecution, setGroupExecution] = useState<GroupExecutionDetail | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [subtitleFile, setSubtitleFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  
  useEffect(() => {
    // 加载账号组执行详情
    loadGroupExecutionDetail();
  }, [task.task_id]);
  
  const loadGroupExecutionDetail = async () => {
    try {
      const response = await autoPublishService.getGroupExecutions(
        task.config_id,
        task.created_at
      );
      setGroupExecution(response);
    } catch (error) {
      message.error('加载账号组执行详情失败');
    }
  };
  
  const handleSubtitleUpload = async () => {
    if (!subtitleFile) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('subtitle', subtitleFile);
    formData.append('task_id', task.task_id);
    
    try {
      await autoPublishService.uploadSubtitle(task.task_id, formData);
      message.success('字幕上传成功');
      setSubtitleFile(null);
    } catch (error) {
      message.error('字幕上传失败');
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <Drawer
      title={
        <Space>
          <TeamOutlined />
          任务执行详情 - {task.config_name}
        </Space>
      }
      width={1000}
      visible={visible}
      onClose={onClose}>
      
      {/* 顶部统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="账号总数" 
              value={groupExecution?.total_accounts || 0} 
              prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="成功率" 
              value={groupExecution?.summary.success || 0}
              suffix={`/ ${groupExecution?.summary.total || 0}`}
              valueStyle={{ 
                color: (groupExecution?.summary.success || 0) === 
                       (groupExecution?.summary.total || 0) ? '#3f8600' : '#cf1322' 
              }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="总观看量" 
              value={groupExecution?.summary.total_views || 0} 
              prefix={<EyeOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic 
              title="平均耗时" 
              value={groupExecution?.summary.avg_duration || 0} 
              suffix="秒" 
              prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
      </Row>
      
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* Tab 1: 概览信息 */}
        <TabPane tab="概览" key="overview">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="任务ID">{task.task_id}</Descriptions.Item>
            <Descriptions.Item label="配置名称">{task.config_name}</Descriptions.Item>
            <Descriptions.Item label="Pipeline">{task.pipeline_name}</Descriptions.Item>
            <Descriptions.Item label="账号组">{task.group_name}</Descriptions.Item>
            <Descriptions.Item label="执行时间">{task.created_at}</Descriptions.Item>
            <Descriptions.Item label="完成时间">{task.completed_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Progress percent={task.priority} steps={5} size="small" showInfo={false} />
            </Descriptions.Item>
            <Descriptions.Item label="重试次数">{task.retry_count}</Descriptions.Item>
          </Descriptions>
          
          {/* 字幕上传 */}
          <Card title="字幕文件" size="small" style={{ marginTop: 16 }}>
            {task.metadata?.subtitle_file ? (
              <Alert 
                message="已上传字幕文件" 
                description={task.metadata.subtitle_file}
                type="success" 
                showIcon />
            ) : (
              <Space>
                <Upload
                  beforeUpload={(file) => {
                    setSubtitleFile(file);
                    return false;
                  }}
                  accept=".srt,.vtt"
                  maxCount={1}>
                  <Button icon={<UploadOutlined />}>选择字幕文件</Button>
                </Upload>
                <Button 
                  type="primary" 
                  loading={uploading}
                  disabled={!subtitleFile}
                  onClick={handleSubtitleUpload}>
                  上传
                </Button>
                {subtitleFile && (
                  <Text type="secondary">{subtitleFile.name}</Text>
                )}
              </Space>
            )}
          </Card>
        </TabPane>
        
        {/* Tab 2: 账号执行详情（重要） */}
        <TabPane 
          tab={
            <Badge count={groupExecution?.accounts.length || 0} offset={[10, 0]}>
              账号执行详情
            </Badge>
          } 
          key="accounts">
          <List
            dataSource={groupExecution?.accounts || []}
            renderItem={(account: AccountExecution) => (
              <Card 
                size="small" 
                style={{ marginBottom: 16 }}
                title={
                  <Space>
                    <Avatar style={{ backgroundColor: getStatusColor(account.status) }}>
                      {account.account_name.substring(0, 1)}
                    </Avatar>
                    <Text strong>{account.account_name}</Text>
                    <Tag>{account.platform}</Tag>
                    <Tag color={getStatusColor(account.status)}>
                      {getStatusText(account.status)}
                    </Tag>
                  </Space>
                }
                extra={
                  <Space>
                    {account.video_url && (
                      <Button 
                        type="link" 
                        icon={<PlayCircleOutlined />}
                        href={account.video_url} 
                        target="_blank">
                        查看视频
                      </Button>
                    )}
                    {account.status === 'failed' && (
                      <Button 
                        type="link" 
                        danger
                        onClick={() => retryAccount(account.task_id)}>
                        重试
                      </Button>
                    )}
                  </Space>
                }>
                
                <Row gutter={16}>
                  <Col span={12}>
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="任务ID">
                        {account.task_id.substring(0, 8)}...
                      </Descriptions.Item>
                      <Descriptions.Item label="执行耗时">
                        {account.duration ? `${account.duration}秒` : '-'}
                      </Descriptions.Item>
                      {account.error_message && (
                        <Descriptions.Item label="错误信息">
                          <Text type="danger">{account.error_message}</Text>
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  </Col>
                  
                  <Col span={12}>
                    {account.status === 'completed' && account.performance && (
                      <Card size="small" title="发布数据" bordered={false}>
                        <Row gutter={8}>
                          <Col span={12}>
                            <Statistic 
                              title="观看" 
                              value={account.performance.views} 
                              valueStyle={{ fontSize: 14 }} />
                          </Col>
                          <Col span={12}>
                            <Statistic 
                              title="点赞" 
                              value={account.performance.likes}
                              valueStyle={{ fontSize: 14 }} />
                          </Col>
                          <Col span={12}>
                            <Statistic 
                              title="评论" 
                              value={account.performance.comments}
                              valueStyle={{ fontSize: 14 }} />
                          </Col>
                          <Col span={12}>
                            <Statistic 
                              title="完播率" 
                              value={account.performance.retention_rate}
                              suffix="%"
                              valueStyle={{ fontSize: 14 }} />
                          </Col>
                        </Row>
                      </Card>
                    )}
                  </Col>
                </Row>
              </Card>
            )}
          />
        </TabPane>
        
        {/* Tab 3: 汇总数据 */}
        <TabPane tab="汇总数据" key="summary">
          <Card title="整体表现" size="small">
            <Row gutter={16}>
              <Col span={8}>
                <Card size="small" bordered={false}>
                  <Statistic 
                    title="总观看量" 
                    value={groupExecution?.summary.total_views || 0} />
                  <Progress 
                    percent={100} 
                    strokeColor="#52c41a" 
                    showInfo={false} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false}>
                  <Statistic 
                    title="总点赞数" 
                    value={groupExecution?.summary.total_likes || 0} />
                  <Progress 
                    percent={75} 
                    strokeColor="#1890ff" 
                    showInfo={false} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false}>
                  <Statistic 
                    title="平均完播率" 
                    value={calculateAvgRetention(groupExecution?.accounts || [])}
                    suffix="%" />
                  <Progress 
                    percent={calculateAvgRetention(groupExecution?.accounts || [])} 
                    strokeColor="#faad14" 
                    showInfo={false} />
                </Card>
              </Col>
            </Row>
          </Card>
          
          {/* 账号排名 */}
          <Card title="账号表现排名" size="small" style={{ marginTop: 16 }}>
            <List
              dataSource={sortAccountsByPerformance(groupExecution?.accounts || [])}
              renderItem={(account: AccountExecution, index: number) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Badge count={index + 1} 
                        style={{ backgroundColor: getRankColor(index) }} />
                    }
                    title={account.account_name}
                    description={`观看: ${account.performance.views} | 点赞: ${account.performance.likes}`}
                  />
                  <div>
                    <Tag color="blue">CTR: {account.performance.ctr}%</Tag>
                    <Tag color="green">完播: {account.performance.retention_rate}%</Tag>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </TabPane>
        
        {/* Tab 4: 执行日志 */}
        <TabPane tab="执行日志" key="logs">
          <Timeline>
            {task.metadata?.logs?.map((log, index) => (
              <Timeline.Item key={index} color={getLogColor(log)}>
                <Text code>{log}</Text>
              </Timeline.Item>
            )) || <Empty description="暂无日志" />}
          </Timeline>
        </TabPane>
      </Tabs>
    </Drawer>
  );
};
```

### 1.4 任务列表组件

```tsx
const TaskExecutionList: React.FC = () => {
  const [tasks, setTasks] = useState<TaskExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    status: '',
    config_id: '',
    account_id: '',
    date_range: []
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  });
  
  const columns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text copyable>{id.substring(0, 8)}...</Text>
        </Tooltip>
      )
    },
    {
      title: '配置名称',
      dataIndex: 'config_name',
      width: 150,
      render: (name: string, record: TaskExecution) => (
        <Space direction="vertical" size={0}>
          <Text>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.group_name}
          </Text>
        </Space>
      )
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_name',
      width: 150
    },
    {
      title: '状态',
      dataIndex: 'pipeline_status',
      width: 100,
      render: (status: string) => {
        const config = {
          'pending': { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
          'running': { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
          'completed': { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
          'failed': { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
        }[status];
        
        return (
          <Badge status={config.color} text={
            <Space>
              {config.icon}
              {config.text}
            </Space>
          } />
        );
      }
    },
    {
      title: '执行时间',
      dataIndex: 'created_at',
      width: 150,
      render: (time: string) => moment(time).format('MM-DD HH:mm:ss')
    },
    {
      title: '耗时',
      width: 80,
      render: (_: any, record: TaskExecution) => {
        if (!record.started_at || !record.completed_at) return '-';
        const duration = moment(record.completed_at).diff(moment(record.started_at), 'seconds');
        return `${duration}秒`;
      }
    },
    {
      title: '操作',
      width: 200,
      fixed: 'right',
      render: (_: any, record: TaskExecution) => (
        <Space>
          <Button 
            type="link" 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => showTaskDetail(record)}>
            查看
          </Button>
          <Button 
            type="link" 
            size="small" 
            icon={<BarChartOutlined />}
            onClick={() => showPerformance(record)}>
            数据
          </Button>
          {record.pipeline_status === 'failed' && (
            <Button 
              type="link" 
              size="small" 
              danger
              icon={<ReloadOutlined />}
              onClick={() => retryTask(record.task_id)}>
              重试
            </Button>
          )}
        </Space>
      )
    }
  ];
  
  return (
    <Card>
      {/* 筛选条件 */}
      <Space style={{ marginBottom: 16 }}>
        <Select 
          style={{ width: 120 }}
          placeholder="状态"
          allowClear
          value={filters.status}
          onChange={v => setFilters({ ...filters, status: v })}>
          <Option value="pending">等待中</Option>
          <Option value="running">运行中</Option>
          <Option value="completed">已完成</Option>
          <Option value="failed">失败</Option>
        </Select>
        
        <Select 
          style={{ width: 200 }}
          placeholder="选择配置"
          allowClear
          value={filters.config_id}
          onChange={v => setFilters({ ...filters, config_id: v })}>
          {configs.map(c => (
            <Option key={c.config_id} value={c.config_id}>
              {c.config_name}
            </Option>
          ))}
        </Select>
        
        <RangePicker 
          value={filters.date_range}
          onChange={v => setFilters({ ...filters, date_range: v })} />
        
        <Button type="primary" onClick={loadTasks}>查询</Button>
        <Button onClick={resetFilters}>重置</Button>
      </Space>
      
      <Table
        columns={columns}
        dataSource={tasks}
        loading={loading}
        rowKey="task_id"
        pagination={pagination}
        onChange={handleTableChange}
        scroll={{ x: 1200 }}
      />
    </Card>
  );
};
```

## 2. 需要的接口

### 2.1 获取任务列表
```http
GET /api/auto-publish/tasks

Query参数:
  - page: number (默认1)
  - page_size: number (默认20)
  - status: string (可选)
  - config_id: string (可选)
  - account_id: string (可选)
  - start_date: string (可选)
  - end_date: string (可选)

响应:
{
  "tasks": [...],
  "total": 1256,
  "page": 1,
  "page_size": 20
}
```

### 2.2 获取账号组执行详情（重要）
```http
GET /api/auto-publish/tasks/{config_id}/group-executions

Query参数:
  - execution_time: string (执行时间，用于查找同批次任务)

响应:
{
  "config_id": "config_001",
  "config_name": "每日故事发布",
  "group_id": "story_channels",
  "group_name": "故事频道组",
  "execution_time": "2024-12-25T20:00:00Z",
  "total_accounts": 3,
  "accounts": [
    {
      "account_id": "yt_001",
      "account_name": "小说频道1",
      "platform": "youtube",
      "task_id": "task_001",
      "status": "completed",
      "video_url": "https://youtube.com/watch?v=xxx",
      "duration": 300,
      "performance": {
        "views": 5234,
        "likes": 234,
        "comments": 45,
        "shares": 12,
        "watch_time_minutes": 12340,
        "ctr": 5.2,
        "retention_rate": 68.5,
        "subscriber_gained": 34
      }
    },
    {
      "account_id": "yt_002",
      "account_name": "小说频道2",
      "platform": "youtube",
      "task_id": "task_002",
      "status": "completed",
      "video_url": "https://youtube.com/watch?v=yyy",
      "duration": 280,
      "performance": {
        "views": 4123,
        "likes": 189,
        "comments": 34,
        "shares": 8,
        "watch_time_minutes": 9876,
        "ctr": 4.8,
        "retention_rate": 65.2,
        "subscriber_gained": 28
      }
    },
    {
      "account_id": "yt_003",
      "account_name": "小说频道3",
      "platform": "youtube",
      "task_id": "task_003",
      "status": "failed",
      "error_message": "Pipeline execution failed: timeout",
      "duration": null,
      "performance": null
    }
  ],
  "summary": {
    "total": 3,
    "success": 2,
    "failed": 1,
    "running": 0,
    "pending": 0,
    "avg_duration": 290,
    "total_views": 9357,
    "total_likes": 423
  }
}
```

### 2.3 上传字幕文件
```http
POST /api/auto-publish/tasks/{task_id}/subtitle

请求体: FormData
  - subtitle: File (SRT或VTT格式)

响应:
{
  "success": true,
  "file_path": "/subtitles/task_001.srt"
}
```

### 2.4 获取任务性能数据
```http
GET /api/auto-publish/tasks/{task_id}/performance

响应:
{
  "task_id": "task_001",
  "platform": "youtube",
  "video_url": "https://youtube.com/watch?v=xxx",
  "performance": {
    "views": 5234,
    "likes": 234,
    "comments": 45,
    "shares": 12,
    "watch_time_minutes": 12340,
    "ctr": 5.2,
    "retention_rate": 68.5,
    "subscriber_gained": 34,
    "revenue": 12.5
  },
  "updated_at": "2024-12-25T22:00:00Z"
}
```

### 2.5 重试任务
```http
POST /api/auto-publish/tasks/{task_id}/retry

响应:
{
  "success": true,
  "new_task_id": "task_retry_001"
}
```

## 3. 后端执行流程

### 3.1 获取账号组执行详情流程
```python
@router.get("/tasks/{config_id}/group-executions")
async def get_group_executions(
    config_id: str,
    execution_time: str = Query(...),
    current_user = Depends(get_current_user)
):
    """获取账号组的所有账号执行情况"""
    db = get_db_manager()
    
    # 1. 获取配置信息
    config = db.query_one("""
        SELECT 
            pc.*,
            ag.group_name
        FROM publish_configs pc
        JOIN account_groups ag ON pc.group_id = ag.group_id
        WHERE pc.config_id = ?
    """, (config_id,))
    
    if not config:
        raise HTTPException(404, "Config not found")
    
    # 2. 获取同批次的所有任务（同一配置、相近时间）
    tasks = db.query("""
        SELECT 
            apt.*,
            a.account_name,
            a.platform
        FROM auto_publish_tasks apt
        JOIN accounts a ON apt.account_id = a.account_id
        WHERE apt.config_id = ?
          AND ABS(TIMESTAMPDIFF(MINUTE, apt.created_at, ?)) <= 5
        ORDER BY apt.account_id
    """, (config_id, execution_time))
    
    # 3. 构建账号执行列表
    accounts = []
    total_views = 0
    total_likes = 0
    success_count = 0
    
    for task in tasks:
        # 获取性能数据
        performance = None
        if task['metadata']:
            metadata = json.loads(task['metadata'])
            performance = metadata.get('performance')
            
            if performance:
                total_views += performance.get('views', 0)
                total_likes += performance.get('likes', 0)
        
        if task['pipeline_status'] == 'completed':
            success_count += 1
        
        accounts.append({
            'account_id': task['account_id'],
            'account_name': task['account_name'],
            'platform': task['platform'],
            'task_id': task['task_id'],
            'status': task['pipeline_status'],
            'video_url': json.loads(task['pipeline_result'] or '{}').get('video_url'),
            'duration': calculate_duration(task['started_at'], task['completed_at']),
            'error_message': task['error_message'],
            'performance': performance
        })
    
    # 4. 计算汇总数据
    summary = {
        'total': len(tasks),
        'success': success_count,
        'failed': len([t for t in tasks if t['pipeline_status'] == 'failed']),
        'running': len([t for t in tasks if t['pipeline_status'] == 'running']),
        'pending': len([t for t in tasks if t['pipeline_status'] == 'pending']),
        'avg_duration': calculate_avg_duration(tasks),
        'total_views': total_views,
        'total_likes': total_likes
    }
    
    return {
        'config_id': config_id,
        'config_name': config['config_name'],
        'group_id': config['group_id'],
        'group_name': config['group_name'],
        'execution_time': execution_time,
        'total_accounts': len(accounts),
        'accounts': accounts,
        'summary': summary
    }
```

### 3.2 上传字幕文件流程
```python
@router.post("/tasks/{task_id}/subtitle")
async def upload_subtitle(
    task_id: str,
    subtitle: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """上传字幕文件"""
    db = get_db_manager()
    
    # 1. 验证任务存在
    task = db.query_one(
        "SELECT * FROM auto_publish_tasks WHERE task_id = ?",
        (task_id,)
    )
    if not task:
        raise HTTPException(404, "Task not found")
    
    # 2. 验证文件格式
    if not subtitle.filename.endswith(('.srt', '.vtt')):
        raise HTTPException(400, "Invalid subtitle format. Only SRT and VTT are supported")
    
    # 3. 保存文件
    subtitle_dir = Path("subtitles")
    subtitle_dir.mkdir(exist_ok=True)
    
    file_path = subtitle_dir / f"{task_id}_{subtitle.filename}"
    
    with open(file_path, "wb") as f:
        content = await subtitle.read()
        f.write(content)
    
    # 4. 更新任务元数据
    metadata = json.loads(task['metadata'] or '{}')
    metadata['subtitle_file'] = str(file_path)
    
    db.execute("""
        UPDATE auto_publish_tasks 
        SET metadata = ?
        WHERE task_id = ?
    """, (json.dumps(metadata), task_id))
    
    return {
        "success": True,
        "file_path": str(file_path)
    }
```

## 4. 数据模型

使用现有`auto_publish_tasks`表，通过metadata字段扩展存储：
- 字幕文件路径
- 视频URL
- 性能数据
- 执行日志

## 5. 数据库交互

### 5.1 核心SQL查询

```sql
-- 获取任务列表（含关联信息）
SELECT 
    apt.*,
    pc.config_name,
    ag.group_name,
    pr.pipeline_name,
    a.account_name
FROM auto_publish_tasks apt
LEFT JOIN publish_configs pc ON apt.config_id = pc.config_id
LEFT JOIN account_groups ag ON apt.group_id = ag.group_id
LEFT JOIN pipeline_registry pr ON apt.pipeline_id = pr.pipeline_id
LEFT JOIN accounts a ON apt.account_id = a.account_id
WHERE 1=1
  AND (? IS NULL OR apt.pipeline_status = ?)
  AND (? IS NULL OR apt.config_id = ?)
  AND (? IS NULL OR apt.created_at >= ?)
  AND (? IS NULL OR apt.created_at <= ?)
ORDER BY apt.created_at DESC
LIMIT ? OFFSET ?;

-- 获取同批次任务（账号组执行）
SELECT 
    apt.*,
    a.account_name,
    a.platform,
    JSON_EXTRACT(apt.metadata, '$.performance') as performance
FROM auto_publish_tasks apt
JOIN accounts a ON apt.account_id = a.account_id
WHERE apt.config_id = ?
  AND DATE(apt.created_at) = DATE(?)
  AND HOUR(apt.created_at) = HOUR(?)
ORDER BY apt.account_id;

-- 获取任务性能统计
SELECT 
    COUNT(*) as total_tasks,
    SUM(JSON_EXTRACT(metadata, '$.performance.views')) as total_views,
    SUM(JSON_EXTRACT(metadata, '$.performance.likes')) as total_likes,
    AVG(JSON_EXTRACT(metadata, '$.performance.retention_rate')) as avg_retention
FROM auto_publish_tasks
WHERE config_id = ?
  AND pipeline_status = 'completed'
  AND DATE(created_at) = DATE(?);
```

## 6. 前端实现要点

### 6.1 账号数据聚合展示
```tsx
// 计算账号组的汇总数据
const calculateGroupSummary = (accounts: AccountExecution[]) => {
  const summary = {
    total_views: 0,
    total_likes: 0,
    total_comments: 0,
    avg_retention: 0,
    avg_ctr: 0
  };
  
  let validCount = 0;
  
  accounts.forEach(account => {
    if (account.status === 'completed' && account.performance) {
      summary.total_views += account.performance.views;
      summary.total_likes += account.performance.likes;
      summary.total_comments += account.performance.comments;
      summary.avg_retention += account.performance.retention_rate;
      summary.avg_ctr += account.performance.ctr;
      validCount++;
    }
  });
  
  if (validCount > 0) {
    summary.avg_retention /= validCount;
    summary.avg_ctr /= validCount;
  }
  
  return summary;
};
```

### 6.2 账号表现排名
```tsx
const sortAccountsByPerformance = (accounts: AccountExecution[]) => {
  return [...accounts]
    .filter(a => a.status === 'completed' && a.performance)
    .sort((a, b) => {
      // 综合评分：观看量 * 0.5 + 点赞 * 0.3 + 完播率 * 0.2
      const scoreA = (a.performance.views * 0.5) + 
                    (a.performance.likes * 0.3) + 
                    (a.performance.retention_rate * 100 * 0.2);
      const scoreB = (b.performance.views * 0.5) + 
                    (b.performance.likes * 0.3) + 
                    (b.performance.retention_rate * 100 * 0.2);
      return scoreB - scoreA;
    });
};
```

## 7. 测试要点

### 7.1 功能测试
- [ ] 任务列表筛选和分页
- [ ] 账号组执行详情展示
- [ ] 每个账号的独立数据展示
- [ ] 字幕文件上传
- [ ] 任务重试功能
- [ ] 性能数据展示

### 7.2 数据测试
- [ ] 大量账号的聚合计算
- [ ] 性能数据的准确性
- [ ] 同批次任务的识别

## 8. 注意事项

1. **批次识别**：同一配置在相近时间（5分钟内）的任务视为同批次
2. **性能数据**：需要定期从平台API更新
3. **字幕管理**：支持SRT和VTT格式
4. **数据聚合**：注意处理空值和异常数据
5. **权限控制**：敏感数据（如收益）需要权限验证