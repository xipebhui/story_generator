# 统一发布接口文档

## 概述

本文档描述了统一的视频发布接口，**完全替代原有的create接口**。新接口同时支持：
- 立即发布视频（不传scheduled_time或传过去的时间）
- 定时发布视频（传未来的scheduled_time）
- 查询发布任务状态
- 取消发布任务
- 管理发布队列
- 持久化存储，服务重启不丢失任务

## 重要说明

⚠️ **这个接口完全替代了原有的create接口**：
- 原接口：`POST /api/publish/video` (废弃)
- 新接口：`POST /api/publish/schedule` (统一使用)
- 新接口向后兼容，支持所有原有功能

## 接口基础信息

- **基础路径**: `http://localhost:51082/api`（与主服务同一端口）
- **请求格式**: JSON
- **响应格式**: JSON
- **认证方式**: 暂无（后续可添加）
- **持久化**: SQLite数据库存储任务（publish_tasks.db）
- **服务集成**: 发布服务已集成到主API服务中，无需单独启动

## 接口列表

### 1. 创建发布任务

创建一个发布任务，支持立即发布和定时发布。

**接口路径**: `POST /api/publish/schedule`

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| video_id | string | 是 | 视频ID |
| platform | string | 是 | 发布平台：douyin/kuaishou/xiaohongshu |
| account_id | string | 是 | 账号ID |
| scheduled_time | string | 否 | ISO 8601格式的时间，如"2025-08-27T10:00:00"。不传或传过去的时间则立即执行 |
| title | string | 是 | 视频标题 |
| description | string | 否 | 视频描述 |
| tags | array | 否 | 标签数组，如["美食", "探店"] |
| video_path | string | 是 | 视频文件路径 |
| cover_path | string | 否 | 封面图片路径 |
| extra_params | object | 否 | 平台特定的额外参数 |

**请求示例**:

立即发布：
```json
{
  "video_id": "test_0DmxeSNvtsM",
  "platform": "douyin",
  "account_id": "douyin_account_001",
  "title": "精彩视频分享",
  "description": "这是一个测试视频",
  "tags": ["测试", "示例"],
  "video_path": "/outputs/test/video_20250826.mp4",
  "cover_path": "/outputs/test/cover_20250826.jpg"
}
```

定时发布：
```json
{
  "video_id": "test_0DmxeSNvtsM",
  "platform": "douyin",
  "account_id": "douyin_account_001",
  "scheduled_time": "2025-08-27T14:30:00",
  "title": "定时发布测试",
  "description": "这是一个定时发布的测试视频",
  "tags": ["定时", "测试"],
  "video_path": "/outputs/test/video_20250826.mp4"
}
```

**响应示例**:

成功响应：
```json
{
  "task_id": "pub_20250826_a1b2c3d4",
  "status": "scheduled",
  "scheduled_time": "2025-08-27T14:30:00",
  "message": "发布任务已创建"
}
```

**状态说明**:
- `scheduled`: 已计划，等待执行
- `processing`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败
- `cancelled`: 已取消

### 2. 查询发布任务列表

获取发布任务列表，支持分页和状态筛选。

**接口路径**: `GET /api/publish/tasks`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| status | string | 否 | 筛选状态：pending/scheduled/processing/completed/failed/cancelled |
| platform | string | 否 | 筛选平台：douyin/kuaishou/xiaohongshu |
| account_id | string | 否 | 筛选账号ID |
| page | int | 否 | 页码，默认1 |
| limit | int | 否 | 每页数量，默认20，最大100 |
| start_date | string | 否 | 开始日期，ISO格式 |
| end_date | string | 否 | 结束日期，ISO格式 |

**请求示例**:
```
GET /api/publish/tasks?status=scheduled&platform=douyin&page=1&limit=20
```

**响应示例**:
```json
{
  "total": 45,
  "page": 1,
  "limit": 20,
  "tasks": [
    {
      "task_id": "pub_20250826_a1b2c3d4",
      "video_id": "test_0DmxeSNvtsM",
      "platform": "douyin",
      "account_id": "douyin_account_001",
      "status": "scheduled",
      "scheduled_time": "2025-08-27T14:30:00",
      "created_at": "2025-08-26T20:00:00",
      "title": "定时发布测试"
    },
    {
      "task_id": "pub_20250826_e5f6g7h8",
      "video_id": "test_ABC123",
      "platform": "kuaishou",
      "account_id": "kuaishou_account_002",
      "status": "completed",
      "scheduled_time": "2025-08-26T10:00:00",
      "executed_at": "2025-08-26T10:00:15",
      "created_at": "2025-08-25T20:00:00",
      "title": "已完成的发布任务"
    }
  ]
}
```

