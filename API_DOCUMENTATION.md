# YouTube Story Generator API 文档

本文档描述了前端所需的所有后端 API 接口定义。

## 基础信息

- **基础URL**: `http://localhost:51082`
- **API前缀**: `/api/v1`
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: `application/json`
- **编码**: `UTF-8`

## 1. Pipeline 任务管理接口

### 1.1 创建任务

**接口**: `POST /api/v1/pipeline/create`

**描述**: 创建新的视频生成任务

**请求体**:
```json
{
  "workflow": "YouTube故事",  // 工作流类型: "YouTube故事" | "YouTube漫画" | "YouTube解压"
  "params": {
    "title": "故事标题",
    "genre": "恐怖",  // 类型: 恐怖、搞笑、感人等
    "duration": 180,  // 时长（秒）
    "style": "realistic"  // 风格
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_20240115_123456",
    "status": "pending",
    "workflow": "YouTube故事",
    "created_at": "2024-01-15T10:30:45Z"
  }
}
```

### 1.2 获取任务列表

**接口**: `GET /api/v1/pipeline/tasks`

**描述**: 获取所有任务列表

**查询参数**:
- `status` (可选): 过滤状态 pending|running|completed|failed
- `page` (可选): 页码，默认1
- `limit` (可选): 每页数量，默认20

**响应**:
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "task_20240115_123456",
        "workflow": "YouTube故事",
        "status": "completed",  // pending|running|completed|failed
        "progress": 100,
        "current_stage": "完成",
        "created_at": "2024-01-15T10:30:45Z",
        "updated_at": "2024-01-15T10:35:20Z",
        "duration": 275,  // 执行时长（秒）
        "result": {
          "video_path": "/outputs/task_20240115_123456/final.mp4",
          "preview_url": "http://localhost:51082/preview/task_20240115_123456.mp4",
          "youtube_metadata": {
            "title": "【恐怖故事】午夜的敲门声",
            "description": "这是一个关于...",
            "tags": ["恐怖故事", "悬疑", "短视频"]
          }
        }
      }
    ],
    "total": 45,
    "page": 1,
    "limit": 20
  }
}
```

### 1.3 获取任务详情

**接口**: `GET /api/v1/pipeline/task/{task_id}`

**描述**: 获取指定任务的详细信息

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_20240115_123456",
    "workflow": "YouTube故事",
    "status": "running",
    "progress": 45,
    "current_stage": "生成音频",
    "stages": [
      {
        "name": "生成剧本",
        "status": "completed",
        "start_time": "2024-01-15T10:30:45Z",
        "end_time": "2024-01-15T10:31:05Z",
        "output": {
          "script": "剧本内容...",
          "scenes": 5
        }
      },
      {
        "name": "生成图像",
        "status": "completed",
        "start_time": "2024-01-15T10:31:05Z",
        "end_time": "2024-01-15T10:33:20Z",
        "output": {
          "images": [
            "/outputs/task_20240115_123456/scene_1.png",
            "/outputs/task_20240115_123456/scene_2.png"
          ]
        }
      },
      {
        "name": "生成音频",
        "status": "running",
        "start_time": "2024-01-15T10:33:20Z",
        "progress": 60
      }
    ],
    "params": {
      "title": "午夜的敲门声",
      "genre": "恐怖",
      "duration": 180,
      "style": "realistic"
    },
    "created_at": "2024-01-15T10:30:45Z",
    "updated_at": "2024-01-15T10:33:45Z"
  }
}
```

### 1.4 获取任务结果

**接口**: `GET /api/v1/pipeline/task/{task_id}/result`

