# YouTube元数据生成指南

## 概述

V3 Pipeline新增了专门的YouTube元数据生成步骤，能够生成完整的双语版本发布建议，包括标题、描述、标签、缩略图设计和发布策略。

## 功能特点

### 1. 双语支持
- 中文和英文版本的标题、描述、标签
- 适配不同语言市场的优化建议

### 2. 全方位覆盖
- **标题优化** - 3种不同风格的标题
- **描述文案** - SEO优化的视频描述
- **标签系统** - 混合语言标签策略
- **缩略图设计** - 视觉和文字建议
- **发布策略** - 时间、受众、互动策略

### 3. 智能生成
- 基于故事内容自动分析
- 从Framework V3提取关键信息
- 考虑YouTube算法偏好

## 生成的文件

执行Pipeline后，会在`final/`目录生成两个文件：

### 1. `youtube_metadata.json`
结构化的JSON数据，便于程序读取：

```json
{
  "titles": {
    "chinese": ["中文标题1", "中文标题2", "中文标题3"],
    "english": ["English Title 1", "English Title 2", "English Title 3"]
  },
  "descriptions": {
    "chinese": "中文描述...",
    "english": "English description..."
  },
  "tags": {
    "chinese": ["标签1", "标签2"],
    "english": ["tag1", "tag2"],
    "mixed": ["混合标签"]
  },
  "thumbnail": {
    "visual_focus": "视觉焦点描述",
    "text_overlay": {
      "chinese": "中文文字",
      "english": "English text"
    },
    "color_scheme": "配色方案",
    "emotion": "情绪表达"
  },
  "strategy": {
    "publish_time": "最佳发布时间",
    "target_audience": "目标受众",
    "first_48_hours": ["策略1", "策略2"],
    "community_posts": ["帖子创意1", "帖子创意2"]
  }
}
```

### 2. `youtube_metadata.md`
人类可读的Markdown格式：

```markdown
# YouTube发布建议 / YouTube Publishing Guide

## 📝 标题建议 / Title Suggestions

### 中文标题
1. 【震撼】这个故事改变了100万人
2. 30分钟看完一生的转折
3. 你绝对想不到的结局

### English Titles
1. The Story That Changed Everything
2. 30 Minutes That Will Transform Your Life
3. You Won't Believe How This Ends

[... 更多内容 ...]
```

## 使用方法

### 1. 自动生成
Pipeline会自动执行YouTube元数据生成步骤：

```bash
python story_pipeline_v3_runner.py VIDEO_ID
```

生成的文件位置：
```
story_result/
└── [creator]/[video_id]/
    └── final/
        ├── youtube_metadata.json  # 结构化数据
        └── youtube_metadata.md    # 可读文档
```

### 2. 查看结果

查看可读版本：
```bash
cat story_result/[creator]/[video_id]/final/youtube_metadata.md
```

程序化读取：
```python
import json

with open('story_result/[creator]/[video_id]/final/youtube_metadata.json', 'r', encoding='utf-8') as f:
    metadata = json.load(f)
    
# 使用中文标题
cn_titles = metadata['titles']['chinese']
# 使用英文标签
en_tags = metadata['tags']['english']
```

## 优化建议

### 1. 标题优化策略

生成的三种标题类型：

1. **数字/震撼型**
   - 使用具体数字
   - 制造认知反差
   - 例：`3秒决定改变了300万人的命运`

2. **疑问/好奇型**
   - 提出引人深思的问题
   - 留下悬念
   - 例：`为什么99%的人会做出同样的选择？`

3. **利益/价值型**
   - 明确观看收益
   - 承诺转变
   - 例：`看完这个，你将重新理解成功`

### 2. 描述文案要点

- **前125字符** - YouTube搜索结果中显示的部分，必须极具吸引力
- **故事简介** - 2-3句话概括，不剧透
- **讨论问题** - 3-5个引导评论的问题
- **时间戳** - 预留位置添加章节时间戳

### 3. 标签策略

- **广泛标签** - 大类别标签，如"故事"、"story"
- **具体标签** - 细分标签，如"真实故事改编"
- **趋势标签** - 当前热门相关标签
- **混合语言** - 扩大覆盖范围

### 4. 缩略图设计

系统会提供：
- **视觉焦点** - 主要视觉元素描述
- **文字叠加** - 双语版本的标题文字
- **配色建议** - 基于情感的色彩方案
- **表情指导** - 人物表情或情绪建议

### 5. 发布策略

包含：
- **最佳时间** - 基于目标受众的发布时间
- **受众定位** - 年龄、兴趣等人口统计
- **48小时策略** - 关键推广期的互动策略
- **社区运营** - Community帖子创意

## 自定义调整

### 修改生成逻辑

如果需要调整生成策略，编辑`pipeline_steps_youtube_metadata.py`中的提示词：

```python
def _generate_metadata(self, input_data: Dict) -> Dict:
    prompt = """
    # 在这里修改提示词来调整生成策略
    You are a YouTube content optimization expert...
    """
```

### 添加新字段

在JSON结构中添加新字段：

```python
# 在_generate_metadata方法的prompt中添加
"custom_field": {
    "new_data": "...",
    "more_info": "..."
}
```

### 本地化调整

针对特定市场调整：

```python
# 添加更多语言版本
"titles": {
    "chinese": [...],
    "english": [...],
    "japanese": [...],  # 新增日文
    "korean": [...]     # 新增韩文
}
```

## 最佳实践

### 1. A/B测试
- 使用不同的标题版本
- 监控点击率差异
- 选择表现最好的版本

### 2. 定期更新
- 根据YouTube算法变化调整策略
- 跟踪热门标签趋势
- 优化发布时间

### 3. 数据驱动
- 记录每个视频的表现
- 分析哪些元数据组合效果最好
- 持续优化生成策略

## 故障排除

### 问题1：元数据生成失败
- 检查API连接
- 查看日志文件
- 使用备用元数据（自动生成）

### 问题2：语言不准确
- 调整提示词中的语言要求
- 增加具体的语言示例

### 问题3：标签不够优化
- 更新标签库
- 添加行业特定标签
- 研究竞争对手标签策略

## 总结

YouTube元数据生成功能让你能够：

✅ **自动化** - 无需手动编写发布信息
✅ **双语支持** - 覆盖更广泛的受众
✅ **优化建议** - 基于最佳实践的建议
✅ **完整方案** - 从标题到发布策略全覆盖
✅ **易于使用** - 自动集成在Pipeline中

这个功能大大简化了YouTube内容发布的准备工作，让你可以专注于内容创作本身。