### 3. 查询单个任务详情

获取指定发布任务的详细信息。

**接口路径**: `GET /api/publish/task/{task_id}`

**路径参数**:
- `task_id`: 任务ID

**请求示例**:
```
GET /api/publish/task/pub_20250826_a1b2c3d4
```

**响应示例**:

成功完成的任务：
```json
{
  "task_id": "pub_20250826_a1b2c3d4",
  "video_id": "test_0DmxeSNvtsM",
  "platform": "douyin",
  "account_id": "douyin_account_001",
  "status": "completed",
  "scheduled_time": "2025-08-27T14:30:00",
  "executed_at": "2025-08-27T14:30:05",
  "created_at": "2025-08-26T20:00:00",
  "title": "定时发布测试",
  "description": "这是一个定时发布的测试视频",
  "tags": ["定时", "测试"],
  "video_path": "/outputs/test/video_20250826.mp4",
  "cover_path": "/outputs/test/cover_20250826.jpg",
  "retry_count": 0,
  "result": {
    "platform_video_id": "7401234567890",
    "url": "https://www.douyin.com/video/7401234567890",
    "message": "发布成功"
  }
}
```

失败的任务：
```json
{
  "task_id": "pub_20250826_i9j0k1l2",
  "video_id": "test_XYZ789",
  "platform": "douyin",
  "account_id": "douyin_account_003",
  "status": "failed",
  "scheduled_time": "2025-08-27T10:00:00",
  "executed_at": "2025-08-27T10:00:10",
  "created_at": "2025-08-26T18:00:00",
  "title": "失败的发布任务",
  "retry_count": 3,
  "error_message": "账号登录失败，请检查账号状态"
}
```

### 4. 取消发布任务

取消一个尚未执行的发布任务。

**接口路径**: `DELETE /api/publish/task/{task_id}`

**路径参数**:
- `task_id`: 任务ID

**请求示例**:
```
DELETE /api/publish/task/pub_20250826_a1b2c3d4
```

**响应示例**:

成功响应：
```json
{
  "message": "任务已取消",
  "task_id": "pub_20250826_a1b2c3d4"
}
```

错误响应：
```json
{
  "error": "任务已执行，无法取消",
  "task_id": "pub_20250826_a1b2c3d4",
  "status": "completed"
}
```

### 5. 修改定时时间

修改一个尚未执行的任务的定时时间。

**接口路径**: `PUT /api/publish/task/{task_id}/reschedule`

**路径参数**:
- `task_id`: 任务ID

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| scheduled_time | string | 是 | 新的发布时间，ISO 8601格式 |

**请求示例**:
```json
{
  "scheduled_time": "2025-08-28T16:00:00"
}
```

**响应示例**:
```json
{
  "task_id": "pub_20250826_a1b2c3d4",
  "old_time": "2025-08-27T14:30:00",
  "new_time": "2025-08-28T16:00:00",
  "message": "发布时间已更新"
}
```

## 前端集成指南

### 1. 接口调用示例（TypeScript）

```typescript
// 定义接口类型
interface PublishRequest {
  video_id: string;
  platform: 'douyin' | 'kuaishou' | 'xiaohongshu';
  account_id: string;
  scheduled_time?: string;  // ISO 8601格式
  title: string;
  description?: string;
  tags?: string[];
  video_path: string;
  cover_path?: string;
}

interface PublishTask {
  task_id: string;
  status: 'scheduled' | 'processing' | 'completed' | 'failed' | 'cancelled';
  scheduled_time?: string;
  executed_at?: string;
  created_at: string;
  title: string;
  platform: string;
  account_id: string;
  error_message?: string;
  result?: {
    platform_video_id: string;
    url: string;
  };
}

// API服务类
class PublishService {
  private baseUrl = 'http://localhost:51082/api';

  // 创建发布任务
  async schedulePublish(data: PublishRequest): Promise<PublishTask> {
    const response = await fetch(`${this.baseUrl}/publish/schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }

  // 获取任务列表
  async getTasks(params?: {
    status?: string;
    platform?: string;
    page?: number;
    limit?: number;
  }): Promise<{ total: number; tasks: PublishTask[] }> {
    const query = new URLSearchParams(params as any);
    const response = await fetch(`${this.baseUrl}/publish/tasks?${query}`);
    return response.json();
  }

  // 获取任务详情
  async getTask(taskId: string): Promise<PublishTask> {
    const response = await fetch(`${this.baseUrl}/publish/task/${taskId}`);
    return response.json();
  }

  // 取消任务
  async cancelTask(taskId: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/publish/task/${taskId}`, {
      method: 'DELETE'
    });
    return response.json();
  }

  // 重新安排时间
  async rescheduleTask(taskId: string, newTime: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/publish/task/${taskId}/reschedule`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scheduled_time: newTime })
    });
    return response.json();
  }
}
```

### 2. React组件使用示例

```jsx
import React, { useState, useEffect } from 'react';
import { DatePicker, Button, Table, Tag, message } from 'antd';
import dayjs from 'dayjs';

