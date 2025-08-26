# YouTube 视频上传接口集成说明

## 概述
本系统已集成真实的 YouTube 批量上传 API，支持通过比特浏览器 Profile 上传视频到 YouTube。

## 真实 API 接口定义

### 上传端点
- **URL**: `POST /api/upload`
- **功能**: 批量上传视频到 YouTube

### 请求格式
```json
{
  "tasks": [
    {
      "profileId": "string",  // 比特浏览器 Profile ID
      "video": {
        "uid": "string",       // 任务唯一标识符
        "path": "string",      // 视频文件路径
        "title": "string",     // 视频标题
        "description": "string", // 视频描述
        "tags": ["string"],    // 标签数组
        "visibility": "string", // 可见性 (public/unlisted/private)
        "thumbnail": "string"   // 缩略图路径（可选）
      }
    }
  ]
}
```

### 响应格式
```json
{
  "success": true,
  "totalTasks": 1,
  "successCount": 1,
  "failCount": 0,
  "executionTime": 45.67,
  "results": [
    {
      "uid": "string",
      "status": "SUCCESS",  // SUCCESS 或 FAIL
      "url": "https://youtu.be/videoId",
      "error": "string",    // 失败时的错误信息
      "profileId": "string",
      "executionTime": 15.23
    }
  ]
}
```

## 系统集成实现

### 1. 请求构建 (`publish_service.py`)
```python
# 构建符合真实 API 格式的请求
upload_request = {
    'tasks': [
        {
            'profileId': account['profile_id'],
            'video': {
                'uid': publish_id,
                'path': publish_task.video_path,
                'title': publish_task.video_title,
                'description': publish_task.video_description,
                'tags': json.loads(publish_task.video_tags),
                'visibility': publish_task.privacy_status,
                'thumbnail': publish_task.thumbnail_path  # 如果有
            }
        }
    ]
}
```

### 2. 响应处理
- 检查 `status` 字段是否为 "SUCCESS"
- 从 `url` 字段提取 YouTube 视频 ID
- 保存上传结果到数据库

### 3. 缩略图处理

#### 上传缩略图端点
- **URL**: `POST /api/publish/upload-thumbnail`
- **功能**: 上传缩略图文件到服务器

#### 请求格式
- **Content-Type**: `multipart/form-data`
- **参数**:
  - `task_id`: 任务 ID
  - `file`: 图片文件

#### 缩略图存储
- **存储目录**: `thumbnails/`
- **文件命名**: `{task_id}_{timestamp}.{ext}`
- **支持格式**: JPEG, PNG, WebP
- **文件大小限制**: 最大 2MB
- **路径处理**: 
  - 上传接口返回**绝对路径**用于发布
  - 同时返回相对路径供参考
  - 数据库保存绝对路径

#### 使用流程
1. 用户通过 `/api/publish/upload-thumbnail` 上传缩略图
2. 系统保存文件到 `thumbnails/` 目录
3. 更新任务记录的 `thumbnail_path` 字段
4. 发布时自动包含缩略图路径

## 配置要求

### 环境变量
```bash
# YouTube 上传服务地址
YTENGINE_HOST=http://localhost:51077

# 使用真实上传（设为 false）
USE_MOCK_UPLOAD=false
```

### 账号配置
每个账号需要配置：
- `profile_id`: 比特浏览器的 Profile ID
- `account_name`: 账号名称（用于识别）
- `status`: 账号状态（active/inactive）

## 发布流程

### 1. 创建发布任务
```bash
POST /api/publish/schedule
{
  "task_id": "pipeline_task_id",
  "account_ids": ["account_001"],
  "video_title": "视频标题",
  "video_description": "视频描述",
  "video_tags": ["tag1", "tag2"],
  "thumbnail_path": "thumbnails/xxx.jpg",  # 可选
  "privacy_status": "public"
}
```

### 2. 系统处理流程
1. 创建发布任务记录
2. 获取视频文件路径
3. 获取账号的 profile_id
4. 构建上传请求
5. 调用真实 YouTube API
6. 解析响应结果
7. 更新任务状态

### 3. 状态跟踪
- **pending**: 待发布
- **uploading**: 上传中
- **success**: 上传成功
- **failed**: 上传失败

## 注意事项

1. **视频文件路径**: 必须是绝对路径，且文件必须存在
2. **缩略图路径**: 可选，但建议提供以获得更好的展示效果
3. **Profile ID**: 必须是有效的比特浏览器 Profile ID
4. **网络超时**: 上传大文件时可能需要较长时间，默认超时 10 分钟
5. **错误处理**: 
   - API 返回 `status: "FAIL"` 时会记录错误信息
   - 网络错误会自动重试（根据配置）
   - 所有错误都会记录到日志

## API 测试

### 测试上传（使用 curl）
```bash
# 1. 上传缩略图（返回绝对路径）
curl -X POST http://localhost:51082/api/publish/upload-thumbnail \
  -F "task_id=test_task_001" \
  -F "file=@/path/to/thumbnail.jpg"

# 响应示例:
# {
#   "message": "缩略图上传成功",
#   "thumbnail_path": "/Users/xxx/workspace/youtube/story_generator/thumbnails/test_task_001_20241201_120000.jpg",
#   "relative_path": "thumbnails/test_task_001_20241201_120000.jpg",
#   "filename": "test_task_001_20241201_120000.jpg",
#   "size": 102400
# }

# 2. 创建发布任务（使用绝对路径）
curl -X POST http://localhost:51082/api/publish/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test_task_001",
    "account_ids": ["account_001"],
    "video_title": "测试视频",
    "video_description": "这是一个测试视频",
    "video_tags": ["test", "demo"],
    "thumbnail_path": "/Users/xxx/workspace/youtube/story_generator/thumbnails/test_task_001_20241201_120000.jpg",
    "privacy_status": "unlisted"
  }'
```

## 故障排查

### 常见问题

1. **上传失败 - Profile ID 无效**
   - 检查账号配置中的 profile_id 是否正确
   - 确认比特浏览器中该 Profile 存在且已登录 YouTube

2. **缩略图不显示**
   - 检查缩略图文件路径是否正确
   - 确认文件格式符合要求（JPEG/PNG/WebP）
   - 文件大小不超过 2MB

3. **视频文件找不到**
   - 确认视频导出成功
   - 检查 video_path 是否为绝对路径
   - 验证文件权限

4. **上传超时**
   - 检查网络连接
   - 确认 YouTube 上传服务正在运行
   - 考虑增加超时时间（针对大文件）

## 更新日志

### 2024-12-XX
- 实现真实 YouTube API 对接
- 添加缩略图上传功能
- 优化错误处理和日志记录
- 支持批量上传（虽然目前每次只发一个任务）