**描述**: 获取已完成任务的结果文件

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_20240115_123456",
    "video_path": "/outputs/task_20240115_123456/final.mp4",
    "preview_url": "http://localhost:51082/preview/task_20240115_123456.mp4",
    "download_url": "http://localhost:51082/download/task_20240115_123456.zip",
    "youtube_metadata": {
      "title": "【恐怖故事】午夜的敲门声",
      "description": "在一个寂静的夜晚...\n\n时间戳：\n00:00 开场\n00:30 故事开始\n02:45 结尾",
      "tags": ["恐怖故事", "悬疑", "短视频", "睡前故事"],
      "category": "Entertainment",
      "thumbnail": "/outputs/task_20240115_123456/thumbnail.jpg"
    },
    "files": {
      "video": "/outputs/task_20240115_123456/final.mp4",
      "audio": "/outputs/task_20240115_123456/audio.mp3",
      "script": "/outputs/task_20240115_123456/script.txt",
      "images": [
        "/outputs/task_20240115_123456/scene_1.png",
        "/outputs/task_20240115_123456/scene_2.png",
        "/outputs/task_20240115_123456/scene_3.png"
      ],
      "subtitles": "/outputs/task_20240115_123456/subtitles.srt"
    },
    "statistics": {
      "duration": 180,
      "file_size": 45678901,  // 字节
      "resolution": "1920x1080",
      "fps": 30,
      "bitrate": "5000k"
    }
  }
}
```

### 1.5 取消任务

**接口**: `POST /api/v1/pipeline/task/{task_id}/cancel`

**描述**: 取消正在运行的任务

**响应**:
```json
{
  "success": true,
  "message": "任务已取消",
  "data": {
    "task_id": "task_20240115_123456",
    "status": "cancelled"
  }
}
```

### 1.6 重试任务

**接口**: `POST /api/v1/pipeline/task/{task_id}/retry`

**描述**: 重试失败的任务

**响应**:
```json
{
  "success": true,
  "message": "任务已重新启动",
  "data": {
    "task_id": "task_20240115_123456",
    "new_task_id": "task_20240115_234567",
    "status": "pending"
  }
}
```

### 1.7 删除任务

**接口**: `DELETE /api/v1/pipeline/task/{task_id}`

**描述**: 删除任务及其所有相关文件

**响应**:
```json
{
  "success": true,
  "message": "任务已删除"
}
```

## 2. 账号管理接口

### 2.1 获取账号列表

**接口**: `GET /api/v1/accounts`

**描述**: 获取所有YouTube账号列表

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "acc_001",
      "name": "主账号",
      "youtube_account": "MyYouTubeChannel",
      "youtube_channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
      "bitbrowser_name": "BitBrowser_Main",
      "status": "active",  // active|inactive
      "statistics": {
        "subscribers": 1250,
        "total_views": 45000,
        "videos_count": 35,
        "last_upload": "2024-01-14T15:30:00Z"
      },
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### 2.2 创建账号

**接口**: `POST /api/v1/accounts`

**描述**: 添加新的YouTube账号

**请求体**:
```json
{
  "name": "新账号",
  "youtube_account": "NewYouTubeChannel",
  "youtube_channel_id": "UC_xxxxxxxxxxxxx",
  "bitbrowser_name": "BitBrowser_New"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "acc_002",
    "name": "新账号",
    "youtube_account": "NewYouTubeChannel",
    "youtube_channel_id": "UC_xxxxxxxxxxxxx",
    "bitbrowser_name": "BitBrowser_New",
    "status": "active",
    "created_at": "2024-01-15T11:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 2.3 更新账号

**接口**: `PUT /api/v1/accounts/{account_id}`

**描述**: 更新账号信息

**请求体**:
```json
{
  "name": "更新的账号名",
  "youtube_account": "UpdatedChannel",
  "bitbrowser_name": "BitBrowser_Updated",
  "status": "active"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "acc_001",
    "name": "更新的账号名",
    "youtube_account": "UpdatedChannel",
    "bitbrowser_name": "BitBrowser_Updated",
    "status": "active",
    "updated_at": "2024-01-15T11:30:00Z"
  }
}
```

### 2.4 删除账号

**接口**: `DELETE /api/v1/accounts/{account_id}`

**描述**: 删除账号

**响应**:
```json
{
  "success": true,
  "message": "账号已删除"
}
```

## 3. 发布管理接口

### 3.1 创建发布任务

**接口**: `POST /api/v1/publish`

**描述**: 创建视频发布任务

**请求体**:
```json
{
  "task_id": "task_20240115_123456",
  "account_id": "acc_001",
  "title": "【恐怖故事】午夜的敲门声",
  "description": "故事简介...",
  "video_path": "/outputs/task_20240115_123456/final.mp4",
  "thumbnail_path": "/outputs/task_20240115_123456/thumbnail.jpg",
  "tags": ["恐怖故事", "悬疑", "短视频"],
  "category": "Entertainment",
  "visibility": "public",  // public|private|unlisted
  "publish_mode": "immediate",  // immediate|scheduled|interval
  "publish_time": "2024-01-15T20:00:00Z",  // 仅scheduled模式
  "publish_interval": 60  // 分钟，仅interval模式
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "publish_id": "pub_20240115_567890",
    "task_id": "task_20240115_123456",
    "account_id": "acc_001",
    "status": "pending",
    "created_at": "2024-01-15T11:00:00Z"
  }
}
```

### 3.2 获取发布任务列表

**接口**: `GET /api/v1/publish/tasks`

**描述**: 获取所有发布任务

**查询参数**:
- `task_id` (可选): 按原始任务ID过滤
- `account_id` (可选): 按账号ID过滤
- `status` (可选): pending|publishing|published|failed

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "publish_id": "pub_20240115_567890",
      "task_id": "task_20240115_123456",
      "account_id": "acc_001",
      "account_name": "主账号",
      "title": "【恐怖故事】午夜的敲门声",
      "status": "published",  // pending|publishing|published|failed
      "youtube_url": "https://youtube.com/watch?v=abc123",
      "youtube_video_id": "abc123",
      "publish_time": "2024-01-15T20:00:00Z",
      "published_at": "2024-01-15T20:00:35Z",
      "statistics": {
        "views": 125,
        "likes": 15,
        "comments": 3
      },
      "error_message": null,
      "created_at": "2024-01-15T11:00:00Z",
      "updated_at": "2024-01-15T20:00:35Z"
    }
  ]
}
```

### 3.3 获取发布任务详情

**接口**: `GET /api/v1/publish/{publish_id}`

**描述**: 获取发布任务详细信息

**响应**:
```json
{
  "success": true,
  "data": {
    "publish_id": "pub_20240115_567890",
    "task_id": "task_20240115_123456",
    "account_id": "acc_001",
    "account_name": "主账号",
    "title": "【恐怖故事】午夜的敲门声",
    "description": "完整描述...",
    "video_path": "/outputs/task_20240115_123456/final.mp4",
    "thumbnail_path": "/outputs/task_20240115_123456/thumbnail.jpg",
    "tags": ["恐怖故事", "悬疑", "短视频"],
    "category": "Entertainment",
    "visibility": "public",
    "status": "published",
    "youtube_url": "https://youtube.com/watch?v=abc123",
    "youtube_video_id": "abc123",
    "youtube_studio_url": "https://studio.youtube.com/video/abc123/edit",
    "publish_time": "2024-01-15T20:00:00Z",
    "published_at": "2024-01-15T20:00:35Z",
    "ytengine_response": {
      "taskId": "pub_20240115_567890",
      "status": "completed",
      "videoUrl": "https://youtu.be/abc123",
      "executionTime": 35.2
    },
    "created_at": "2024-01-15T11:00:00Z",
    "updated_at": "2024-01-15T20:00:35Z"
  }
}
```

### 3.4 取消发布任务

**接口**: `POST /api/v1/publish/{publish_id}/cancel`

**描述**: 取消待发布的任务

**响应**:
```json
{
  "success": true,
  "message": "发布任务已取消",
  "data": {
    "publish_id": "pub_20240115_567890",
    "status": "cancelled"
  }
}
```

### 3.5 重试发布任务

**接口**: `POST /api/v1/publish/{publish_id}/retry`

**描述**: 重试失败的发布任务

**响应**:
```json
{
  "success": true,
  "message": "发布任务已重新启动",
  "data": {
    "publish_id": "pub_20240115_567890",
    "status": "pending"
  }
}
```

## 4. 统计分析接口

### 4.1 获取总体统计

**接口**: `GET /api/v1/stats/overview`

**描述**: 获取系统总体统计数据

**响应**:
```json
{
  "success": true,
  "data": {
    "tasks": {
      "total": 156,
      "pending": 2,
      "running": 3,
      "completed": 145,
      "failed": 6,
      "success_rate": 92.9,
      "avg_duration": 285  // 秒
    },
    "publish": {
      "total": 132,
      "published": 125,
      "pending": 5,
      "failed": 2,
      "total_views": 45000,
      "total_likes": 1250,
      "total_comments": 320
    },
    "storage": {
      "total_size": 45678901234,  // 字节
      "videos_count": 145,
      "avg_video_size": 314682078  // 字节
    },
    "accounts": {
      "total": 5,
      "active": 4,
      "inactive": 1
    },
    "period": {
      "today_tasks": 12,
      "today_published": 10,
      "week_tasks": 45,
      "week_published": 42,
      "month_tasks": 156,
      "month_published": 132
    }
  }
}
```

### 4.2 获取任务统计

**接口**: `GET /api/v1/stats/tasks`

**描述**: 获取任务执行统计

**查询参数**:
- `start_date`: 开始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)
- `workflow` (可选): 工作流类型过滤

**响应**:
```json
{
  "success": true,
  "data": {
    "daily": [
      {
        "date": "2024-01-15",
        "total": 12,
        "completed": 10,
        "failed": 2,
        "avg_duration": 290
      }
    ],
    "by_workflow": {
      "YouTube故事": {
        "total": 80,
        "completed": 75,
        "failed": 5,
        "avg_duration": 280
      },
      "YouTube漫画": {
        "total": 50,
        "completed": 48,
        "failed": 2,
        "avg_duration": 320
      },
      "YouTube解压": {
        "total": 26,
        "completed": 22,
        "failed": 4,
        "avg_duration": 250
      }
    },
    "by_hour": [
      {
        "hour": "00",
        "count": 2
      },
      {
        "hour": "01",
        "count": 1
      }
    ]
  }
}
```

### 4.3 获取发布统计

**接口**: `GET /api/v1/stats/publish`

**描述**: 获取发布统计数据

**查询参数**:
- `account_id` (可选): 按账号过滤
- `period` (可选): today|week|month|all

**响应**:
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_published": 125,
      "total_views": 45000,
      "total_likes": 1250,
      "total_comments": 320,
      "avg_views_per_video": 360,
      "engagement_rate": 3.2
    },
    "by_account": [
      {
        "account_id": "acc_001",
        "account_name": "主账号",
        "videos_published": 85,
        "total_views": 32000,
        "total_likes": 900,
        "subscribers_gained": 450
      }
    ],
    "top_videos": [
      {
        "publish_id": "pub_20240110_123456",
        "title": "爆款视频标题",
        "views": 5000,
        "likes": 250,
        "comments": 45,
        "youtube_url": "https://youtube.com/watch?v=xyz"
      }
    ],
    "performance_trend": [
      {
        "date": "2024-01-15",
        "views": 1250,
        "likes": 45,
        "comments": 12
      }
    ]
  }
}
```

