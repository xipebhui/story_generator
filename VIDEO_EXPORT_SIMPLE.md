# 简化的视频导出功能

## 概述

简化后的视频导出功能只需要调用剪映导出服务的API即可，不需要复杂的文件管理和路径配置。

## API接口规范

### 1. 测试接口
- **URL**: `/api/test`
- **方法**: GET
- **响应**:
```json
{
    "status": "success",
    "message": "API is working!"
}
```

### 2. 导出草稿接口
- **URL**: `/api/export_draft`
- **方法**: POST
- **请求体**:
```json
{
    "draft_name": "草稿文件夹名称"
}
```
- **成功响应**:
```json
{
    "status": "success",
    "output_path": "导出的视频文件路径"
}
```
- **错误响应**:
```json
{
    "detail": "Export failed: [错误信息]"
}
```

## 使用方法

### 1. 在 Pipeline 中使用

```bash
# 生成草稿并自动导出视频
python unified_pipeline.py --videoid VIDEO_ID --creatorid CREATOR_ID --export-video
```

### 2. 独立使用

```python
from export_video_simple import export_video

# 导出视频
draft_name = "test_draft_001"
video_path = export_video(draft_name)

if video_path:
    print(f"视频导出成功: {video_path}")
else:
    print("视频导出失败")
```

### 3. 命令行使用

```bash
# 导出指定草稿
python export_video_simple.py draft_name
```

## 环境配置

在 `.env` 文件中配置导出服务地址：

```env
# 视频导出服务URL
EXPORT_VIDEO_URL=http://localhost:8080
```

## 实现细节

### 核心函数

```python
def export_video(draft_name: str, export_url: Optional[str] = None) -> Optional[str]:
    """
    导出剪映草稿为视频
    
    Args:
        draft_name: 草稿文件夹名称
        export_url: 导出服务URL（可选）
        
    Returns:
        成功返回视频文件路径，失败返回None
    """
```

### 特点

1. **极简设计**：只有两个参数 - 草稿名称和服务URL
2. **无需路径管理**：不需要配置输出目录，由导出服务决定
3. **错误处理**：包含超时、连接错误等异常处理
4. **服务测试**：提供测试函数检查服务可用性

## 测试

运行测试脚本：

```bash
python test_export_simple.py
```

## 注意事项

1. **草稿名称**：就是生成的草稿文件夹的名称
2. **输出路径**：由导出服务决定，不能通过API控制
3. **超时时间**：默认5分钟，适合大部分视频导出
4. **服务依赖**：需要剪映导出服务（JyExport）正在运行

## 与原版本对比

| 特性 | 原版本 | 简化版 |
|-----|--------|--------|
| 代码行数 | 300+ | 100 |
| 参数数量 | 多个 | 2个 |
| 路径管理 | 需要 | 不需要 |
| 文件复制 | 需要 | 不需要 |
| 批量导出 | 支持 | 不支持 |
| 草稿信息查询 | 支持 | 不支持 |

简化版专注于核心功能，更容易维护和使用。