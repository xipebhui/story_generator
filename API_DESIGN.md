# Pipeline API设计文档

## 概述

这是一个简化版的Pipeline API服务，用于异步执行视频生成任务，并返回YouTube元数据和视频文件路径。

## 技术架构

- **框架**: FastAPI（原生异步支持）
- **任务管理**: 内存存储 + BackgroundTasks
- **执行模式**: 异步后台执行
- **状态跟踪**: 简单的状态机（pending → running → completed/failed）

## API端点

### 1. 提交任务
**POST** `/api/pipeline/run`

请求体:
```json
{
    "video_id": "test_001",
    "creator_id": "user_123", 
    "gender": 1,           // 0=男性, 1=女性
    "duration": 60,        // 视频时长(秒)
    "image_dir": null,     // 可选：图片目录
    "export_video": false  // 是否导出视频
}
```

响应:
```json
{
    "task_id": "user_123_test_001_a1b2c3d4",
    "message": "任务已启动",
    "status_url": "/api/pipeline/status/{task_id}",
    "result_url": "/api/pipeline/result/{task_id}"
}
```

### 2. 查询状态
**GET** `/api/pipeline/status/{task_id}`

响应:
```json
{
    "task_id": "user_123_test_001_a1b2c3d4",
    "status": "running",
    "current_stage": "语音生成",
    "progress": {
        "故事二创": "成功",
        "语音生成": "运行中",
        "剪映草稿生成": "待处理",
        "视频导出": "待处理"
    },
    "created_at": "2024-01-01T12:00:00",
    "completed_at": null
}
```

### 3. 获取结果
**GET** `/api/pipeline/result/{task_id}`

成功响应:
```json
{
    "task_id": "user_123_test_001_a1b2c3d4",
    "status": "completed",
    "youtube_metadata": {
        "title": "视频标题",
        "description": "视频描述",
        "tags": ["标签1", "标签2"],
        "category": "娱乐"
    },
    "video_path": "/path/to/video.mp4",
    "draft_path": "/path/to/draft",
    "audio_path": "/path/to/audio.mp3",
    "story_path": "/path/to/story.txt",
    "error": null
}
```

失败响应:
```json
{
    "task_id": "user_123_test_001_a1b2c3d4",
    "status": "failed",
    "youtube_metadata": null,
    "video_path": null,
    "error": "错误信息"
}
```

### 4. 列出所有任务
**GET** `/api/pipeline/tasks`

响应:
```json
{
    "total": 5,
    "tasks": [
        {
            "task_id": "user_123_test_001_a1b2c3d4",
            "status": "completed",
            "created_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:10:00"
        }
    ]
}
```

### 5. 健康检查
**GET** `/health`

响应:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "tasks_count": 5
}
```

## 使用方法

### 1. 启动服务器

```bash
# 方式1：使用启动脚本
./start_api.sh

# 方式2：直接运行
python api_simple.py
```

服务器将在 http://localhost:8888 启动

### 2. 测试API

```bash
# 快速测试（不导出视频）
python test_api.py

# 完整测试（包含视频导出）
python test_api.py --with-video
```

### 3. 使用curl测试

```bash
# 提交任务
curl -X POST http://localhost:8888/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_001",
    "creator_id": "user_123",
    "gender": 1,
    "duration": 60,
    "export_video": false
  }'

# 查询状态
curl http://localhost:8888/api/pipeline/status/{task_id}

# 获取结果
curl http://localhost:8888/api/pipeline/result/{task_id}
```

### 4. 查看API文档

访问 http://localhost:8888/docs 可以查看交互式API文档（由FastAPI自动生成）

## 任务流程

1. **提交任务**: 客户端发送POST请求，获得task_id
2. **后台执行**: Pipeline在后台异步执行，依次完成各阶段
3. **状态查询**: 客户端通过task_id定期查询进度
4. **获取结果**: 任务完成后，获取YouTube元数据和视频路径

## 阶段说明

Pipeline包含以下阶段：

1. **故事二创**: 生成故事内容和YouTube元数据
2. **语音生成**: 将故事转换为语音（TTS）
3. **剪映草稿生成**: 生成剪映草稿文件
4. **视频导出**（可选）: 导出最终视频文件

## 返回数据

### YouTube元数据
从 `./story_result/{creator_id}/{video_id}/final/youtube_metadata.json` 文件读取，包含：
- title: 视频标题
- description: 视频描述
- tags: 标签列表
- category: 视频分类
- 其他YouTube相关字段

### 文件路径
- **video_path**: 导出的视频文件路径（如果启用export_video）
- **draft_path**: 剪映草稿路径
- **audio_path**: 生成的音频文件路径
- **story_path**: 故事文本文件路径

## 错误处理

- 404: 任务不存在
- 400: 任务未完成（尝试获取未完成任务的结果）
- 500: 服务器内部错误

## 性能考虑

- 任务存储在内存中，服务器重启会丢失
- 适合开发和测试环境
- 生产环境建议使用Redis或数据库存储任务状态

## 扩展性

设计保持开放性，便于后续添加：
- WebSocket/SSE实时推送
- 任务取消功能
- 批量任务提交
- 任务优先级
- 持久化存储
- 分布式任务队列（Celery）

## 注意事项

1. 默认端口为8888，可在`api_simple.py`中修改
2. 任务ID格式：`{creator_id}_{video_id}_{随机码}`
3. Pipeline执行时间较长（5-15分钟），客户端需要耐心等待
4. 建议设置合理的超时时间（默认30分钟）