## 5. 文件管理接口

### 5.1 上传文件

**接口**: `POST /api/v1/files/upload`

**描述**: 上传文件（封面图片、音频等）

**请求类型**: `multipart/form-data`

**表单字段**:
- `file`: 文件
- `type`: 文件类型 (thumbnail|audio|video|image)
- `task_id` (可选): 关联的任务ID

**响应**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_20240115_789012",
    "file_path": "/uploads/2024/01/15/file_20240115_789012.jpg",
    "file_url": "http://localhost:51082/files/file_20240115_789012.jpg",
    "file_size": 245678,
    "mime_type": "image/jpeg",
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### 5.2 获取文件信息

**接口**: `GET /api/v1/files/{file_id}`

**描述**: 获取文件详细信息

**响应**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_20240115_789012",
    "file_path": "/uploads/2024/01/15/file_20240115_789012.jpg",
    "file_url": "http://localhost:51082/files/file_20240115_789012.jpg",
    "file_size": 245678,
    "mime_type": "image/jpeg",
    "dimensions": {
      "width": 1280,
      "height": 720
    },
    "task_id": "task_20240115_123456",
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### 5.3 删除文件

**接口**: `DELETE /api/v1/files/{file_id}`

**描述**: 删除文件

**响应**:
```json
{
  "success": true,
  "message": "文件已删除"
}
```

