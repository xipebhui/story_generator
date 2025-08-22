# V3 Pipeline 使用文档

## 概述

V3 Pipeline是一个全新设计的故事生成流程，具有以下特点：

1. **移除DNA提取** - 直接使用原始字幕
2. **Framework V3** - 使用`framework_generatorv3.md`生成JSON格式框架
3. **动态Segment** - 根据V3框架自动决定segment数量
4. **独立开头生成** - 专门的爆款开头生成
5. **严格模式** - 任何失败立即终止，保证质量
6. **完整缓存** - 所有中间结果保存用于调试

## 流程图

```
YouTube视频
    ↓
1. 获取数据 (字幕/评论/信息)
    ↓
2. Framework V3生成 (JSON格式)
    ↓
3. 解析框架 (提取segment数量)
    ↓
4. 生成开头 (爆款hook)
    ↓
5. 生成Segments (动态数量)
    ↓
6. 拼接&润色
    ↓
7. 生成总结 (中文)
    ↓
最终输出
```

## 快速开始

### 基础使用

```bash
# 运行V3 Pipeline
python story_pipeline_v3_runner.py VIDEO_ID

# 指定创作者名称
python story_pipeline_v3_runner.py VIDEO_ID --creator myname

# 调试模式
python story_pipeline_v3_runner.py VIDEO_ID --debug
```

### 测试脚本

```bash
# 使用测试脚本
python test_v3_pipeline.py VIDEO_ID

# 使用默认测试视频
python test_v3_pipeline.py
```

## 文件结构

### 核心文件

- `pipeline_context_v3.py` - V3专用数据结构
- `pipeline_steps_v3.py` - V3步骤实现
- `story_pipeline_v3_runner.py` - 严格模式运行器
- `test_v3_pipeline.py` - 测试脚本

### 提示词文件

- `prompts/framework_generatorv3.md` - V3框架生成提示词
- `prompts/story_header.md` - 开头生成提示词
- `prompts/segment_generator.md` - 片段生成提示词
- `prompts/final_polish.md` - 润色提示词

### 输出目录

```
story_result/
└── [creator_name]/
    └── [video_id]/
        ├── raw/                    # 原始数据
        │   ├── video_info.json
        │   ├── comments.json
        │   └── subtitle.txt
        ├── processing/             # 处理过程文件
        │   ├── framework_v3.json   # V3框架JSON
        │   ├── parsed_segments.json
        │   ├── story_header.txt    # 生成的开头
        │   ├── segments/           # 所有segment
        │   │   ├── segment_01.txt
        │   │   ├── segment_02.txt
        │   │   └── ...
        │   ├── merged_story.txt    # 拼接的故事
        │   └── polished_story.txt  # 润色后的故事
        └── final/                  # 最终输出
            ├── story.txt           # 最终英文故事
            ├── summary_cn.txt      # 中文总结
            ├── metadata.json       # 元数据
            └── report.md           # 执行报告
```

## V3特性详解

### 1. Framework V3 JSON结构

```json
{
  "adaptationAnalysis": {
    "newStoryTitle": "新故事标题",
    "coreConcept": "核心概念",
    "openingReplicationStrategy": {
      "originalHookAnalysis": "原始钩子分析",
      "replicationPlan": "复制计划"
    },
    "coreExperienceLoop": {
      "loopPattern": "循环模式",
      "amplificationPlan": "放大计划"
    },
    "mainCharacters": [...]
  },
  "storyBlueprint": [
    {
      "step": 1,
      "stepTitle": "步骤标题",
      "plotPlan": "情节计划",
      "pacingAndWordCount": "节奏和字数"
    },
    ...
  ]
}
```

### 2. 严格模式

- **无降级** - 不会使用备用方案
- **无重试** - 失败立即终止
- **完整日志** - 记录所有步骤
- **错误追踪** - 保存错误信息到`error.json`

### 3. 动态Segment

- Segment数量由Framework V3自动决定
- 每个segment对应`storyBlueprint`中的一个step
- 支持任意数量的segments（不限于9或30）

### 4. 缓存机制

- 每个步骤都有独立缓存
- 支持断点续传
- 可以单独重新生成某个步骤

## 调试技巧

### 1. 查看中间结果

所有中间文件都保存在`processing/`目录：

```bash
# 查看Framework V3 JSON
cat story_result/[creator]/[video_id]/processing/framework_v3.json

# 查看生成的开头
cat story_result/[creator]/[video_id]/processing/story_header.txt

# 查看某个segment
cat story_result/[creator]/[video_id]/processing/segments/segment_01.txt
```

### 2. 修改提示词

直接编辑`prompts/`目录下的文件，无需修改代码：

- `framework_generatorv3.md` - 调整框架生成策略
- `story_header.md` - 优化开头生成
- `segment_generator.md` - 改进segment质量

### 3. 错误处理

如果Pipeline失败：

1. 查看`error.json`了解失败步骤
2. 查看`pipeline_v3.log`详细日志
3. 检查`processing/`目录中最后生成的文件

### 4. 重新运行

由于有缓存，可以安全地重新运行：

```bash
# 会自动使用已缓存的步骤
python story_pipeline_v3_runner.py VIDEO_ID

# 删除缓存重新生成
rm -rf story_result/[creator]/[video_id]/processing/
python story_pipeline_v3_runner.py VIDEO_ID
```

## API配置

### 环境变量

```bash
# YouTube API (可选，有默认值)
export YOUTUBE_API_KEY="your_youtube_api_key"

# Gemini API (推荐设置)
export NEWAPI_API_KEY="your_gemini_api_key"
```

## 常见问题

### Q: 为什么使用严格模式？

A: 保证生成质量。宁可失败重试，也不产生低质量内容。

### Q: 如何调整segment数量？

A: 修改`framework_generatorv3.md`，让AI生成更多或更少的steps。

### Q: 如何优化生成速度？

A: 利用缓存机制。已生成的步骤会自动缓存，重新运行时跳过。

### Q: 如何处理token限制？

A: 
- Framework V3已优化为JSON格式，更紧凑
- Segment生成只传入必要信息
- 润色时可以分批处理

## 性能指标

典型执行时间（参考）：

- 数据获取: 5-10秒
- Framework V3: 10-15秒
- 开头生成: 5-10秒
- Segment生成: 5-10秒/个
- 润色: 15-20秒
- 总计: 2-5分钟（取决于segment数量）

## 维护说明

### 添加新步骤

1. 在`pipeline_steps_v3.py`中创建新的Step类
2. 在`pipeline_context_v3.py`中添加相应字段
3. 在`story_pipeline_v3_runner.py`中添加到Pipeline

### 修改流程

1. 调整`create_pipeline()`中的步骤顺序
2. 更新相关步骤的输入输出
3. 测试确保数据正确传递

## 总结

V3 Pipeline提供了：

✅ **灵活性** - 动态segment数量，适应不同故事
✅ **质量保证** - 严格模式，失败即止
✅ **易调试** - 完整缓存，清晰日志
✅ **可扩展** - 模块化设计，易于修改
✅ **高效率** - 智能缓存，断点续传

这是一个专为生产环境设计的可靠Pipeline。