# Video Pipeline API 完整接口文档

> 版本：0.2.0  
> 基础URL：http://localhost:51082  
> 文档生成时间：2024-01-26

## 目录

- [概述](#概述)
- [通用说明](#通用说明)
- [数据模型](#数据模型)
- [API接口列表](#api接口列表)
  - [Pipeline管理接口](#1-pipeline管理接口)
  - [发布管理接口](#2-发布管理接口)
  - [账号管理接口](#3-账号管理接口)
  - [系统接口](#4-系统接口)
- [错误码说明](#错误码说明)
- [使用示例](#使用示例)

---

## 概述

Video Pipeline API 是一个用于管理视频制作和发布流程的RESTful API服务。主要功能包括：

- **Pipeline管理**：创建和管理视频制作任务
- **发布管理**：将制作完成的视频发布到多个YouTube账号
- **账号管理**：管理YouTube发布账号
- **任务历史**：查询历史任务记录和统计信息

### 技术栈
- FastAPI (Web框架)
- SQLAlchemy (ORM)
- SQLite/MySQL (数据库)
- 异步任务处理

---

## 通用说明

### 请求格式
- Content-Type: `application/json`
- 编码: UTF-8

### 响应格式
- Content-Type: `application/json`
- 成功响应: HTTP 200/201
- 错误响应: HTTP 4xx/5xx

### 认证
当前版本无需认证（后续可添加）

### 分页参数
- `page`: 页码，从1开始
- `page_size`: 每页数量，默认20，最大100

---

## 数据模型

### PipelineRequest (Pipeline请求)
```json
{
  "video_id": "string",           // YouTube视频ID (必填)
  "creator_id": "string",         // 创作者ID (必填)
  "gender": 0,                    // 语音性别: 0=男性, 1=女性 (默认1)
  "duration": 60,                 // 每张图片持续时间(秒) (默认60)
  "image_dir": "string",          // 图片目录路径 (可选)
  "export_video": false,          // 是否导出视频 (默认false)
  "enable_subtitle": true         // 是否启用字幕 (默认true)
}
```

### TaskStatus (任务状态)
```json
{
  "task_id": "string",            // 任务ID
  "status": "string",             // 状态: pending/running/completed/failed
  "current_stage": "string",      // 当前阶段
  "progress": {                   // 各阶段进度
    "故事二创": "成功",
    "语音生成": "运行中",
    "剪映草稿生成": "待处理"
  },
  "created_at": "2024-01-26T10:00:00",      // 创建时间
  "started_at": "2024-01-26T10:01:00",      // 开始时间
  "completed_at": "2024-01-26T10:05:00",    // 完成时间
  "total_duration": 240.5                    // 总耗时(秒)
}
```

### TaskResult (任务结果)
```json
{
  "task_id": "string",
  "status": "string",
  "youtube_metadata": {           // YouTube元数据
    "title": "string",
    "description": "string",
    "tags": ["tag1", "tag2"]
  },
  "video_path": "string",         // 视频文件路径
  "preview_url": "string",        // 预览URL
  "draft_path": "string",         // 剪映草稿路径
  "audio_path": "string",         // 音频路径
  "story_path": "string",         // 故事文本路径
  "thumbnail_path": "string",     // 缩略图路径
  "error": "string",              // 错误信息
  "publish_tasks": []             // 发布任务列表
}
```

### PublishRequest (发布请求)
```json
{
  "task_id": "string",                      // Pipeline任务ID (必填)
  "account_ids": ["acc1", "acc2"],         // 账号ID列表 (必填)
  "video_title": "string",                  // 视频标题 (可选)
  "video_description": "string",            // 视频描述 (可选)
  "video_tags": ["tag1", "tag2"],          // 标签列表 (可选)
  "thumbnail_path": "string",               // 封面图路径 (可选)
  "scheduled_time": "2024-01-26T18:00:00", // 定时发布时间 (可选)
  "privacy_status": "public"                // 隐私设置: public/private/unlisted
}
```

### Account (账号信息)
```json
{
  "id": 1,
  "account_id": "string",         // 账号唯一ID
  "account_name": "string",       // 账号名称
  "profile_id": "string",         // BitBrowser Profile ID
  "channel_url": "string",        // YouTube频道URL
  "window_number": "string",      // 窗口序号
  "description": "string",        // 描述
  "is_active": true,              // 是否激活
  "created_at": "2024-01-26T10:00:00",
  "updated_at": "2024-01-26T10:00:00"
}
```

---

## API接口列表

## 1. Pipeline管理接口

### 1.1 运行Pipeline任务

**端点**: `POST /api/pipeline/run`

**功能**: 创建并运行一个新的Pipeline任务

**请求体**:
```json
{
  "video_id": "dQw4w9WgXcQ",
  "creator_id": "test_creator",
  "gender": 1,
  "duration": 60,
  "export_video": false,
  "enable_subtitle": true
}
```

**响应**: 
```json
{
  "task_id": "test_creator_dQw4w9WgXcQ_abc12345",
  "message": "任务已启动",
  "status_url": "/api/pipeline/status/test_creator_dQw4w9WgXcQ_abc12345",
  "result_url": "/api/pipeline/result/test_creator_dQw4w9WgXcQ_abc12345"
}
```

**状态码**:
- 200: 成功创建任务
- 400: 请求参数错误
- 500: 服务器内部错误

---

### 1.2 查询任务状态

**端点**: `GET /api/pipeline/status/{task_id}`

**功能**: 获取指定任务的当前状态

**路径参数**:
- `task_id`: 任务ID

**响应**:
```json
{
  "task_id": "test_creator_dQw4w9WgXcQ_abc12345",
  "status": "running",
  "current_stage": "语音生成",
  "progress": {
    "故事二创": "成功",
    "语音生成": "运行中",
    "剪映草稿生成": "待处理"
  },
  "created_at": "2024-01-26T10:00:00",
  "started_at": "2024-01-26T10:01:00",
  "completed_at": null,
  "total_duration": null
}
```

**状态码**:
- 200: 成功
- 404: 任务不存在

---

### 1.3 获取任务结果

**端点**: `GET /api/pipeline/result/{task_id}`

**功能**: 获取已完成任务的详细结果

**路径参数**:
- `task_id`: 任务ID

**响应**:
```json
{
  "task_id": "test_creator_dQw4w9WgXcQ_abc12345",
  "status": "completed",
  "youtube_metadata": {
    "title": "精彩故事标题",
    "description": "这是一个精彩的故事...",
    "tags": ["故事", "娱乐", "创意"]
  },
  "video_path": "/path/to/video.mp4",
  "preview_url": "https://example.com/preview.mp4",
  "draft_path": "/path/to/draft",
  "audio_path": "/path/to/audio.mp3",
  "story_path": "/path/to/story.txt",
  "thumbnail_path": "/path/to/thumbnail.jpg",
  "error": null,
  "publish_tasks": [
    {
      "publish_id": "pub_xxx",
      "account_id": "yt_001_novel",
      "status": "success",
      "youtube_video_url": "https://youtube.com/watch?v=xxx"
    }
  ]
}
```

**状态码**:
- 200: 成功
- 400: 任务未完成
- 404: 任务不存在

---

### 1.4 查询任务历史

**端点**: `GET /api/pipeline/history`

**功能**: 查询历史任务记录

**查询参数**:
- `creator_id` (可选): 创作者ID筛选
- `status` (可选): 状态筛选 (pending/running/completed/failed)
- `start_date` (可选): 开始日期 (ISO格式: 2024-01-26T00:00:00)
- `end_date` (可选): 结束日期
- `page` (可选): 页码，默认1
- `page_size` (可选): 每页数量，默认20，最大100

**请求示例**:
```
GET /api/pipeline/history?creator_id=test_creator&status=completed&page=1&page_size=20
```

**响应**:
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "tasks": [
    {
      "id": 1,
      "task_id": "test_creator_video1_abc123",
      "video_id": "video1",
      "creator_id": "test_creator",
      "status": "completed",
      "created_at": "2024-01-26T10:00:00",
      "completed_at": "2024-01-26T10:05:00",
      "total_duration": 300.5,
      "youtube_metadata": {...},
      "video_path": "/path/to/video.mp4"
    }
  ]
}
```

---

### 1.5 获取统计信息

**端点**: `GET /api/pipeline/statistics`

**功能**: 获取Pipeline任务统计信息

**查询参数**:
- `creator_id` (可选): 创作者ID筛选

**响应**:
```json
{
  "pipeline": {
    "total": 1000,
    "completed": 900,
    "failed": 50,
    "running": 10,
    "success_rate": 90.0
  },
  "publish": {
    "total": 2000,
    "success": 1800,
    "failed": 200,
    "success_rate": 90.0
  },
  "avg_duration_seconds": 240.5
}
```

---

## 2. 发布管理接口

### 2.1 创建发布任务

**端点**: `POST /api/publish/create`

**功能**: 为已完成的Pipeline任务创建发布任务

**请求体**:
```json
{
  "task_id": "test_creator_video1_abc123",
  "account_ids": ["yt_001_novel", "yt_002_novel"],
  "video_title": "自定义标题",
  "video_description": "自定义描述",
  "video_tags": ["标签1", "标签2"],
  "thumbnail_path": "/path/to/thumbnail.jpg",
  "scheduled_time": "2024-01-27T18:00:00",
  "privacy_status": "public"
}
```

**响应**:
```json
{
  "message": "创建了 2 个发布任务",
  "publish_tasks": [
    {
      "publish_id": "pub_task1_yt001_xyz",
      "task_id": "test_creator_video1_abc123",
      "account_id": "yt_001_novel",
      "status": "pending"
    },
    {
      "publish_id": "pub_task1_yt002_xyz",
      "task_id": "test_creator_video1_abc123",
      "account_id": "yt_002_novel",
      "status": "pending"
    }
  ]
}
```

---

### 2.2 执行发布任务

**端点**: `POST /api/publish/execute/{publish_id}`

**功能**: 执行指定的发布任务（上传到YouTube）

**路径参数**:
- `publish_id`: 发布任务ID

**响应**:
```json
{
  "message": "发布任务已启动",
  "publish_id": "pub_task1_yt001_xyz"
}
```

---

### 2.3 批量发布

**端点**: `POST /api/publish/batch`

**功能**: 批量创建并执行发布任务

**请求体**: 与创建发布任务相同

**响应**:
```json
{
  "message": "启动了 2 个发布任务",
  "results": [
    {
      "publish_id": "pub_task1_yt001_xyz",
      "account_id": "yt_001_novel",
      "status": "started"
    },
    {
      "publish_id": "pub_task1_yt002_xyz",
      "account_id": "yt_002_novel",
      "status": "started"
    }
  ]
}
```

---

### 2.4 查询发布历史

**端点**: `GET /api/publish/history`

**功能**: 查询发布任务历史

**查询参数**:
- `task_id` (可选): Pipeline任务ID筛选
- `account_id` (可选): 账号ID筛选
- `status` (可选): 状态筛选 (pending/uploading/success/failed)
- `limit` (可选): 返回数量限制，默认100，最大500

**响应**:
```json
{
  "total": 50,
  "publish_tasks": [
    {
      "publish_id": "pub_task1_yt001_xyz",
      "task_id": "test_creator_video1_abc123",
      "account_id": "yt_001_novel",
      "video_title": "视频标题",
      "status": "success",
      "youtube_video_id": "dQw4w9WgXcQ",
      "youtube_video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "created_at": "2024-01-26T10:00:00",
      "upload_completed_at": "2024-01-26T10:05:00"
    }
  ]
}
```

---

### 2.5 重试失败的发布

**端点**: `POST /api/publish/retry/{publish_id}`

**功能**: 重试失败的发布任务

**路径参数**:
- `publish_id`: 发布任务ID

**响应**:
```json
{
  "message": "重试任务已启动",
  "publish_id": "pub_task1_yt001_xyz"
}
```

---

## 3. 账号管理接口

### 3.1 获取所有账号

**端点**: `GET /api/accounts`

**功能**: 获取所有YouTube账号列表

**查询参数**:
- `active_only` (可选): 是否只返回激活账号，默认true

**响应**:
```json
{
  "total": 15,
  "accounts": [
    {
      "id": 1,
      "account_id": "yt_001_novel",
      "account_name": "youtube-001-小说",
      "profile_id": "1590cf235ecf4d66bf7e1f57242d520f",
      "channel_url": null,
      "window_number": "1960",
      "description": "窗口序号: 1960",
      "is_active": true,
      "created_at": "2024-01-26T10:00:00",
      "updated_at": null
    }
  ]
}
```

---

### 3.2 获取账号详情

**端点**: `GET /api/accounts/{account_id}`

**功能**: 获取指定账号的详细信息

**路径参数**:
- `account_id`: 账号ID

**响应**: 单个账号对象（结构同上）

**状态码**:
- 200: 成功
- 404: 账号不存在

---

### 3.3 获取账号统计信息

**端点**: `GET /api/accounts/{account_id}/statistics`

**功能**: 获取指定账号的发布统计信息

**路径参数**:
- `account_id`: 账号ID

**响应**:
```json
{
  "account_id": "yt_001_novel",
  "total_publish": 100,
  "success": 90,
  "failed": 5,
  "pending": 5,
  "success_rate": 90.0
}
```

---

### 3.4 更新账号状态

**端点**: `PUT /api/accounts/{account_id}/status`

**功能**: 激活或禁用账号

**路径参数**:
- `account_id`: 账号ID

**查询参数**:
- `is_active`: true激活，false禁用

**请求示例**:
```
PUT /api/accounts/yt_001_novel/status?is_active=false
```

**响应**:
```json
{
  "message": "账号状态已更新为 禁用"
}
```

---

## 4. 系统接口

### 4.1 健康检查

**端点**: `GET /health`

**功能**: 检查服务健康状态

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-26T10:00:00",
  "database": "connected",
  "accounts_loaded": 15
}
```

---

### 4.2 API信息

**端点**: `GET /`

**功能**: 获取API基本信息和端点列表

**响应**:
```json
{
  "name": "Video Pipeline API with Database",
  "version": "0.2.0",
  "endpoints": {
    "pipeline": {
      "run": "/api/pipeline/run",
      "status": "/api/pipeline/status/{task_id}",
      "result": "/api/pipeline/result/{task_id}",
      "history": "/api/pipeline/history",
      "statistics": "/api/pipeline/statistics"
    },
    "publish": {
      "create": "/api/publish/create",
      "execute": "/api/publish/execute/{publish_id}",
      "batch": "/api/publish/batch",
      "history": "/api/publish/history",
      "retry": "/api/publish/retry/{publish_id}"
    },
    "accounts": {
      "list": "/api/accounts",
      "detail": "/api/accounts/{account_id}",
      "statistics": "/api/accounts/{account_id}/statistics",
      "update_status": "/api/accounts/{account_id}/status"
    },
    "health": "/health"
  }
}
```

---

## 错误码说明

### HTTP状态码
- **200 OK**: 请求成功
- **201 Created**: 资源创建成功
- **400 Bad Request**: 请求参数错误
- **404 Not Found**: 资源不存在
- **500 Internal Server Error**: 服务器内部错误

### 错误响应格式
```json
{
  "detail": "错误详细信息"
}
```

### 常见错误
| 错误码 | 说明 | 解决方案 |
|-------|------|---------|
| 404 | 任务不存在 | 检查task_id是否正确 |
| 400 | 任务未完成 | 等待任务完成后再查询结果 |
| 400 | 请求参数错误 | 检查请求体格式和必填字段 |
| 500 | Pipeline执行失败 | 查看日志了解详细错误 |

---

## 使用示例

### 完整的工作流程

#### 1. 创建并运行Pipeline任务

```python
import requests
import time

# 1. 创建任务
response = requests.post(
    "http://localhost:51082/api/pipeline/run",
    json={
        "video_id": "dQw4w9WgXcQ",
        "creator_id": "my_channel",
        "gender": 1,
        "duration": 60,
        "export_video": True
    }
)
task_data = response.json()
task_id = task_data["task_id"]
print(f"任务已创建: {task_id}")

# 2. 轮询任务状态
while True:
    response = requests.get(f"http://localhost:51082/api/pipeline/status/{task_id}")
    status = response.json()
    print(f"当前状态: {status['status']}, 阶段: {status['current_stage']}")
    
    if status['status'] in ['completed', 'failed']:
        break
    time.sleep(10)

# 3. 获取任务结果
if status['status'] == 'completed':
    response = requests.get(f"http://localhost:51082/api/pipeline/result/{task_id}")
    result = response.json()
    print(f"视频路径: {result['video_path']}")
    print(f"YouTube元数据: {result['youtube_metadata']}")
```

#### 2. 发布到多个YouTube账号

```python
# 获取可用账号
response = requests.get("http://localhost:51082/api/accounts?active_only=true")
accounts = response.json()["accounts"][:3]  # 使用前3个账号
account_ids = [acc["account_id"] for acc in accounts]

# 批量发布
response = requests.post(
    "http://localhost:51082/api/publish/batch",
    json={
        "task_id": task_id,
        "account_ids": account_ids,
        "video_title": "精彩视频",
        "video_description": "这是一个精彩的视频",
        "video_tags": ["娱乐", "故事"],
        "privacy_status": "public"
    }
)
publish_results = response.json()
print(f"发布结果: {publish_results}")
```

#### 3. 查询历史记录

```python
# 查询最近的任务
response = requests.get(
    "http://localhost:51082/api/pipeline/history",
    params={
        "creator_id": "my_channel",
        "status": "completed",
        "page": 1,
        "page_size": 10
    }
)
history = response.json()
print(f"找到 {history['total']} 个历史任务")

# 查询发布历史
response = requests.get(
    "http://localhost:51082/api/publish/history",
    params={"limit": 50}
)
publish_history = response.json()
print(f"找到 {publish_history['total']} 个发布记录")
```

### cURL命令示例

```bash
# 创建Pipeline任务
curl -X POST http://localhost:51082/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_video",
    "creator_id": "test_user",
    "gender": 1,
    "duration": 60
  }'

# 查询任务状态
curl http://localhost:51082/api/pipeline/status/test_user_test_video_abc123

# 获取账号列表
curl http://localhost:51082/api/accounts

# 查询统计信息
curl http://localhost:51082/api/pipeline/statistics?creator_id=test_user
```

---

## 附录

### 环境变量配置

创建 `.env` 文件配置以下变量：

```bash
# 数据库路径
DB_PATH=./data/pipeline_tasks.db

# 日志级别
LOG_LEVEL=INFO

# YouTube上传服务
YTENGINE_HOST=http://localhost:51077
USE_MOCK_UPLOAD=true  # 测试模式

# 草稿目录
DRAFT_LOCAL_DIR=/path/to/drafts

# API服务
API_HOST=0.0.0.0
API_PORT=51082
```

### 数据库迁移

从SQLite迁移到MySQL：

```bash
# 备份现有数据
python3 db_migrate.py backup --db sqlite:///data/pipeline_tasks.db --output backup.db

# 迁移到MySQL
python3 db_migrate.py migrate \
  --from data/pipeline_tasks.db \
  --to mysql+pymysql://user:password@localhost:3306/pipeline_db
```

### 日志文件

日志文件位置：
- API日志: `api_with_db.log`
- Pipeline日志: `logs/pipeline_*.log`

### 技术支持

如有问题请查看：
- Swagger文档: http://localhost:51082/docs
- ReDoc文档: http://localhost:51082/redoc
- 项目仓库: [GitHub地址]

---

*文档版本: 1.0.0*  
*更新日期: 2024-01-26*