const PublishManager = ({ videoId, videoPath, title }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const publishService = new PublishService();

  // 创建发布任务
  const handlePublish = async (scheduledTime) => {
    try {
      setLoading(true);
      const task = await publishService.schedulePublish({
        video_id: videoId,
        platform: 'douyin',
        account_id: 'douyin_account_001',
        scheduled_time: scheduledTime?.toISOString(),
        title: title,
        video_path: videoPath
      });
      
      message.success(
        scheduledTime 
          ? `已安排在 ${scheduledTime.format('YYYY-MM-DD HH:mm')} 发布`
          : '正在发布...'
      );
      
      // 刷新任务列表
      await loadTasks();
      
      // 如果是立即发布，轮询状态
      if (!scheduledTime) {
        pollTaskStatus(task.task_id);
      }
    } catch (error) {
      message.error('创建发布任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 轮询任务状态
  const pollTaskStatus = (taskId) => {
    const interval = setInterval(async () => {
      try {
        const task = await publishService.getTask(taskId);
        if (task.status === 'completed') {
          clearInterval(interval);
          message.success('发布成功！');
          await loadTasks();
        } else if (task.status === 'failed') {
          clearInterval(interval);
          message.error(`发布失败：${task.error_message}`);
          await loadTasks();
        }
      } catch (error) {
        clearInterval(interval);
      }
    }, 3000);  // 每3秒查询一次
  };

  // 加载任务列表
  const loadTasks = async () => {
    try {
      const response = await publishService.getTasks({
        page: 1,
        limit: 20
      });
      setTasks(response.tasks);
    } catch (error) {
      message.error('加载任务列表失败');
    }
  };

  // 取消任务
  const handleCancel = async (taskId) => {
    try {
      await publishService.cancelTask(taskId);
      message.success('任务已取消');
      await loadTasks();
    } catch (error) {
      message.error('取消任务失败');
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  return (
    <div>
      {/* 发布控制 */}
      <div style={{ marginBottom: 24 }}>
        <Button 
          type="primary" 
          onClick={() => handlePublish()}
          loading={loading}
        >
          立即发布
        </Button>
        
        <DatePicker
          showTime
          placeholder="选择发布时间"
          disabledDate={(current) => current && current < dayjs().startOf('day')}
          onChange={(date) => date && handlePublish(date)}
          style={{ marginLeft: 16 }}
        />
      </div>

      {/* 任务列表 */}
      <Table
        dataSource={tasks}
        rowKey="task_id"
        columns={[
          {
            title: '任务ID',
            dataIndex: 'task_id',
            width: 200
          },
          {
            title: '平台',
            dataIndex: 'platform',
            width: 100
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 120,
            render: (status) => {
              const colors = {
                scheduled: 'blue',
                processing: 'orange',
                completed: 'green',
                failed: 'red',
                cancelled: 'gray'
              };
              return <Tag color={colors[status]}>{status}</Tag>;
            }
          },
          {
            title: '计划时间',
            dataIndex: 'scheduled_time',
            width: 200,
            render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
          },
          {
            title: '操作',
            key: 'actions',
            width: 150,
            render: (_, record) => (
              <>
                {record.status === 'scheduled' && (
                  <Button 
                    size="small" 
                    danger
                    onClick={() => handleCancel(record.task_id)}
                  >
                    取消
                  </Button>
                )}
                {record.status === 'completed' && record.result?.url && (
                  <a href={record.result.url} target="_blank">
                    查看
                  </a>
                )}
              </>
            )
          }
        ]}
      />
    </div>
  );
};
```

### 3. 状态管理（使用Redux）

```javascript
// actions/publish.js
export const publishActions = {
  SCHEDULE_PUBLISH: 'SCHEDULE_PUBLISH',
  SCHEDULE_PUBLISH_SUCCESS: 'SCHEDULE_PUBLISH_SUCCESS',
  SCHEDULE_PUBLISH_FAILURE: 'SCHEDULE_PUBLISH_FAILURE',
  LOAD_TASKS: 'LOAD_TASKS',
  LOAD_TASKS_SUCCESS: 'LOAD_TASKS_SUCCESS',
  CANCEL_TASK: 'CANCEL_TASK',
  UPDATE_TASK_STATUS: 'UPDATE_TASK_STATUS'
};

// 创建发布任务
export const schedulePublish = (data) => async (dispatch) => {
  dispatch({ type: publishActions.SCHEDULE_PUBLISH });
  
  try {
    const response = await fetch('/api/publish/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const task = await response.json();
    
    dispatch({
      type: publishActions.SCHEDULE_PUBLISH_SUCCESS,
      payload: task
    });
    
    return task;
  } catch (error) {
    dispatch({
      type: publishActions.SCHEDULE_PUBLISH_FAILURE,
      payload: error.message
    });
    throw error;
  }
};

// reducer/publish.js
const initialState = {
  tasks: [],
  loading: false,
  error: null,
  currentTask: null
};

export const publishReducer = (state = initialState, action) => {
  switch (action.type) {
    case publishActions.SCHEDULE_PUBLISH:
      return { ...state, loading: true, error: null };
      
    case publishActions.SCHEDULE_PUBLISH_SUCCESS:
      return {
        ...state,
        loading: false,
        tasks: [action.payload, ...state.tasks],
        currentTask: action.payload
      };
      
    case publishActions.SCHEDULE_PUBLISH_FAILURE:
      return { ...state, loading: false, error: action.payload };
      
    case publishActions.LOAD_TASKS_SUCCESS:
      return { ...state, tasks: action.payload };
      
    case publishActions.UPDATE_TASK_STATUS:
      return {
        ...state,
        tasks: state.tasks.map(task =>
          task.task_id === action.payload.task_id
            ? { ...task, ...action.payload }
            : task
        )
      };
      
    default:
      return state;
  }
};
```

## 注意事项

### 1. 时间处理
- 所有时间使用ISO 8601格式（`YYYY-MM-DDTHH:mm:ss`）
- 前端需要处理时区转换
- 建议使用dayjs或moment.js处理时间

### 2. 错误处理
- 所有接口调用都应该包含错误处理
- 显示友好的错误提示给用户
- 记录错误日志便于调试

### 3. 状态同步
- 定时任务创建后，前端可以选择轮询状态或使用WebSocket接收更新
- 建议对正在执行的任务进行轮询（3-5秒间隔）
- 已完成或失败的任务不需要继续轮询

### 4. 权限控制
- 只能取消自己创建的任务
- 只能查看有权限的账号的任务
- 后续会添加认证机制

### 5. 性能优化
- 任务列表使用分页加载
- 避免频繁刷新整个列表
- 使用状态缓存减少API调用

## 迁移计划

### 第一阶段（兼容阶段）
1. 新增定时发布接口，不影响现有立即发布功能
2. 前端新增定时发布UI组件
3. 两种发布方式并存

### 第二阶段（过渡阶段）
1. 前端统一使用新接口
2. 立即发布也通过新接口（不传scheduled_time）
3. 保留旧接口但标记为deprecated

### 第三阶段（完成阶段）
1. 移除旧接口
2. 所有发布统一通过任务队列
3. 完善任务管理功能

## 常见问题

**Q: 立即发布和定时发布有什么区别？**
A: 立即发布不传scheduled_time或传过去的时间，定时发布传未来的时间。

**Q: 任务状态多久更新一次？**
A: 后端实时更新，前端建议3-5秒轮询一次。

**Q: 可以同时发布到多个平台吗？**
A: 目前需要为每个平台创建独立的任务，后续会支持批量发布。

**Q: 定时任务的精度如何？**
A: 精度在1分钟内，实际执行时间可能有几秒延迟。

**Q: 服务器重启后定时任务会丢失吗？**
A: 不会，所有任务都持久化存储在数据库中。

## 联系方式

如有问题，请联系后端开发团队。