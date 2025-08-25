# 视频导出功能配置说明

## 功能概述
视频导出功能已集成到 Pipeline 中，可以在生成剪映草稿后自动将其导出为 MP4 视频文件。

## 环境变量配置

所有配置都在 `.env` 文件中管理。请复制 `.env.example` 并重命名为 `.env`，然后修改相应的配置值。

### 主要配置项

1. **DRAFT_LOCAL_DIR**
   - 说明：剪映草稿本地存储目录
   - 默认值：`test`（相对路径）或 `./final_drafts/jianying`
   - 示例：`DRAFT_LOCAL_DIR=/path/to/jianying/drafts`

2. **DRAFT_ONLINE_DIR**
   - 说明：在线草稿信息目录
   - 默认值：`./final_drafts/online`
   - 示例：`DRAFT_ONLINE_DIR=/path/to/online/drafts`

3. **VIDEO_OUTPUT_DIR**
   - 说明：视频输出目录
   - 默认值：`./output/videos`
   - 示例：`VIDEO_OUTPUT_DIR=/path/to/output/videos`

4. **EXPORT_VIDEO_URL**
   - 说明：视频导出服务的API地址
   - 默认值：`http://localhost:8080/api/export_draft`
   - 示例：`EXPORT_VIDEO_URL=http://your-export-server:8080/api/export_draft`

5. **LOG_LEVEL**
   - 说明：日志级别
   - 默认值：`INFO`
   - 可选值：`DEBUG`, `INFO`, `WARNING`, `ERROR`
   - 示例：`LOG_LEVEL=DEBUG`

### 配置示例 (.env 文件)

```env
# 草稿和输出目录配置
DRAFT_LOCAL_DIR=/Users/username/jianying/drafts
DRAFT_ONLINE_DIR=/Users/username/jianying/online
VIDEO_OUTPUT_DIR=/Users/username/output/videos

# 视频导出服务配置
EXPORT_VIDEO_URL=http://localhost:8080/api/export_draft

# 日志配置
LOG_LEVEL=INFO
```

## 使用方法

### 1. 基本用法 - 生成草稿但不导出视频
```bash
python unified_pipeline.py --videoid VIDEO_ID --creatorid CREATOR_ID
```

### 2. 生成草稿并导出视频
```bash
python unified_pipeline.py --videoid VIDEO_ID --creatorid CREATOR_ID --export-video
```

### 3. 独立导出已有草稿
```bash
# 导出单个草稿
python export_video.py draft_id

# 导出到指定目录
python export_video.py draft_id --output-dir /path/to/output

# 批量导出
python export_video.py draft_1 draft_2 draft_3 --batch

# 查看草稿信息
python export_video.py draft_id --info
```

## 视频导出服务 API 规范

导出服务需要实现以下 API 接口：

### 请求
- **URL**: `POST /api/export_draft`
- **Content-Type**: `application/json`
- **请求体**:
```json
{
    "draft_id": "草稿ID",
    "export_format": "mp4",
    "quality": "high",
    "timestamp": 1755984000
}
```

### 响应
- **成功响应** (HTTP 200):
```json
{
    "status": "success",
    "video_path": "/path/to/exported/video.mp4"
}
```

- **失败响应** (HTTP 200/400/500):
```json
{
    "status": "failed",
    "error": "错误信息"
}
```

## 文件结构

### 草稿目录结构
```
final_drafts/
├── jianying/                  # 剪映草稿存储目录
│   └── draft_id/              # 单个草稿目录
│       ├── draft_meta_info.json
│       ├── draft_content.json
│       └── materials/         # 材料文件目录
│           ├── audio_1.mp3
│           ├── image_1.jpg
│           └── subtitle.srt
└── online/                    # 在线草稿信息目录
    └── draft_id_request.json
```

### 输出视频目录
```
output/
└── videos/
    └── creator_id/           # 按创作者ID分类
        └── video_file.mp4     # 导出的视频文件
```

## 测试

运行测试脚本验证功能：
```bash
python test_export_video.py
```

测试包括：
- 获取草稿信息
- 模拟视频导出
- 导出到指定目录
- 批量导出
- 错误处理

## 注意事项

1. **导出服务依赖**：视频导出功能需要外部的导出服务支持，确保导出服务正在运行并可访问。

2. **草稿文件完整性**：确保草稿目录包含必需的文件：
   - `draft_meta_info.json`
   - `draft_content.json`
   - 材料文件（音频、图片、字幕等）

3. **超时设置**：视频导出可能需要较长时间，当前设置的超时时间为 5 分钟。

4. **错误处理**：视频导出失败不会影响整个 Pipeline 流程，只会记录警告日志。

5. **磁盘空间**：确保有足够的磁盘空间存储导出的视频文件。

## 常见问题

### Q: 导出服务连接失败
A: 检查 `EXPORT_VIDEO_URL` 环境变量是否正确设置，并确保导出服务正在运行。

### Q: 草稿文件找不到
A: 确保草稿已经成功生成，并且路径配置正确。检查 `DRAFT_LOCAL_DIR` 环境变量。

### Q: 导出超时
A: 可能是视频太长或服务器性能问题。可以尝试：
   - 增加超时时间（修改 `http_utils.py` 中的 timeout 参数）
   - 优化导出服务性能
   - 减少视频时长

### Q: 批量导出失败
A: 批量导出会逐个处理草稿，单个失败不影响其他草稿。检查失败的具体原因。