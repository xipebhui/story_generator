# 定时发布API使用说明

## 概述

定时发布功能已经完全集成到主服务（api_with_db.py）中，使用同一个端口（51082）和数据库。支持立即发布和定时发布两种模式。

## 核心功能

1. **立即发布**：创建任务后立即上传到YouTube
2. **定时发布**：设置未来的发布时间，系统会自动在指定时间执行发布
3. **持久化存储**：所有定时任务保存在数据库中，服务重启后自动恢复
4. **队列管理**：使用小顶堆实现高效的任务调度

## API接口说明

### 1. 创建定时发布任务

**接口地址**: `POST /api/publish/schedule`

**功能说明**: 支持立即发布和定时发布，是推荐使用的主要发布接口

**请求参数**:
```json
{
  "task_id": "creator_001_video_001_abc123",  // Pipeline任务ID（必填）
  "account_ids": ["account_001", "account_002"],  // 发布账号ID列表（必填）
  "video_title": "视频标题（可选）",
  "video_description": "视频描述（可选）",
  "video_tags": ["tag1", "tag2"],  // 标签列表（可选）
  "thumbnail_path": "/path/to/thumbnail.jpg",  // 封面图路径（可选）
  "scheduled_time": "2024-12-25T10:00:00",  // 定时发布时间（可选，ISO格式）
  "privacy_status": "public"  // 隐私设置: public/private/unlisted
}
```

**响应示例**:
```json
{
  "message": "创建了 2 个发布任务（0个立即发布，2个定时发布）",
  "results": [
    {
      "publish_id": "pub_creator_001_video_001_abc123_account_001_xyz789",
      "account_id": "account_001",
      "status": "scheduled",
      "scheduled_time": "2024-12-25T10:00:00",
      "message": "已安排在 2024-12-25T10:00:00 发布"
    },
    {
      "publish_id": "pub_creator_001_video_001_abc123_account_002_xyz790",
      "account_id": "account_002",
      "status": "scheduled",
      "scheduled_time": "2024-12-25T10:00:00",
      "message": "已安排在 2024-12-25T10:00:00 发布"
    }
  ],
  "summary": {
    "total": 2,
    "immediate": 0,
    "scheduled": 2,
    "failed": 0
  }
}
```

### 2. 查看定时发布队列

**接口地址**: `GET /api/publish/scheduler/queue`

**功能说明**: 查看当前定时发布队列的状态

**响应示例**:
```json
{
  "total": 5,
  "next_task": ["2024-12-25T10:00:00", "pub_xxx_001"],
  "tasks": [
    {
      "scheduled_time": "2024-12-25T10:00:00",
      "publish_id": "pub_xxx_001"
    },
    {
      "scheduled_time": "2024-12-25T12:00:00",
      "publish_id": "pub_xxx_002"
    }
  ]
}
```

### 3. 取消定时发布

**接口地址**: `DELETE /api/publish/scheduler/{publish_id}`

**功能说明**: 取消一个定时发布任务

**响应示例**:
```json
{
  "message": "定时发布任务已取消",
  "publish_id": "pub_xxx_001"
}
```

### 4. 重新安排发布时间

**接口地址**: `POST /api/publish/scheduler/reschedule/{publish_id}`

**功能说明**: 修改已存在的定时发布任务的发布时间

**请求参数**:
```json
{
  "new_time": "2024-12-26T14:00:00"
}
```

**响应示例**:
```json
{
  "message": "发布时间已更新为 2024-12-26T14:00:00",
  "publish_id": "pub_xxx_001",
  "new_scheduled_time": "2024-12-26T14:00:00"
}
```

### 5. 查询发布历史

**接口地址**: `GET /api/publish/history`

**功能说明**: 查询发布历史记录

**请求参数**:
- `task_id`: Pipeline任务ID（可选）
- `account_id`: 账号ID（可选）
- `status`: 状态筛选（可选）: pending/uploading/success/failed
- `limit`: 返回数量限制（默认100）

**响应示例**:
```json
{
  "total": 25,
  "publish_tasks": [
    {
      "publish_id": "pub_xxx_001",
      "task_id": "creator_001_video_001",
      "account_id": "account_001",
      "status": "success",
      "youtube_video_url": "https://youtube.com/watch?v=xxx",
      "scheduled_time": "2024-12-25T10:00:00",
      "created_at": "2024-12-24T10:00:00"
    }
  ]
}
```

## 使用流程

### 场景1：立即发布

```bash
# 不设置scheduled_time或设置为过去的时间，任务会立即执行
curl -X POST http://localhost:51082/api/publish/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "creator_001_video_001_abc123",
    "account_ids": ["account_001"],
    "video_title": "立即发布的视频"
  }'
```

### 场景2：定时发布

```bash
# 设置future的scheduled_time，任务会在指定时间执行
curl -X POST http://localhost:51082/api/publish/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "creator_001_video_001_abc123",
    "account_ids": ["account_001", "account_002"],
    "scheduled_time": "2024-12-25T10:00:00",
    "video_title": "圣诞节特别视频"
  }'
```

### 场景3：查看队列状态

```bash
curl -X GET http://localhost:51082/api/publish/scheduler/queue
```

### 场景4：取消定时任务

```bash
curl -X DELETE http://localhost:51082/api/publish/scheduler/pub_xxx_001
```

## 技术实现

1. **调度器架构**：
   - 使用Python的heapq实现小顶堆，保证O(log n)的插入和删除效率
   - 后台线程每30秒检查一次是否有任务需要执行
   - 任务执行时间精度在30秒以内

2. **数据持久化**：
   - 所有定时任务信息保存在PublishTask表中
   - scheduled_time字段记录计划发布时间
   - is_scheduled字段标识是否为定时任务
   - 服务启动时自动从数据库加载未执行的定时任务

3. **容错机制**：
   - 服务重启后自动恢复定时任务
   - 任务执行失败后记录错误信息，可通过retry接口重试
   - 使用事务保证数据一致性

## 注意事项

1. **时间格式**：scheduled_time必须使用ISO 8601格式（YYYY-MM-DDTHH:MM:SS）
2. **时区处理**：建议使用UTC时间或明确指定时区
3. **调度精度**：任务执行时间精度为30秒，实际执行时间可能有±30秒的偏差
4. **任务数量**：系统可以处理数千个定时任务，但建议合理安排避免同一时间大量任务
5. **重启恢复**：服务重启后会自动恢复所有未执行的定时任务

## 与前端对接

前端可以通过以下方式使用定时发布功能：

1. **发布界面**：
   - 添加"发布时间"选择器（日期+时间）
   - 立即发布：不设置时间或选择"立即"
   - 定时发布：选择未来的时间

2. **状态显示**：
   - pending：待发布（定时任务）
   - uploading：上传中
   - success：发布成功
   - failed：发布失败
   - cancelled：已取消

3. **管理界面**：
   - 显示定时发布队列
   - 支持取消和重新安排
   - 查看发布历史

## 兼容性说明

- 原有的`/api/publish/create`接口保持兼容，也支持定时发布功能
- 建议新的前端实现使用`/api/publish/schedule`接口
- 所有发布任务都保存在同一个数据库中，可以统一查询和管理