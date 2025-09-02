# Tab 2: 发布配置管理

> 参考：[global_context.md](./global_context.md) - 全局上下文和规范

## 1. 前端方案

### 1.1 界面布局
```
┌─────────────────────────────────────────────────────────────────┐
│  发布配置管理                                      [+ 创建配置]   │
├─────────────────────────────────────────────────────────────────┤
│  🔍 搜索: [___________] [Pipeline▼] [账号组▼] [状态▼]  [搜索]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  配置列表（表格）                                                 │
│  ┌────────┬──────────┬──────────┬────────┬────────┬───────────┐│
│  │配置名称 │Pipeline  │账号组    │调度方式│执行数  │操作        ││
│  ├────────┼──────────┼──────────┼────────┼────────┼───────────┤│
│  │每日故事│story_v3  │story_grp │每日20:00│156任务│查看 编辑 删除││
│  │测试配置│meta_gen  │test_grp  │监控触发 │45任务 │查看 编辑 删除││
│  └────────┴──────────┴──────────┴────────┴────────┴───────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 组件结构
```tsx
// components/AutoPublish/PublishConfigManager.tsx
import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, InputNumber,
  Tag, Space, Drawer, Descriptions, Timeline, Badge, message,
  DatePicker, TimePicker, Radio, Tabs, List, Statistic
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  CalendarOutlined, RobotOutlined, ClockCircleOutlined
} from '@ant-design/icons';

interface PublishConfig {
  config_id: string;
  config_name: string;
  group_id: string;
  group_name?: string;
  pipeline_id: string;
  pipeline_name?: string;
  pipeline_config?: any;  // Pipeline参数配置
  trigger_type: 'scheduled' | 'monitor';
  trigger_config: TriggerConfig;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // 统计信息
  task_count?: number;
  success_count?: number;
  failed_count?: number;
  last_execution?: string;
  next_execution?: string;
}

interface TriggerConfig {
  // 定时触发配置
  schedule?: {
    type: 'daily' | 'weekly' | 'monthly' | 'cron';
    time?: string;  // HH:mm
    weekday?: number;  // 0-6
    day?: number;  // 1-31
    cron?: string;  // cron表达式
  };
  // 监控触发配置
  monitor?: {
    platform: string;
    type: string;
    target: string;
    check_interval: number;
  };
}

interface TaskExecution {
  task_id: string;
  account_id: string;
  account_name?: string;
  pipeline_status: 'pending' | 'running' | 'completed' | 'failed';
  publish_status: 'pending' | 'published' | 'failed';
  created_at: string;
  completed_at?: string;
  duration?: number;
  error_message?: string;
}

