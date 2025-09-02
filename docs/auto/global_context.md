# 自动发布系统 - 全局上下文和规范

## 系统定义

### 核心概念
1. **Pipeline**: 视频制作工作流，定义如何生成视频内容
2. **PublishConfig**: Pipeline与账号组的绑定配置，定义使用哪个Pipeline、哪些账号、何时执行
3. **Task**: 一次实际的Pipeline执行记录，记录生成的视频和执行状态
4. **AccountGroup**: 账号组，包含多个YouTube账号

### 数据关系
```
Pipeline (1) --> (N) PublishConfig (1) --> (N) Task
                         |
                         v
                   AccountGroup (1) --> (N) Account
```

## 命名规范

### 文件命名
- **React组件**: PascalCase，如 `PipelineManager.tsx`
- **服务文件**: camelCase，如 `autoPublish.ts`
- **样式文件**: kebab-case，如 `pipeline-manager.less`

### 代码命名
```typescript
// 组件名：PascalCase
const PipelineManager: React.FC = () => {}

// 接口名：PascalCase，I前缀
interface IPipeline {}

// 变量名：camelCase
const pipelineList = []

// 常量：UPPER_SNAKE_CASE
const API_BASE_URL = '/api/auto-publish'

// 函数名：camelCase
const loadPipelineList = async () => {}
```

### API路径规范
```
GET    /api/auto-publish/pipelines              # 获取列表
POST   /api/auto-publish/pipelines              # 创建
GET    /api/auto-publish/pipelines/{id}         # 获取详情
PUT    /api/auto-publish/pipelines/{id}         # 更新
DELETE /api/auto-publish/pipelines/{id}         # 删除
GET    /api/auto-publish/pipelines/{id}/configs # 获取关联资源
```

### 数据库字段
- 使用snake_case：`pipeline_id`, `config_name`, `created_at`
- 主键格式：`{prefix}_{timestamp}`
  - Pipeline: `pipeline_自定义` 或 `youtube_story_v3`
  - Config: `config_20241225143000`
  - Task: `task_20241225143000_001`
  - Group: `grp_20241225143000`

## 统一交互规范

### 页面布局
```tsx
// 标准列表页结构
<Card>
  {/* 顶部操作栏 */}
  <Space style={{ marginBottom: 16 }}>
    <Input.Search placeholder="搜索" style={{ width: 200 }} />
    <Select placeholder="筛选" style={{ width: 120 }} />
    <Button type="primary" icon={<PlusOutlined />}>创建</Button>
  </Space>
  
  {/* 数据表格 */}
  <Table
    columns={columns}
    dataSource={data}
    rowKey="id"
    pagination={{
      current: 1,
      pageSize: 20,
      total: 100,
      showSizeChanger: false,
      showTotal: (total) => `共 ${total} 条`
    }}
  />
</Card>
```

### 弹窗规范
- **详情展示**: Drawer，宽度900px，从右侧滑出
- **创建/编辑**: Modal，宽度800px，居中显示
- **确认操作**: Popconfirm，附着在按钮上

### 表单规范
```tsx
// 统一表单布局
<Form form={form} layout="vertical">
  <Row gutter={16}>
    <Col span={12}>
      <Form.Item name="field1" label="字段1" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
    </Col>
    <Col span={12}>
      <Form.Item name="field2" label="字段2">
        <Select />
      </Form.Item>
    </Col>
  </Row>
</Form>
```

### 消息提示
```typescript
// 成功
message.success('操作成功');

// 失败
message.error('操作失败：' + error.message);

// 加载中
const hide = message.loading('正在处理...', 0);
// 处理完成后
hide();
```

### 状态标签配色
```typescript
const STATUS_CONFIG = {
  // Pipeline状态
  'active': { color: 'green', text: '启用' },
  'inactive': { color: 'default', text: '停用' },
  'testing': { color: 'blue', text: '测试中' },
  
  // Task状态
  'pending': { color: 'default', text: '等待中' },
  'running': { color: 'blue', text: '运行中' },
  'completed': { color: 'green', text: '已完成' },
  'failed': { color: 'red', text: '失败' }
};
```

## 数据结构定义

### Pipeline
```typescript
interface Pipeline {
  pipeline_id: string;          // 唯一标识
  pipeline_name: string;        // 显示名称
  pipeline_type: string;        // 类型：content_generation/metadata/processing
  pipeline_class: string;       // Python类路径
  config_schema: {              // 参数配置模式
    type: 'object';
    properties: {
      [key: string]: {
        type: string;
        description?: string;
        default?: any;
        required?: boolean;
        minimum?: number;
        maximum?: number;
        enum?: any[];
      }
    };
    required?: string[];
  };
  supported_platforms: ['youtube']; // 只支持YouTube
  version: string;              // 版本号
  status: 'active' | 'inactive' | 'testing';
  metadata?: any;               // 扩展数据
  created_at: string;           // ISO 8601格式
  updated_at: string;
}
```