### 5.4 下载任务文件包

**接口**: `GET /api/v1/files/download/{task_id}`

**描述**: 下载任务的所有文件（ZIP格式）

**响应**: 二进制文件流 (application/zip)

## 6. 系统配置接口

### 6.1 获取工作流配置

**接口**: `GET /api/v1/config/workflows`

**描述**: 获取所有可用的工作流配置

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "key": "youtube_story",
      "name": "YouTube故事",
      "description": "生成故事类短视频",
      "icon": "book",
      "params": [
        {
          "key": "genre",
          "label": "故事类型",
          "type": "select",
          "required": true,
          "options": ["恐怖", "搞笑", "感人", "悬疑", "科幻"]
        },
        {
          "key": "duration",
          "label": "视频时长(秒)",
          "type": "number",
          "required": true,
          "min": 60,
          "max": 600,
          "default": 180
        },
        {
          "key": "style",
          "label": "画面风格",
          "type": "select",
          "required": false,
          "options": ["realistic", "cartoon", "anime", "pixel"],
          "default": "realistic"
        }
      ]
    },
    {
      "key": "youtube_comic",
      "name": "YouTube漫画",
      "description": "生成漫画风格视频",
      "icon": "picture",
      "params": [
        {
          "key": "comic_style",
          "label": "漫画风格",
          "type": "select",
          "required": true,
          "options": ["日式", "美式", "韩式", "国风"]
        }
      ]
    },
    {
      "key": "youtube_asmr",
      "name": "YouTube解压",
      "description": "生成解压类视频",
      "icon": "thunderbolt",
      "params": [
        {
          "key": "asmr_type",
          "label": "解压类型",
          "type": "select",
          "required": true,
          "options": ["切割", "整理", "清洁", "制作"]
        }
      ]
    }
  ]
}
```

### 6.2 获取系统设置

**接口**: `GET /api/v1/config/settings`

**描述**: 获取系统设置

**响应**:
```json
{
  "success": true,
  "data": {
    "ytengine": {
      "enabled": true,
      "url": "http://localhost:51077",
      "mock_mode": false,
      "timeout": 300000
    },
    "storage": {
      "output_dir": "/outputs",
      "upload_dir": "/uploads",
      "max_file_size": 104857600,  // 100MB
      "auto_cleanup": true,
      "cleanup_after_days": 30
    },
    "pipeline": {
      "max_concurrent_tasks": 5,
      "default_timeout": 600000,  // 10分钟
      "retry_on_failure": true,
      "max_retry_count": 3
    },
    "publish": {
      "default_visibility": "private",
      "default_category": "Entertainment",
      "auto_publish": false,
      "schedule_enabled": true
    }
  }
}
```

### 6.3 更新系统设置

**接口**: `PUT /api/v1/config/settings`

**描述**: 更新系统设置（需要管理员权限）

**请求体**:
```json
{
  "ytengine": {
    "mock_mode": true
  },
  "publish": {
    "default_visibility": "public"
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "设置已更新",
  "data": {
    // 返回更新后的完整设置
  }
}
```

## 7. WebSocket 实时通信

### 7.1 任务进度推送

**连接地址**: `ws://localhost:51082/ws/task/{task_id}`

**消息格式**:
```json
{
  "type": "progress",  // progress|stage|completed|failed|log
  "task_id": "task_20240115_123456",
  "data": {
    "progress": 45,
    "stage": "生成音频",
    "message": "正在生成第3段音频...",
    "timestamp": "2024-01-15T10:33:45Z"
  }
}
```

### 7.2 发布状态推送

**连接地址**: `ws://localhost:51082/ws/publish/{publish_id}`

**消息格式**:
```json
{
  "type": "publish_status",  // publish_status|upload_progress|completed|failed
  "publish_id": "pub_20240115_567890",
  "data": {
    "status": "publishing",
    "progress": 75,
    "message": "正在上传视频...",
    "timestamp": "2024-01-15T20:00:15Z"
  }
}
```

## 错误响应格式

所有接口的错误响应都遵循以下格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": "详细错误信息（可选）"
  }
}
```

### 常见错误码

- `UNAUTHORIZED`: 未授权访问
- `FORBIDDEN`: 无权限
- `NOT_FOUND`: 资源不存在
- `BAD_REQUEST`: 请求参数错误
- `INTERNAL_ERROR`: 服务器内部错误
- `TASK_NOT_FOUND`: 任务不存在
- `ACCOUNT_NOT_FOUND`: 账号不存在
- `FILE_TOO_LARGE`: 文件过大
- `INVALID_FILE_TYPE`: 文件类型不支持
- `YTENGINE_ERROR`: YTEngine服务错误
- `QUOTA_EXCEEDED`: 配额超限

## 认证说明

大部分接口需要认证，请在请求头中包含：

```
Authorization: Bearer {jwt_token}
```

JWT Token 通过登录接口获取（如需要可以添加登录接口）。

## 分页参数

支持分页的接口都接受以下查询参数：

- `page`: 页码，从1开始
- `limit`: 每页数量，默认20，最大100
- `sort`: 排序字段
- `order`: 排序方向 (asc|desc)

## 注意事项

1. **文件路径**: 所有文件路径都是服务器端的绝对路径
2. **时间格式**: 所有时间都使用ISO 8601格式 (UTC)
3. **ID格式**: 使用格式 `{type}_{timestamp}_{random}` 
4. **并发限制**: 同一账号最多5个并发任务
5. **文件大小**: 单个文件最大100MB
6. **请求频率**: API限制每秒最多10个请求

## 集成 YTEngine

发布功能通过 YTEngine 服务实现真实的 YouTube 上传：

1. **YTEngine 健康检查**: 在发布前检查服务状态
2. **使用 BitBrowser profileId**: account.bitbrowser_name 作为 YTEngine 的 profileId
3. **Mock 模式**: 开发环境可使用 mock 模式测试
4. **真实上传**: 生产环境调用 YTEngine `/api/upload` 接口

## 部署建议

1. **使用 HTTPS**: 生产环境应使用 HTTPS
2. **API 网关**: 建议使用 Nginx 或 Kong 作为 API 网关
3. **限流**: 实施请求限流保护
4. **监控**: 添加 API 监控和日志
5. **备份**: 定期备份生成的视频文件