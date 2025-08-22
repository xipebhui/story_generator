# 优化版图片生成流程说明

## 概述
新的图片生成流程（v2）优化了以下几个方面：
1. 从框架中提取角色特征，保持视觉一致性
2. 从每个segment内容中智能提取关键场景
3. 结合角色特征生成更精准的SD提示词
4. 支持每个segment生成多张图片

## 主要功能

### 1. 角色特征提取
- 从框架文档的"核心角色视觉设计"部分提取角色信息
- 提取视觉描述和SD友好的特征关键词
- 确保所有图片中角色外观的一致性

### 2. 场景提取
- 使用AI从每个segment内容中提取最具视觉冲击力的场景
- 提取场景描述、情感氛围、关键元素和色调
- 根据`images_per_segment`参数控制提取数量

### 3. SD提示词生成
- 结合角色特征和场景信息生成专业的SD提示词
- 包含正面提示词和负面提示词
- 自动添加风格标签，确保图片质量

## 使用方法

### 命令行参数
```bash
python youtube_story_creator_v2.py <video_id> <creator_name> [options]

选项：
  --segments N            片段数量（默认9）
  --images-per-segment N  每个片段生成的图片数量（默认1）
  --length N             目标故事长度（默认30000）
```

### 示例
```bash
# 每个片段生成2张图片
python youtube_story_creator_v2.py abc123 my_creator --images-per-segment 2

# 生成9个片段，每段3张图片
python youtube_story_creator_v2.py abc123 my_creator --segments 9 --images-per-segment 3
```

## 输出格式

### JSON格式 (sd_prompts_v2.json)
```json
{
  "character_profiles": {
    "角色名": {
      "name": "角色名",
      "visual_description": "视觉描述",
      "sd_features": "SD特征关键词"
    }
  },
  "total_images": 总图片数,
  "images": [
    {
      "segment": 片段编号,
      "scene_index": 场景索引,
      "scene_description": "场景描述",
      "emotion": "情感氛围",
      "sd_prompt": {
        "positive": "正面提示词",
        "negative": "负面提示词"
      }
    }
  ]
}
```

### Markdown格式 (sd_prompts_v2.md)
人类可读的格式，包含：
- 角色特征描述
- 每个场景的详细信息
- 格式化的SD提示词

## 技术细节

### 方法概览
- `generate_image_prompts_v2()`: 主方法，协调整个流程
- `extract_character_profiles()`: 从框架提取角色特征
- `extract_key_scenes_from_segment()`: 从segment提取场景
- `generate_sd_prompt_for_scene()`: 为场景生成SD提示词
- `save_prompts_as_markdown()`: 保存为Markdown格式

### 优化点
1. **角色一致性**：通过提取和复用角色特征，确保不同图片中角色外观一致
2. **智能场景提取**：使用AI理解文本内容，提取最具表现力的画面
3. **灵活配置**：支持动态调整每个片段的图片数量
4. **双格式输出**：JSON供程序使用，Markdown供人类阅读

## 测试
运行测试脚本验证功能：
```bash
python test_image_generation_v2.py
```

测试包括：
- 角色特征提取测试
- 场景提取测试
- SD提示词生成测试
- 完整流程测试