interface TaskStats {
  total: number;
  success: number;
  failed: number;
  running: number;
  pending: number;
  avg_duration: number;
  success_rate: number;
}
```

### 1.3 创建/编辑配置表单

#### 1.3.1 基本信息
```tsx
const ConfigForm: React.FC = () => {
  const [triggerType, setTriggerType] = useState<'scheduled' | 'monitor'>('scheduled');
  const [pipelineSchema, setPipelineSchema] = useState<any>(null);
  
  return (
    <Form form={form} layout="vertical">
      <Form.Item name="config_name" label="配置名称" rules={[{ required: true }]}>
        <Input placeholder="例如: 每日故事发布" />
      </Form.Item>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="pipeline_id" label="选择Pipeline" rules={[{ required: true }]}>
            <Select onChange={handlePipelineChange} placeholder="选择Pipeline">
              {pipelines.map(p => (
                <Option key={p.pipeline_id} value={p.pipeline_id}>
                  {p.pipeline_name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="group_id" label="选择账号组" rules={[{ required: true }]}>
            <Select placeholder="选择账号组">
              {groups.map(g => (
                <Option key={g.group_id} value={g.group_id}>
                  {g.group_name} ({g.member_count}个账号)
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
      
      <Form.Item name="priority" label="优先级" 
        tooltip="数值越大优先级越高，范围0-100">
        <Slider min={0} max={100} defaultValue={50} 
          marks={{ 0: '低', 50: '中', 100: '高' }} />
      </Form.Item>
      
      {/* Pipeline参数配置（根据选择的Pipeline动态生成） */}
      {pipelineSchema && (
        <Card title="Pipeline参数配置" size="small">
          {renderPipelineParams(pipelineSchema)}
        </Card>
      )}
      
      {/* 触发方式配置 */}
      <Form.Item label="触发方式">
        <Radio.Group value={triggerType} onChange={e => setTriggerType(e.target.value)}>
          <Radio.Button value="scheduled">
            <CalendarOutlined /> 定时触发
          </Radio.Button>
          <Radio.Button value="monitor">
            <RobotOutlined /> 监控触发
          </Radio.Button>
        </Radio.Group>
      </Form.Item>
      
      {triggerType === 'scheduled' ? renderScheduleConfig() : renderMonitorConfig()}
    </Form>
  );
};
```

#### 1.3.2 定时触发配置
```tsx
const renderScheduleConfig = () => (
  <Card title="定时触发配置" size="small">
    <Form.Item name={['trigger_config', 'schedule', 'type']} label="调度类型">
      <Radio.Group>
        <Radio value="daily">每日</Radio>
        <Radio value="weekly">每周</Radio>
        <Radio value="monthly">每月</Radio>
        <Radio value="cron">Cron表达式</Radio>
      </Radio.Group>
    </Form.Item>
    
    <Form.Item 
      noStyle
      shouldUpdate={(prev, cur) => 
        prev.trigger_config?.schedule?.type !== cur.trigger_config?.schedule?.type
      }>
      {({ getFieldValue }) => {
        const scheduleType = getFieldValue(['trigger_config', 'schedule', 'type']);
        
        switch (scheduleType) {
          case 'daily':
            return (
              <Form.Item name={['trigger_config', 'schedule', 'time']} label="执行时间">
                <TimePicker format="HH:mm" />
              </Form.Item>
            );
          
          case 'weekly':
            return (
              <>
                <Form.Item name={['trigger_config', 'schedule', 'weekday']} label="星期">
                  <Select>
                    <Option value={0}>周日</Option>
                    <Option value={1}>周一</Option>
                    <Option value={2}>周二</Option>
                    <Option value={3}>周三</Option>
                    <Option value={4}>周四</Option>
                    <Option value={5}>周五</Option>
                    <Option value={6}>周六</Option>
                  </Select>
                </Form.Item>
                <Form.Item name={['trigger_config', 'schedule', 'time']} label="执行时间">
                  <TimePicker format="HH:mm" />
                </Form.Item>
              </>
            );
          
          case 'cron':
            return (
              <Form.Item name={['trigger_config', 'schedule', 'cron']} label="Cron表达式"
                rules={[{ pattern: /^[\d\s\*\/\-\,]+$/ }]}>
                <Input placeholder="例如: 0 20 * * *" />
              </Form.Item>
            );
          
          default:
            return null;
        }
      }}
    </Form.Item>
  </Card>
);
```

### 1.4 配置详情抽屉
```tsx
const ConfigDetail: React.FC<{ config: PublishConfig }> = ({ config }) => {
  const [tasks, setTasks] = useState<TaskExecution[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  
  useEffect(() => {
    loadTaskExecutions();
    loadTaskStats();
  }, [config.config_id]);
  
  return (
    <Drawer title="配置详情" width={900} visible={visible} onClose={onClose}>
      <Descriptions title="基本信息" bordered column={2}>
        <Descriptions.Item label="配置名称">{config.config_name}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Badge status={config.is_active ? 'success' : 'default'} 
            text={config.is_active ? '启用' : '停用'} />
        </Descriptions.Item>
        <Descriptions.Item label="Pipeline">{config.pipeline_name}</Descriptions.Item>
        <Descriptions.Item label="账号组">{config.group_name}</Descriptions.Item>
        <Descriptions.Item label="触发方式">
          {config.trigger_type === 'scheduled' ? '定时触发' : '监控触发'}
        </Descriptions.Item>
        <Descriptions.Item label="优先级">
          <Progress percent={config.priority} steps={5} size="small" />
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{config.created_at}</Descriptions.Item>
        <Descriptions.Item label="最近执行">{config.last_execution || '-'}</Descriptions.Item>
      </Descriptions>
      
      <Divider />
      
      {/* 执行统计 */}
      {stats && (
        <Card title="执行统计" size="small">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="总执行次数" value={stats.total} />
            </Col>
            <Col span={6}>
              <Statistic title="成功率" value={stats.success_rate} suffix="%" 
                valueStyle={{ color: stats.success_rate > 90 ? '#3f8600' : '#cf1322' }} />
            </Col>
            <Col span={6}>
              <Statistic title="平均耗时" value={stats.avg_duration} suffix="秒" />
            </Col>
            <Col span={6}>
              <Statistic title="失败次数" value={stats.failed} 
                valueStyle={{ color: '#cf1322' }} />
            </Col>
          </Row>
        </Card>
      )}
      
      <Divider />
      
      {/* 执行历史 */}
      <Card title={`执行历史 (${stats?.total || 0}条)`} size="small">
        <Table
          dataSource={tasks}
          loading={loading}
          rowKey="task_id"
          size="small"
          pagination={{
            current: currentPage,
            pageSize: 10,
            total: stats?.total || 0,
            onChange: (page) => {
              setCurrentPage(page);
              loadTaskExecutions(page);
            }
          }}
          columns={[
            {
              title: '任务ID',
              dataIndex: 'task_id',
              width: 120,
              render: (id: string) => (
                <Button type="link" size="small" 
                  onClick={() => navigateToTask(id)}>
                  {id.substring(0, 8)}...
                </Button>
              )
            },
            {
              title: '账号',
              dataIndex: 'account_name',
              width: 120
            },
            {
              title: 'Pipeline状态',
              dataIndex: 'pipeline_status',
              width: 100,
              render: (status: string) => {
                const color = {
                  'completed': 'green',
                  'running': 'blue',
                  'failed': 'red',
                  'pending': 'default'
                }[status];
                return <Tag color={color}>{status}</Tag>;
              }
            },
            {
              title: '发布状态',
              dataIndex: 'publish_status',
              width: 100,
              render: (status: string) => {
                const color = {
                  'published': 'green',
                  'failed': 'red',
                  'pending': 'default'
                }[status];
                return <Tag color={color}>{status}</Tag>;
              }
            },
            {
              title: '执行时间',
              dataIndex: 'created_at',
              width: 150,
              render: (time: string) => moment(time).format('MM-DD HH:mm')
            },
            {
              title: '耗时',
              dataIndex: 'duration',
              width: 80,
              render: (d: number) => d ? `${d}秒` : '-'
            },
            {
              title: '操作',
              width: 100,
              render: (_: any, record: TaskExecution) => (
                <Space>
                  <Button type="link" size="small" 
                    onClick={() => navigateToTask(record.task_id)}>
                    查看
                  </Button>
                  {record.pipeline_status === 'failed' && (
                    <Button type="link" size="small" danger
                      onClick={() => retryTask(record.task_id)}>
                      重试
                    </Button>
                  )}
                </Space>
              )
            }
          ]}
        />
        
        {/* 执行时间线 */}
        <Timeline style={{ marginTop: 16 }}>
          {tasks.slice(0, 5).map(task => (
            <Timeline.Item 
              key={task.task_id}
              color={task.pipeline_status === 'completed' ? 'green' : 'red'}>
              <p>{task.account_name} - {moment(task.created_at).format('MM-DD HH:mm')}</p>
              <p>{task.pipeline_status === 'completed' ? '✅ 成功' : `❌ 失败: ${task.error_message}`}</p>
            </Timeline.Item>
          ))}
        </Timeline>
      </Card>
    </Drawer>
  );
};
```

## 2. 需要的接口

### 2.1 复用现有接口
```http
GET /api/auto-publish/publish-configs
POST /api/auto-publish/publish-configs
```

### 2.2 新增接口

#### 2.2.1 获取配置的执行历史
```http
GET /api/auto-publish/configs/{config_id}/tasks

Query参数:
  - page: number (默认1)
  - page_size: number (默认10)
  - status: string (可选，筛选状态)
  - start_date: string (可选，开始日期)
  - end_date: string (可选，结束日期)

响应:
{
  "tasks": [
    {
      "task_id": "task_20241225_001",
      "account_id": "yt_001",
      "account_name": "小说频道1",
      "pipeline_status": "completed",
      "publish_status": "published",
      "created_at": "2024-12-25T20:00:00Z",
      "completed_at": "2024-12-25T20:05:00Z",
      "duration": 300,
      "error_message": null
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 10
}
```

#### 2.2.2 获取配置执行统计
```http
GET /api/auto-publish/configs/{config_id}/stats

响应:
{
  "total": 156,
  "success": 145,
  "failed": 8,
  "running": 1,
  "pending": 2,
  "avg_duration": 285.5,
  "success_rate": 92.9,
  "last_execution": "2024-12-25T20:00:00Z",
  "next_execution": "2024-12-26T20:00:00Z"
}
```

#### 2.2.3 更新配置
```http
PUT /api/auto-publish/configs/{config_id}

请求体: 同创建，但config_id不可修改

响应: 更新后的配置对象
```

#### 2.2.4 删除配置
```http
DELETE /api/auto-publish/configs/{config_id}

响应:
{
  "success": true,
  "message": "Config deleted successfully"
}
```

#### 2.2.5 启用/禁用配置
```http
POST /api/auto-publish/configs/{config_id}/toggle

请求体:
{
  "is_active": true
}

响应:
{
  "success": true,
  "is_active": true
}
```

## 3. 后端执行流程

### 3.1 创建配置流程
```python
@router.post("/publish-configs")
async def create_publish_config(
    request: CreatePublishConfigRequest,
    current_user = Depends(get_current_user)
):
    """创建发布配置"""
    db = get_db_manager()
    executor = get_account_driven_executor()
    
    # 1. 验证Pipeline存在
    pipeline = get_pipeline_registry().get_pipeline(request.pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    
    # 2. 验证账号组存在
    group = db.query_one(
        "SELECT * FROM account_groups WHERE group_id = ?",
        (request.group_id,)
    )
    if not group:
        raise HTTPException(404, "Account group not found")
    
    # 3. 验证Pipeline参数
    if request.pipeline_config:
        validate_pipeline_config(pipeline.config_schema, request.pipeline_config)
    
    # 4. 创建配置
    config_id = f"config_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    config = PublishConfigModel(
        config_id=config_id,
        config_name=request.config_name,
        group_id=request.group_id,
        pipeline_id=request.pipeline_id,
        pipeline_config=request.pipeline_config,
        trigger_type=request.trigger_type,
        trigger_config=request.trigger_config,
        priority=request.priority,
        is_active=True
    )
    
    db.session.add(config)
    db.session.commit()
    
    # 5. 注册到执行器
    if request.trigger_type == 'scheduled':
        executor.register_scheduled_config(config)
    
    return config.to_dict()
```

### 3.2 获取执行历史流程
```python
@router.get("/configs/{config_id}/tasks")
async def get_config_tasks(
    config_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """获取配置的执行历史"""
    db = get_db_manager()
    
    # 构建查询条件
    conditions = ["config_id = ?"]
    params = [config_id]
    
    if status:
        conditions.append("pipeline_status = ?")
        params.append(status)
    
    if start_date:
        conditions.append("created_at >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("created_at <= ?")
        params.append(end_date)
    
    where_clause = " AND ".join(conditions)
    
    # 查询总数
    total = db.query_one(
        f"SELECT COUNT(*) as count FROM auto_publish_tasks WHERE {where_clause}",
        params
    )['count']
    
    # 查询任务列表
    offset = (page - 1) * page_size
    tasks = db.query(f"""
        SELECT 
            apt.*,
            a.account_name
        FROM auto_publish_tasks apt
        LEFT JOIN accounts a ON apt.account_id = a.account_id
        WHERE {where_clause}
        ORDER BY apt.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

### 3.3 获取执行统计流程
```python
@router.get("/configs/{config_id}/stats")
async def get_config_stats(
    config_id: str,
    current_user = Depends(get_current_user)
):
    """获取配置执行统计"""
    db = get_db_manager()
    
    stats = db.query_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN pipeline_status = 'running' THEN 1 ELSE 0 END) as running,
            SUM(CASE WHEN pipeline_status = 'pending' THEN 1 ELSE 0 END) as pending,
            AVG(CASE WHEN completed_at IS NOT NULL 
                THEN TIMESTAMPDIFF(SECOND, started_at, completed_at) 
                ELSE NULL END) as avg_duration,
            MAX(created_at) as last_execution
        FROM auto_publish_tasks
        WHERE config_id = ?
    """, (config_id,))
    
    # 计算成功率
    if stats['total'] > 0:
        stats['success_rate'] = round(stats['success'] / stats['total'] * 100, 1)
    else:
        stats['success_rate'] = 0
    
    # 获取下次执行时间（如果是定时任务）
    config = db.query_one(
        "SELECT trigger_type, trigger_config FROM publish_configs WHERE config_id = ?",
        (config_id,)
    )
    
    if config and config['trigger_type'] == 'scheduled':
        stats['next_execution'] = calculate_next_execution(config['trigger_config'])
    
    return stats
```

## 4. 数据模型

使用现有模型：
- `publish_configs` - 发布配置表
- `auto_publish_tasks` - 任务执行表
- `account_groups` - 账号组表
- `pipeline_registry` - Pipeline注册表

## 5. 数据库交互

### 5.1 核心SQL查询

```sql
-- 获取配置列表（含统计信息）
SELECT 
    pc.*,
    ag.group_name,
    pr.pipeline_name,
    COUNT(DISTINCT apt.task_id) as task_count,
    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN apt.pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    MAX(apt.created_at) as last_execution
FROM publish_configs pc
LEFT JOIN account_groups ag ON pc.group_id = ag.group_id
LEFT JOIN pipeline_registry pr ON pc.pipeline_id = pr.pipeline_id
LEFT JOIN auto_publish_tasks apt ON pc.config_id = apt.config_id
WHERE pc.is_active = 1
GROUP BY pc.config_id
ORDER BY pc.created_at DESC;

-- 获取配置的执行历史
SELECT 
    apt.*,
    a.account_name,
    TIMESTAMPDIFF(SECOND, apt.started_at, apt.completed_at) as duration
FROM auto_publish_tasks apt
LEFT JOIN accounts a ON apt.account_id = a.account_id
WHERE apt.config_id = ?
ORDER BY apt.created_at DESC
LIMIT ? OFFSET ?;

-- 获取配置的账号组执行情况
SELECT 
    a.account_id,
    a.account_name,
    COUNT(apt.task_id) as total_tasks,
    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks,
    AVG(TIMESTAMPDIFF(SECOND, apt.started_at, apt.completed_at)) as avg_duration
FROM accounts a
JOIN account_group_members agm ON a.account_id = agm.account_id
LEFT JOIN auto_publish_tasks apt ON a.account_id = apt.account_id 
    AND apt.config_id = ?
WHERE agm.group_id = ?
GROUP BY a.account_id;
```

## 6. 前端实现要点

### 6.1 Pipeline参数动态表单
```tsx
const renderPipelineParams = (schema: any) => {
  if (!schema || !schema.properties) return null;
  
  return Object.entries(schema.properties).map(([key, param]: [string, any]) => {
    const isRequired = schema.required?.includes(key);
    
    switch (param.type) {
      case 'string':
        if (param.enum) {
          return (
            <Form.Item 
              key={key}
              name={['pipeline_config', key]} 
              label={key}
              rules={[{ required: isRequired }]}
              tooltip={param.description}>
              <Select>
                {param.enum.map((v: string) => (
                  <Option key={v} value={v}>{v}</Option>
                ))}
              </Select>
            </Form.Item>
          );
        }
        return (
          <Form.Item 
            key={key}
            name={['pipeline_config', key]} 
            label={key}
            rules={[{ required: isRequired }]}
            tooltip={param.description}>
            <Input placeholder={param.description} />
          </Form.Item>
        );
      
      case 'integer':
      case 'number':
        return (
          <Form.Item 
            key={key}
            name={['pipeline_config', key]} 
            label={key}
            rules={[{ required: isRequired }]}
            tooltip={param.description}>
            <InputNumber 
              min={param.minimum} 
              max={param.maximum}
              placeholder={param.description} />
          </Form.Item>
        );
      
      case 'boolean':
        return (
          <Form.Item 
            key={key}
            name={['pipeline_config', key]} 
            label={key}
            valuePropName="checked"
            tooltip={param.description}>
            <Switch />
          </Form.Item>
        );
      
      default:
        return null;
    }
  });
};
```

### 6.2 跳转到任务详情
```tsx
const navigateToTask = (taskId: string) => {
  navigate(`/auto-publish?tab=task&task=${taskId}`);
};
```

### 6.3 定时任务预览
```tsx
const previewSchedule = (triggerConfig: any) => {
  // 计算接下来5次执行时间
  const nextExecutions = calculateNextExecutions(triggerConfig, 5);
  
  return (
    <Timeline>
      {nextExecutions.map((time, index) => (
        <Timeline.Item key={index}>
          {moment(time).format('YYYY-MM-DD HH:mm:ss')}
        </Timeline.Item>
      ))}
    </Timeline>
  );
};
```

## 7. 测试要点

### 7.1 功能测试
- [ ] 配置创建（各种触发方式）
- [ ] Pipeline参数配置验证
- [ ] 配置编辑和更新
- [ ] 配置启用/禁用
- [ ] 执行历史查看
- [ ] 任务重试功能

### 7.2 边界测试
- [ ] 大量执行历史的分页
- [ ] 复杂Pipeline参数配置
- [ ] 并发配置创建

## 8. 注意事项

1. **触发时间计算**：定时任务需要考虑时区问题
2. **参数验证**：Pipeline参数需要严格验证
3. **性能优化**：执行历史查询需要合理索引
4. **状态同步**：配置状态变更需要通知执行器