### PublishConfig
```typescript
interface PublishConfig {
  config_id: string;
  config_name: string;
  group_id: string;
  pipeline_id: string;
  pipeline_config?: any;        // Pipeline参数值
  trigger_type: 'scheduled' | 'monitor';
  trigger_config: {
    // 定时触发
    schedule?: {
      type: 'daily' | 'weekly' | 'monthly' | 'cron';
      time?: string;            // HH:mm格式
      weekday?: number;         // 0-6
      day?: number;             // 1-31
      cron?: string;            // cron表达式
    };
    // 监控触发
    monitor?: {
      platform: 'youtube';
      type: string;
      target: string;
      check_interval: number;   // 秒
    };
  };
  priority: number;             // 0-100
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

### Task
```typescript
interface Task {
  task_id: string;
  config_id: string;
  group_id: string;
  account_id: string;
  pipeline_id: string;
  pipeline_status: 'pending' | 'running' | 'completed' | 'failed';
  pipeline_result?: {
    video_path?: string;
    video_url?: string;
    title?: string;
    description?: string;
  };
  publish_status: 'pending' | 'published' | 'failed';
  publish_result?: {
    video_id?: string;
    url?: string;
  };
  priority: number;
  retry_count: number;
  error_message?: string;
  metadata?: {
    subtitle_file?: string;
    performance?: {
      views: number;
      likes: number;
      comments: number;
      retention_rate: number;
    };
    logs?: string[];
  };
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
}
```

### AccountGroup
```typescript
interface AccountGroup {
  group_id: string;
  group_name: string;
  group_type: 'experiment' | 'production' | 'test';
  description?: string;
  is_active: boolean;
  metadata?: any;
  created_at: string;
  updated_at: string;
}
```

## API响应格式

### 成功响应
```typescript
// 单个对象
{
  "pipeline_id": "youtube_story_v3",
  "pipeline_name": "YouTube故事生成V3",
  // ...
}

// 列表响应
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}

// 操作响应
{
  "success": true,
  "message": "操作成功"
}
```

### 错误响应
```typescript
{
  "detail": "错误信息"
}
// HTTP状态码：400/404/500
```

## 前端服务层

### 基础服务类
```typescript
// services/autoPublish.ts
class AutoPublishService {
  private api = axios.create({
    baseURL: '/api/auto-publish',
    timeout: 30000
  });

  // Pipeline相关
  async listPipelines(params?: { page?: number; page_size?: number; status?: string }) {
    const response = await this.api.get('/pipelines', { params });
    return response.data;
  }

  async getPipeline(pipelineId: string) {
    const response = await this.api.get(`/pipelines/${pipelineId}`);
    return response.data;
  }

  async createPipeline(data: Partial<Pipeline>) {
    const response = await this.api.post('/pipelines', data);
    return response.data;
  }

  async updatePipeline(pipelineId: string, data: Partial<Pipeline>) {
    const response = await this.api.put(`/pipelines/${pipelineId}`, data);
    return response.data;
  }

  async deletePipeline(pipelineId: string) {
    const response = await this.api.delete(`/pipelines/${pipelineId}`);
    return response.data;
  }

  // 类似的方法用于PublishConfig、Task、AccountGroup
}

export const autoPublishService = new AutoPublishService();
```

## 错误处理

### 前端错误处理
```typescript
try {
  const result = await autoPublishService.createPipeline(data);
  message.success('创建成功');
  return result;
} catch (error: any) {
  const errorMsg = error.response?.data?.detail || error.message || '操作失败';
  message.error(errorMsg);
  throw error;
}
```

### 后端错误处理
```python
from fastapi import HTTPException

# 参数验证错误
if not pipeline_id:
    raise HTTPException(status_code=400, detail="Pipeline ID is required")

# 资源不存在
if not pipeline:
    raise HTTPException(status_code=404, detail="Pipeline not found")

# 业务逻辑错误
if active_tasks > 0:
    raise HTTPException(status_code=400, detail=f"Cannot delete pipeline with {active_tasks} active tasks")

# 服务器错误
try:
    # 操作
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## 数据验证规则

### Pipeline ID
- 格式：`^[a-z0-9_]+$`
- 长度：3-50字符
- 示例：`youtube_story_v3`

### 配置名称
- 长度：1-100字符
- 不能重复

### 优先级
- 范围：0-100
- 默认：50

### Cron表达式
- 格式：标准cron格式
- 示例：`0 20 * * *`（每天20:00）

### 时间格式
- 时间：`HH:mm`（24小时制）
- 日期时间：ISO 8601格式 `2024-12-25T20:00:00Z`

## 平台说明

系统只支持YouTube平台：
- 平台标识：`youtube`
- 所有Pipeline的`supported_platforms`字段默认为`['youtube']`
- 监控配置的`platform`字段固定为`youtube`
- 账号的`platform`字段固定为`youtube`