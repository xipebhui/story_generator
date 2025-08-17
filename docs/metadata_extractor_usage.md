# YouTube元数据提取器使用指南

## 📋 功能概述

提供了两个独立的Python脚本，用于提取YouTube视频的元数据信息：

1. **youtube_metadata_extractor.py** - 单个视频元数据提取器
2. **batch_metadata_extractor.py** - 批量视频元数据提取器

## 🎯 提取的数据

- **视频基本信息**：标题、描述、频道、发布时间、时长
- **统计数据**：观看数、点赞数、评论数
- **评论内容**：热门评论及其点赞数、作者信息
- **字幕内容**：完整字幕文本（支持多语言）
- **缩略图**：各种分辨率的缩略图URL
- **标签**：视频标签列表

## 🚀 快速开始

### 1. 单个视频提取

```bash
# 基本用法
python youtube_metadata_extractor.py VIDEO_ID

# 示例：提取特定视频
python youtube_metadata_extractor.py dQw4w9WgXcQ

# 指定输出目录
python youtube_metadata_extractor.py VIDEO_ID -o /path/to/output

# 强制刷新（忽略缓存）
python youtube_metadata_extractor.py VIDEO_ID -f

# 指定评论数量和字幕语言
python youtube_metadata_extractor.py VIDEO_ID -c 50 -l en

# 生成报告
python youtube_metadata_extractor.py VIDEO_ID -r
```

### 2. 批量视频提取

```bash
# 从命令行传入多个视频ID
python batch_metadata_extractor.py -v VIDEO_ID1 VIDEO_ID2 VIDEO_ID3

# 从文件读取视频ID列表
python batch_metadata_extractor.py -f video_list.txt

# 自定义输出目录和延迟
python batch_metadata_extractor.py -f video_list.txt -o output_dir -d 3

# 强制刷新所有数据
python batch_metadata_extractor.py -f video_list.txt -r
```

### 3. 视频列表文件格式

创建一个文本文件（如 `video_list.txt`），每行一个视频ID或URL：

```text
# 这是注释，会被忽略
dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0
https://youtu.be/kJQP7kiw5Fk
# 支持多种格式
jNQXAC9IVRw
```

## 📁 输出文件结构

### 单个视频输出
```
metadata/
└── VIDEO_ID/
    ├── video_info.json        # 视频基本信息
    ├── comments.json          # 评论列表
    ├── subtitle_zh.txt        # 中文字幕（纯文本）
    ├── subtitle_zh.json       # 中文字幕（带时间戳）
    ├── subtitle_en.txt        # 英文字幕（如果有）
    ├── metadata_complete.json # 完整元数据
    └── metadata_report.md     # 摘要报告
```

### 批量提取输出
```
batch_metadata/
└── batch_20240101_120000/
    ├── VIDEO_ID1/            # 第一个视频的数据
    │   └── ...
    ├── VIDEO_ID2/            # 第二个视频的数据
    │   └── ...
    ├── batch_results.json    # 批次结果汇总
    └── batch_report.md       # 批次报告
```

## 💻 Python代码调用

### 单个视频提取

```python
from youtube_metadata_extractor import YouTubeMetadataExtractor

# 创建提取器
extractor = YouTubeMetadataExtractor(
    video_id="dQw4w9WgXcQ",
    output_dir="output/video1"
)

# 提取所有元数据
metadata = extractor.extract_all_metadata()

# 或者分别提取
video_info = extractor.extract_video_info()
comments = extractor.extract_comments(max_results=50)
subtitle = extractor.extract_subtitle(language='zh')

# 生成报告
report = extractor.generate_summary_report(metadata)
```

### 批量提取

```python
from batch_metadata_extractor import BatchMetadataExtractor

# 创建批量提取器
batch_extractor = BatchMetadataExtractor(output_base_dir="batch_output")

# 从列表提取
video_ids = ["VIDEO_ID1", "VIDEO_ID2", "VIDEO_ID3"]
results = batch_extractor.extract_from_list(
    video_ids=video_ids,
    force_refresh=False,
    delay_seconds=2
)

# 或从文件提取
results = batch_extractor.extract_from_file(
    file_path="video_list.txt",
    force_refresh=False,
    delay_seconds=2
)

# 检查结果
for result in results:
    if result['status'] == 'success':
        print(f"✅ {result['video_id']}: {result['metadata']['video_info']['title']}")
    else:
        print(f"❌ {result['video_id']}: {result['error']}")
```

## 🔧 高级功能

### 1. 缓存机制

- 所有提取的数据都会缓存到本地文件
- 再次运行时会自动使用缓存（除非使用 `-f` 强制刷新）
- 缓存可以大大减少API调用次数

### 2. 错误处理

- 自动处理API限制和网络错误
- 失败的视频不会影响批量任务的其他视频
- 详细的错误日志便于调试

### 3. 自定义扩展

可以轻松扩展提取器添加新功能：

```python
class CustomExtractor(YouTubeMetadataExtractor):
    def extract_custom_data(self):
        # 添加自定义提取逻辑
        pass
```

## 📊 数据分析示例

提取的数据可以用于各种分析：

```python
import json
import pandas as pd

# 加载批次结果
with open('batch_metadata/batch_xxx/batch_results.json', 'r') as f:
    data = json.load(f)

# 转换为DataFrame
df = pd.DataFrame(data)

# 分析观看数最多的视频
top_videos = df.nlargest(10, 'views')[['title', 'channel', 'views', 'likes']]

# 计算平均互动率
df['engagement_rate'] = (df['likes'] + df['comments_count']) / df['views'] * 100

# 找出字幕最长的视频
longest_subtitle = df.nlargest(5, 'subtitle_length')[['title', 'subtitle_length']]
```

## ⚠️ 注意事项

1. **API限制**：YouTube API有配额限制，批量提取时建议设置合适的延迟
2. **字幕可用性**：不是所有视频都有字幕，特别是自动生成的字幕
3. **隐私设置**：私密或已删除的视频无法提取
4. **网络要求**：需要稳定的网络连接

## 🔑 API密钥配置

默认使用内置的API密钥，但建议使用自己的密钥：

```bash
# 设置环境变量
export YOUTUBE_API_KEY="your_api_key_here"

# 或在代码中设置
os.environ['YOUTUBE_API_KEY'] = "your_api_key_here"
```

## 📝 输出示例

### 元数据报告示例

```markdown
# YouTube视频元数据报告

## 📌 基本信息
- **视频ID**: dQw4w9WgXcQ
- **标题**: Rick Astley - Never Gonna Give You Up
- **频道**: Rick Astley
- **发布时间**: 2009-10-25T06:57:33Z
- **时长**: PT3M33S

## 📊 统计数据
- **观看次数**: 1,234,567,890
- **点赞数**: 12,345,678
- **评论数**: 1,234,567

## 💬 热门评论 (Top 5)
1. **User1** (👍 12345)
   > This is the best song ever!

...
```

## 🤝 贡献和反馈

如有问题或建议，欢迎提出！