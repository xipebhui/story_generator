# 视频创作Pipeline API完整文档

## 服务信息

- **服务地址**: `http://localhost:51082`
- **API文档**: `http://localhost:51082/docs`
- **服务版本**: v0.2.0
- **数据库**: SQLite (./data/pipeline_tasks.db)

## 核心功能

1. **视频制作Pipeline**: 从YouTube视频生成故事、语音、剪映草稿和导出视频
2. **账号管理**: 支持多账号管理和发布
3. **定时发布**: 支持立即发布和定时发布到YouTube
4. **任务管理**: 任务历史、状态查询、失败重试

---

## 1. Pipeline任务管理

### 1.1 创建Pipeline任务

**接口**: `POST /api/pipeline/run`

**功能**: 创建视频制作任务，支持账号绑定

**请求参数**:
```json
{
  "video_id": "YouTube视频ID",           // 必填
  "creator_id": "创作者ID",              // 必填
  "account_name": "发布账号名称",         // 可选，会绑定到文件名
  "gender": 1,                           // 语音性别: 0=男性, 1=女性
  "duration": 60,                        // 每张图片持续时间(秒)
  "image_dir": "图库目录路径",           // 可选
  "export_video": false,                 // 是否导出视频
  "enable_subtitle": true                // 是否启用字幕（默认true）
}
```

**响应示例**:
```json
{
  "task_id": "creator_001_my_channel_video_001_abc123",
  "message": "任务已启动",
  "status_url": "/api/pipeline/status/creator_001_my_channel_video_001_abc123",
  "result_url": "/api/pipeline/result/creator_001_my_channel_video_001_abc123"
}
```

**任务ID格式说明**:
- 有账号名: `{creator_id}_{account_name}_{video_id}_{uuid}`
- 无账号名: `{creator_id}_{video_id}_{uuid}`

### 1.2 查询任务状态

**接口**: `GET /api/pipeline/status/{task_id}`

**功能**: 获取任务当前执行状态

**响应示例**:
```json
{
  "task_id": "creator_001_my_channel_video_001_abc123",
  "status": "running",  // pending/running/completed/failed
  "current_stage": "语音生成",
  "progress": {
    "故事二创": "成功",
    "语音生成": "运行中",
    "剪映草稿生成": "待处理",
    "视频导出": "待处理"
  },
  "created_at": "2024-12-01T10:00:00",
  "started_at": "2024-12-01T10:00:05",
  "completed_at": null,
  "total_duration": null
}
```

### 1.3 获取任务结果

**接口**: `GET /api/pipeline/result/{task_id}`

**功能**: 获取已完成任务的结果文件

**响应示例**:
```json
{
  "task_id": "creator_001_my_channel_video_001_abc123",
  "status": "completed",
  "youtube_metadata": {
    "title": "视频标题",
    "description": "视频描述",
    "tags": ["标签1", "标签2"],
    "duration": 300
  },
  "video_path": "/path/to/video.mp4",          // 本地视频路径
  "preview_url": "http://fileserver/preview.mp4", // 30秒预览视频URL
  "draft_path": "/path/to/draft",              // 剪映草稿路径
  "audio_path": "/path/to/audio.mp3",          // 音频文件路径
  "story_path": "/path/to/story.txt",          // 故事文本路径
  "thumbnail_path": null,
  "error": null,
  "publish_tasks": []  // 关联的发布任务
}
```

### 1.4 重试失败任务

**接口**: `POST /api/pipeline/retry/{task_id}`

**功能**: 为失败的任务创建新任务并重新执行

**响应示例**:
```json
{
  "task_id": "creator_001_my_channel_video_001_def456",
  "message": "重试任务已创建（原任务: creator_001_my_channel_video_001_abc123）",
  "status_url": "/api/pipeline/status/creator_001_my_channel_video_001_def456",
  "result_url": "/api/pipeline/result/creator_001_my_channel_video_001_def456",
  "original_task_id": "creator_001_my_channel_video_001_abc123"
}
```

### 1.5 查询任务历史

