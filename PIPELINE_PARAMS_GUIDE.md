# Story Full Pipeline 参数指南

## 概述

`story_full_pipeline` 支持两种工作模式：
1. **自动获取模式** - 自动获取创作者的最新未处理视频
2. **传统模式** - 手动指定视频ID

## 参数说明

### 自动获取模式 (enable_video_fetch=True)

#### 必选参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `creator_list` | List[str] | 创作者ID列表，按优先级排序 | `['UC...', '@username']` |
| `account_id` | str | 账号ID，用于音频和草稿生成 | `'yt_account_001'` |

#### 可选参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `duration` | int | 300 | 视频时长（秒） |
| `gender` | int | 1 | TTS性别（1=男声，2=女声） |
| `image_dir` | str | None | 图库目录路径 |
| `enable_subtitle` | bool | False | 是否启用字幕 |

#### 示例

```python
params = {
    'creator_list': [
        'UCH9vY_kzBKhDDrpMavKxTIQ',  # 第一优先级
        'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # 第二优先级
        '@channelhandle'             # 支持handle格式
    ],
    'account_id': 'yt_account_001',
    'duration': 300
}
```

### 传统模式 (enable_video_fetch=False)

#### 必选参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `video_id` | str | YouTube视频ID | `'dQw4w9WgXcQ'` |
| `creator_id` | str | 创作者ID | `'UC...'` |
| `account_id` | str | 账号ID | `'yt_account_001'` |

#### 可选参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `duration` | int | 300 | 视频时长（秒） |
| `gender` | int | 1 | TTS性别（1=男声，2=女声） |
| `image_dir` | str | None | 图库目录路径 |
| `enable_subtitle` | bool | False | 是否启用字幕 |

#### 示例

```python
params = {
    'video_id': 'dQw4w9WgXcQ',
    'creator_id': 'UCH9vY_kzBKhDDrpMavKxTIQ',
    'account_id': 'yt_account_001',
    'duration': 300
}
```

## Pipeline配置

### 基本配置项

```python
config = {
    # 功能开关
    'enable_video_fetch': True,   # 是否启用自动获取
    'enable_story': True,         # 是否启用故事生成
    'enable_tts': True,           # 是否启用语音生成
    'enable_draft': True,         # 是否启用草稿生成
    'enable_video_export': True,  # 是否启用视频导出
    'enable_publish': True,       # 是否启用YouTube发布
    'strict_mode': True,          # 强模式：任何失败都中断
    
    # 视频获取配置（自动获取模式）
    'video_fetch_config': {
        'days_back': 7,           # 获取最近N天的视频
        'max_videos': 10          # 每个创作者最多检查N个视频
    }
}
```

## 内部参数流转

当使用自动获取模式时，`video_fetch` 阶段会自动设置以下参数供后续阶段使用：

| 参数名 | 说明 |
|--------|------|
| `video_id` | 找到的未处理视频ID |
| `selected_creator_id` | 实际使用的创作者ID（可能不是列表中的第一个） |
| `channel_id` | YouTube频道ID |
| `channel_title` | 频道标题 |
| `video_title` | 视频标题 |
| `video_published_at` | 视频发布时间 |

## API调用示例

### 使用auto_publish系统

```python
# 1. 注册Pipeline时配置
pipeline_config = {
    "enable_video_fetch": True,
    "enable_story": True,
    "enable_tts": True,
    "enable_draft": True,
    "enable_video_export": True,
    "enable_publish": True,
    "strict_mode": True,
    "video_fetch_config": {
        "days_back": 3,
        "max_videos": 5
    }
}

# 2. API调用（自动获取模式）
POST /pipelines/execute
{
    "pipeline_type": "story_full_pipeline",
    "params": {
        "creator_list": [
            "UCH9vY_kzBKhDDrpMavKxTIQ",
            "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        ],
        "account_id": "yt_account_001",
        "duration": 300
    }
}

# 3. API调用（传统模式）
POST /pipelines/execute
{
    "pipeline_type": "story_full_pipeline",
    "params": {
        "video_id": "specific_video_id",
        "creator_id": "UCH9vY_kzBKhDDrpMavKxTIQ",
        "account_id": "yt_account_001",
        "duration": 300
    }
}
```

## 直接使用Python

```python
from pipelines.story_full_pipeline import StoryFullPipeline
import asyncio

async def run_pipeline():
    # 配置Pipeline
    config = {
        'enable_video_fetch': True,
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': True,
        'enable_publish': False,  # 测试时不发布
        'strict_mode': True,
        'video_fetch_config': {
            'days_back': 3,
            'max_videos': 5
        }
    }
    
    # 创建Pipeline实例
    pipeline = StoryFullPipeline(config)
    
    # 准备参数（自动获取模式）
    params = {
        'creator_list': [
            'UCH9vY_kzBKhDDrpMavKxTIQ',
            'UC_x5XG1OV2P6uZZ5FSM9Ttw'
        ],
        'account_id': 'yt_account_001',
        'duration': 300
    }
    
    # 执行Pipeline
    result = await pipeline.execute(params)
    
    if result['success']:
        print(f"✅ Pipeline成功完成")
        print(f"视频ID: {result['data'].get('video_id')}")
        print(f"使用创作者: {result['data'].get('selected_creator_id')}")
        if 'video_path' in result:
            print(f"生成视频: {result['video_path']}")
    else:
        print(f"❌ Pipeline失败: {result['error']}")

# 运行
asyncio.run(run_pipeline())
```

## 缓存检查逻辑

自动获取模式会检查以下位置判断视频是否已处理：

1. 故事文件: `story_result/{creator}/{video}/final/story.txt`
2. 音频文件: `output/{creator}_*_{video}_story.mp3`
3. 草稿文件: `output/drafts/{creator}_*_{video}_story/`
4. 视频文件: `output/videos/{creator}_{video}.mp4`

任何一个文件存在都表示该视频已处理。

## 注意事项

1. **creator_list优先级** - 列表中的创作者按顺序检查，找到第一个有未处理视频的即停止
2. **API配额** - 频繁调用YouTube API可能消耗配额，合理设置`days_back`和`max_videos`
3. **强模式** - `strict_mode=True`时，任何阶段失败都会立即中断整个Pipeline
4. **账号ID** - `account_id`用于生成文件名，确保同一账号的输出文件不会冲突