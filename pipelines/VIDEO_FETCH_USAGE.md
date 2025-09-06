# 视频自动获取功能使用指南

## 功能概述

`story_full_pipeline` 现在支持自动获取创作者的最新未处理视频，无需手动指定 `video_id`。这个功能通过新增的 `video_fetch` 预处理阶段实现。

## 主要特性

1. **自动获取最新视频** - 只需提供 `creator_id`，系统自动获取最新视频
2. **智能缓存检查** - 自动检查视频是否已处理，避免重复处理
3. **多创作者备选** - 支持配置多个创作者，当主创作者无新视频时自动切换
4. **灵活配置** - 可以启用或禁用此功能，保持向后兼容性

## 使用方式

### 1. 启用自动获取模式

```python
from pipelines.story_full_pipeline import StoryFullPipeline

config = {
    'enable_video_fetch': True,  # 启用自动获取
    'enable_story': True,
    'enable_tts': True,
    'enable_draft': True,
    'enable_video_export': True,
    'enable_publish': True,
    'strict_mode': True,
    
    'video_fetch_config': {
        'creator_list': [
            'UCH9vY_kzBKhDDrpMavKxTIQ',  # 主创作者
            'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # 备选创作者1
        ],
        'days_back': 7,      # 获取最近7天的视频
        'max_videos': 10     # 最多检查10个视频
    }
}

pipeline = StoryFullPipeline(config)

# 只需要提供creator_id
params = {
    'creator_id': 'UCH9vY_kzBKhDDrpMavKxTIQ',
    'account_id': 'yt_account_001'
}

result = await pipeline.execute(params)
```

### 2. 传统模式（向后兼容）

```python
config = {
    'enable_video_fetch': False,  # 禁用自动获取
    'enable_story': True,
    'enable_tts': True,
    'enable_draft': True,
    'enable_video_export': True,
    'enable_publish': False,
    'strict_mode': True
}

pipeline = StoryFullPipeline(config)

# 必须提供video_id
params = {
    'video_id': 'specific_video_id',
    'creator_id': 'test_creator',
    'account_id': 'test_account'
}

result = await pipeline.execute(params)
```

## 配置说明

### video_fetch_config 参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| creator_list | List[str] | [creator_id] | 创作者ID列表，按顺序尝试 |
| days_back | int | 7 | 获取多少天内的视频 |
| max_videos | int | 10 | 每个创作者最多检查的视频数 |

## 工作流程

1. **获取频道详情**
   - 通过 `creator_id` 获取 YouTube 频道信息
   - 支持 channel_id（UC开头）或 handle（@username）

2. **获取最新活动**
   - 使用 YouTube API 的 `activities.list` 方法
   - 获取指定时间范围内的上传视频

3. **缓存检查**
   - 检查多个缓存位置判断视频是否已处理：
     - 故事文件：`story_result/{creator}/{video}/final/story.txt`
     - 音频文件：`output/{creator}_*_{video}_story.mp3`
     - 草稿文件：`output/drafts/{creator}_*_{video}_story`
     - 视频文件：`output/videos/{creator}_{video}.mp4`

4. **备选机制**
   - 如果主创作者没有未处理的视频，自动尝试列表中的下一个创作者
   - 继续直到找到未处理的视频或遍历完所有创作者

## API 集成

在 `auto_publish` 系统中使用：

```python
# 注册Pipeline时的配置
config = {
    "enable_video_fetch": True,
    "video_fetch_config": {
        "creator_list": ["creator1", "creator2"],
        "days_back": 3,
        "max_videos": 5
    },
    "enable_story": True,
    "enable_tts": True,
    "enable_draft": True,
    "enable_video_export": True,
    "enable_publish": True,
    "strict_mode": True
}

# API调用时只需提供creator_id
POST /pipelines/execute
{
    "pipeline_type": "story_full_pipeline",
    "params": {
        "creator_id": "UCH9vY_kzBKhDDrpMavKxTIQ",
        "account_id": "yt_account_001"
    }
}
```

## 测试

运行测试脚本验证功能：

```bash
# 测试视频获取功能
python test_video_fetch.py

# 测试完整Pipeline（带自动获取）
python pipelines/story_full_pipeline.py
```

## 注意事项

1. **API 配额** - 频繁调用 YouTube API 可能消耗配额，建议合理设置 `days_back` 和 `max_videos`

2. **缓存策略** - 系统依赖文件缓存判断视频是否已处理，确保缓存文件不被意外删除

3. **错误处理** - 如果所有创作者都没有未处理的视频，Pipeline 会返回错误

4. **强模式** - 在 `strict_mode=True` 时，视频获取失败会立即中断整个 Pipeline

## 示例输出

成功获取视频时的输出：
```json
{
    "success": true,
    "data": {
        "video_id": "abc123xyz",
        "creator_id": "UCH9vY_kzBKhDDrpMavKxTIQ",
        "channel_id": "UCH9vY_kzBKhDDrpMavKxTIQ",
        "channel_title": "Example Channel",
        "video_fetch": {
            "video_info": {
                "title": "Latest Video Title",
                "published_at": "2024-01-10T12:00:00Z",
                "view_count": 10000
            }
        }
    }
}
```