**接口**: `GET /api/pipeline/history`

**功能**: 查询历史任务记录

**请求参数**:
- `creator_id`: 创作者ID（可选）
- `status`: 状态筛选（可选）: pending/running/completed/failed
- `start_date`: 开始日期（可选，ISO格式）
- `end_date`: 结束日期（可选，ISO格式）
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）

**响应示例**:
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "tasks": [
    {
      "id": 1,
      "task_id": "creator_001_my_channel_video_001_abc123",
      "video_id": "video_001",
      "creator_id": "creator_001",
      "account_name": "my_channel",
      "status": "completed",
      "created_at": "2024-12-01T10:00:00",
      "completed_at": "2024-12-01T10:05:00",
      "total_duration": 300.5
    }
  ]
}
```

### 1.6 获取统计信息

**接口**: `GET /api/pipeline/statistics`

**功能**: 获取任务统计数据

**请求参数**:
- `creator_id`: 创作者ID（可选）

**响应示例**:
```json
{
  "pipeline": {
    "total": 500,
    "completed": 450,
    "failed": 30,
    "running": 5,
    "success_rate": 90.0
  },
  "publish": {
    "total": 200,
    "success": 190,
    "failed": 10,
    "success_rate": 95.0
  },
  "avg_duration_seconds": 285.5
}
```

---

## 2. 发布管理

### 2.1 创建定时发布任务（推荐）

**接口**: `POST /api/publish/schedule`

**功能**: 创建发布任务，支持立即发布和定时发布

**请求参数**:
```json
{
  "task_id": "Pipeline任务ID",                    // 必填
  "account_ids": ["account_001", "account_002"],  // 账号ID列表，必填
  "video_title": "自定义视频标题",                 // 可选
  "video_description": "自定义视频描述",           // 可选
  "video_tags": ["tag1", "tag2"],                // 可选
  "thumbnail_path": "/path/to/thumbnail.jpg",     // 可选
  "scheduled_time": "2024-12-25T10:00:00",       // 可选，定时发布时间
  "privacy_status": "public"                      // public/private/unlisted
}
```

**响应示例**:
```json
{
  "message": "创建了 2 个发布任务（0个立即发布，2个定时发布）",
  "results": [
    {
      "publish_id": "pub_task_001_account_001_xyz",
      "account_id": "account_001",
      "status": "scheduled",
      "scheduled_time": "2024-12-25T10:00:00",
      "message": "已安排在 2024-12-25T10:00:00 发布"
    },
    {
      "publish_id": "pub_task_001_account_002_abc",
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

**发布逻辑**:
- 如果不设置 `scheduled_time` 或设置为过去时间：立即发布
- 如果设置未来的 `scheduled_time`：定时发布
- 服务重启后会自动恢复未执行的定时任务

### 2.2 查看定时发布队列

**接口**: `GET /api/publish/scheduler/queue`

**功能**: 查看当前定时发布队列状态

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

### 2.3 取消定时发布

**接口**: `DELETE /api/publish/scheduler/{publish_id}`

**功能**: 取消一个定时发布任务

**响应示例**:
```json
{
  "message": "定时发布任务已取消",
  "publish_id": "pub_xxx_001"
}
```

### 2.4 重新安排发布时间

**接口**: `POST /api/publish/scheduler/reschedule/{publish_id}`

**功能**: 修改定时发布任务的发布时间

**请求体**:
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

### 2.5 查询发布历史

**接口**: `GET /api/publish/history`

**功能**: 查询发布历史记录

**请求参数**:
- `task_id`: Pipeline任务ID（可选）
- `account_id`: 账号ID（可选）
- `status`: 状态筛选（可选）: pending/uploading/success/failed
- `limit`: 返回数量限制（默认100，最大500）

**响应示例**:
```json
{
  "total": 25,
  "publish_tasks": [
    {
      "publish_id": "pub_xxx_001",
      "task_id": "creator_001_video_001_abc123",
      "account_id": "account_001",
      "video_title": "视频标题",
      "status": "success",
      "youtube_video_id": "YouTube视频ID",
      "youtube_video_url": "https://youtube.com/watch?v=xxx",
      "scheduled_time": "2024-12-25T10:00:00",
      "is_scheduled": true,
      "created_at": "2024-12-24T10:00:00",
      "upload_completed_at": "2024-12-25T10:01:00"
    }
  ]
}
```

### 2.6 重试失败的发布

**接口**: `POST /api/publish/retry/{publish_id}`

**功能**: 重试失败的发布任务

**响应示例**:
```json
{
  "message": "重试任务已启动",
  "publish_id": "pub_xxx_001"
}
```

---

## 3. 账号管理

### 3.1 获取所有账号

**接口**: `GET /api/accounts`

**功能**: 获取所有可用账号

**请求参数**:
- `active_only`: 是否只返回激活账号（默认true）

**响应示例**:
```json
{
  "total": 5,
  "accounts": [
    {
      "account_id": "account_001",
      "account_name": "我的频道1",
      "profile_id": "BitBrowser_Profile_ID",
      "channel_url": "https://youtube.com/@channel1",
      "window_number": "01",
      "description": "主账号",
      "is_active": true,
      "created_at": "2024-12-01T10:00:00"
    }
  ]
}
```

### 3.2 获取账号详情

**接口**: `GET /api/accounts/{account_id}`

**功能**: 获取单个账号信息

**响应示例**:
```json
{
  "account_id": "account_001",
  "account_name": "我的频道1",
  "profile_id": "BitBrowser_Profile_ID",
  "channel_url": "https://youtube.com/@channel1",
  "window_number": "01",
  "description": "主账号",
  "is_active": true,
  "created_at": "2024-12-01T10:00:00",
  "updated_at": "2024-12-01T10:00:00"
}
```

### 3.3 获取账号统计

**接口**: `GET /api/accounts/{account_id}/statistics`

**功能**: 获取账号发布统计信息

**响应示例**:
```json
{
  "account_id": "account_001",
  "total_published": 100,
  "success_count": 95,
  "failed_count": 5,
  "success_rate": 95.0,
  "last_publish_time": "2024-12-01T10:00:00"
}
```

### 3.4 更新账号状态

**接口**: `PUT /api/accounts/{account_id}/status`

**功能**: 激活或禁用账号

**请求参数**:
- `is_active`: true=激活, false=禁用

**响应示例**:
```json
{
  "message": "账号状态已更新为激活"
}
```

---

## 4. 使用示例

### 场景1：创建视频并立即发布

```bash
# 步骤1：创建Pipeline任务
curl -X POST http://localhost:51082/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123",
    "creator_id": "user001",
    "account_name": "my_channel",
    "gender": 1,
    "duration": 60,
    "export_video": true,
    "enable_subtitle": true
  }'

# 步骤2：等待任务完成，查询状态
curl http://localhost:51082/api/pipeline/status/{task_id}

# 步骤3：任务完成后，立即发布到YouTube
curl -X POST http://localhost:51082/api/publish/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "{task_id}",
    "account_ids": ["account_001"],
    "video_title": "我的视频"
  }'
```

### 场景2：批量定时发布

```bash
# 创建定时发布任务（圣诞节上午10点发布）
curl -X POST http://localhost:51082/api/publish/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "{task_id}",
    "account_ids": ["account_001", "account_002", "account_003"],
    "video_title": "圣诞特别节目",
    "video_tags": ["圣诞", "特别节目"],
    "scheduled_time": "2024-12-25T10:00:00",
    "privacy_status": "public"
  }'
```

### 场景3：重试失败的任务

```bash
# 重试Pipeline任务
curl -X POST http://localhost:51082/api/pipeline/retry/{failed_task_id}

# 重试发布任务
curl -X POST http://localhost:51082/api/publish/retry/{failed_publish_id}
```

### 场景4：查看和管理定时队列

```bash
# 查看队列
curl http://localhost:51082/api/publish/scheduler/queue

# 取消定时任务
curl -X DELETE http://localhost:51082/api/publish/scheduler/{publish_id}

# 修改发布时间
curl -X POST http://localhost:51082/api/publish/scheduler/reschedule/{publish_id} \
  -H "Content-Type: application/json" \
  -d '{"new_time": "2024-12-26T14:00:00"}'
```

---

## 5. 文件路径说明

当提供 `account_name` 参数时，生成的文件路径会包含账号名：

- **输出目录**: `outputs/{creator_id}/{account_name}/{video_id}/`
- **日志文件**: `logs/pipeline_{creator_id}_{account_name}_{video_id}_{timestamp}.log`
- **视频文件**: `{creator_id}_{account_name}_{video_id}_{timestamp}.mp4`
- **预览文件**: `{creator_id}_{account_name}_{video_id}_{timestamp}_preview.mp4`

不提供 `account_name` 时：
- **输出目录**: `outputs/{creator_id}/{video_id}/`
- **视频文件**: `{creator_id}_{video_id}_{timestamp}.mp4`

---

## 6. 状态码说明

### 任务状态 (status)
- `pending`: 待处理
- `running`: 运行中
- `completed`: 已完成
- `failed`: 失败

### 发布状态 (publish status)
- `pending`: 待发布
- `uploading`: 上传中
- `success`: 发布成功
- `failed`: 发布失败
- `cancelled`: 已取消
- `scheduled`: 已安排（定时任务）

### 隐私设置 (privacy_status)
- `public`: 公开
- `private`: 私密
- `unlisted`: 不公开

---

## 7. 错误处理

### 常见错误码

| 状态码 | 说明 | 处理方式 |
|-------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式 |
| 404 | 任务或资源不存在 | 检查ID是否正确 |
| 500 | 服务器内部错误 | 查看服务器日志 |

### 错误响应格式

```json
{
  "detail": "错误详细信息"
}
```

---

## 8. 注意事项

1. **账号绑定**: 使用 `account_name` 参数可以将任务与特定发布账号绑定，便于管理和追踪
2. **定时精度**: 定时发布的执行精度为30秒，实际执行时间可能有±30秒偏差
3. **时间格式**: 所有时间使用ISO 8601格式（YYYY-MM-DDTHH:MM:SS）
4. **任务依赖**: 发布任务必须等Pipeline任务完成后才能创建
5. **批量限制**: 单次批量发布建议不超过10个账号
6. **重试策略**: 失败任务会生成新的任务ID，原任务保持不变
7. **数据持久化**: 所有任务信息保存在数据库中，服务重启不会丢失

---

## 9. 前端集成建议

### 任务创建流程
1. 用户选择YouTube视频和账号
2. 调用 `/api/pipeline/run` 创建任务
3. 轮询 `/api/pipeline/status/{task_id}` 查看进度
4. 任务完成后显示结果

### 发布流程
1. 选择已完成的任务
2. 选择发布账号（可多选）
3. 设置发布时间（立即或定时）
4. 调用 `/api/publish/schedule` 创建发布任务
5. 显示发布状态

### 状态显示建议
- 使用进度条显示Pipeline各阶段进度
- 使用不同颜色标识任务状态
- 定时任务显示倒计时
- 失败任务提供重试按钮

### 实时更新
- 建议每5-10秒轮询一次状态接口
- 使用WebSocket实现实时通知（如需要可后续添加）

---

## 10. 环境变量配置

服务使用以下环境变量（在 `.env` 文件中配置）：

```bash
# 日志级别
LOG_LEVEL=INFO

# 数据库路径
DB_PATH=./data/pipeline_tasks.db

# YouTube上传服务
YTENGINE_HOST=http://localhost:51077
USE_MOCK_UPLOAD=true  # 测试环境使用mock接口

# 文件服务器
FILE_SERVER_BASE=http://localhost:50012

# 草稿目录
DRAFT_LOCAL_DIR=/Users/xxx/JianyingPro/Drafts
```

---

## 联系支持

如有问题或需要帮助，请联系开发团队。

**版本**: v0.2.0  
**更新日期**: 2024-12-01  
**作者**: Pipeline开发团队