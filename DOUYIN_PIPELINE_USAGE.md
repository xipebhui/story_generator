# 抖音视频下载发布Pipeline使用指南

## 概述
这个Pipeline实现了从抖音自动下载视频并发布到YouTube的完整流程。

## 功能特点
- ✅ 批量获取抖音创作者的最新视频
- ✅ 自动去重，避免重复处理
- ✅ 下载无水印视频和封面图片
- ✅ 自动发布到YouTube
- ✅ 支持多阶段独立测试

## Pipeline配置

### 基础配置（config）
```python
config = {
    "api_base_url": "http://localhost:51084",  # API服务地址
    "max_videos_per_creator": 1,               # 默认每个创作者获取的视频数
    "storage_base_path": "outputs/douyin_videos",  # 视频存储路径
    "cache_dir": "outputs/douyin_cache",        # 缓存目录（用于去重）
    "download_timeout": 300                     # 下载超时时间（秒）
}
```

### 执行参数（params）
```python
params = {
    "creator_ids": ["CREATOR_ID_1", "CREATOR_ID_2"],  # 创作者ID列表（必需）
    "account_id": "YOUR_YOUTUBE_ACCOUNT",              # YouTube账号ID（必需）
    "max_videos_per_creator": 2                        # 覆盖配置中的默认值（可选）
}
```

## 测试工具使用

### 1. 测试获取视频信息
```bash
# 基础测试
python test_douyin_pipeline.py --mode fetch

# 显示详细日志
python test_douyin_pipeline.py --mode fetch --verbose
```

### 2. 测试视频下载
```bash
# 下载1个视频
python test_douyin_pipeline.py --mode download

# 下载多个视频
python test_douyin_pipeline.py --mode download --max-videos 3
```

### 3. 测试完整流程（包含发布）
```bash
# 使用真实的YouTube账号ID
python test_douyin_pipeline.py --mode publish --account-id YOUR_YOUTUBE_ACCOUNT_ID

# 带详细日志
python test_douyin_pipeline.py --mode publish --account-id YOUR_ACCOUNT --verbose
```

## 在生产环境中使用

### 方式一：直接调用Pipeline
```python
import asyncio
from pipelines.douyin_download_publish_pipeline import DouyinDownloadPublishPipeline

async def main():
    # 创建Pipeline实例
    pipeline = DouyinDownloadPublishPipeline({
        "api_base_url": "http://localhost:51084",
        "max_videos_per_creator": 3,
        "storage_base_path": "outputs/douyin_videos",
        "cache_dir": "outputs/douyin_cache"
    })
    
    # 执行Pipeline
    result = await pipeline.execute({
        "creator_ids": ["CREATOR_ID_1", "CREATOR_ID_2"],
        "account_id": "YOUR_YOUTUBE_ACCOUNT",
        "max_videos_per_creator": 5  # 可选：覆盖默认值
    })
    
    # 处理结果
    if result['success']:
        print(f"成功处理 {result['data']['total_processed']} 个视频")
        print(f"下载成功: {result['data']['total_downloaded']}")
        print(f"发布成功: {result['data']['total_published']}")
    else:
        print(f"执行失败: {result['error']}")

asyncio.run(main())
```

### 方式二：通过Pipeline注册系统
```python
from pipeline_registry import PipelineRegistry

# 获取注册表
registry = PipelineRegistry()

# 获取Pipeline
pipeline_info = registry.get_pipeline('douyin_download_publish')
pipeline_class = pipeline_info['class']

# 创建实例并执行
pipeline = pipeline_class(config)
result = await pipeline.execute(params)
```

## 执行流程

### 阶段1：获取视频信息
1. 遍历creator_ids列表
2. 调用API获取每个创作者的最新视频
3. 检查视频是否已处理（去重）
4. 返回未处理的视频列表

### 阶段2：下载媒体文件
1. 为每个视频创建存储目录
2. 下载视频文件（无水印）
3. 下载封面图片
4. 创建缓存标记文件

### 阶段3：发布到YouTube
1. 创建Pipeline任务记录
2. 调用publish_service创建发布任务
3. 执行YouTube上传
4. 记录发布结果

## 去重机制

Pipeline会检查以下位置判断视频是否已处理：
1. 缓存标记文件：`cache_dir/{creator_id}_{aweme_id}.done`
2. 下载的视频文件：`storage_base/{creator_id}/{aweme_id}/{aweme_id}.mp4`
3. 发布记录文件：`cache_dir/published_{aweme_id}.json`

## 目录结构
```
outputs/
├── douyin_videos/              # 视频存储目录
│   ├── {creator_id}/
│   │   └── {aweme_id}/
│   │       ├── {aweme_id}.mp4         # 视频文件
│   │       └── {aweme_id}_cover.jpg   # 封面图片
└── douyin_cache/               # 缓存目录
    ├── {creator_id}_{aweme_id}.done   # 下载完成标记
    └── published_{aweme_id}.json      # 发布记录

```

## 错误处理

Pipeline包含完善的错误处理机制：
- 参数验证失败会立即返回错误
- 单个视频处理失败不影响其他视频
- 每个阶段独立记录成功/失败状态
- 详细的日志记录便于调试

## 性能优化

- 使用aiohttp异步HTTP请求
- 批量处理视频
- 缓存机制避免重复处理
- 可配置的超时设置

## 注意事项

1. **API服务**：确保抖音API服务正在运行（默认端口51084）
2. **YouTube账号**：需要配置真实的YouTube账号ID才能发布
3. **存储空间**：确保有足够的磁盘空间存储视频
4. **网络连接**：下载大文件需要稳定的网络连接
5. **去重检查**：Pipeline会自动跳过已处理的视频

## 常见问题

### Q: 为什么获取到0个视频？
A: 可能原因：
- 所有视频都已被处理（检查缓存目录）
- API返回数据格式变化
- 创作者ID无效

### Q: 下载失败怎么办？
A: 检查：
- API服务是否正常运行
- 网络连接是否稳定
- 存储路径权限是否正确

### Q: 发布失败怎么办？
A: 确认：
- YouTube账号ID是否正确
- publish_service是否正常运行
- 数据库连接是否正常

## 扩展功能

可以通过修改Pipeline添加以下功能：
- 视频标题/描述自定义
- 批量处理优化
- 定时任务支持
- 更多平台支持