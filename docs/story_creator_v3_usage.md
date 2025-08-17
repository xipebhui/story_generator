# YouTube Story Creator V3 使用指南

## 📋 概述

YouTube Story Creator V3 是一个简化版的故事框架生成器，使用新的 `framework_generatorv3.md` 提示词，专注于从YouTube视频生成故事改编框架。

## 🎯 主要特性

- **简化流程**：专注于框架生成，去除复杂的多阶段处理
- **新提示词格式**：使用v3版本的框架生成器提示词
- **标准输入格式**：遵循 `[START_OF_INPUT_DATA]` 格式规范
- **JSON输出**：生成结构化的JSON框架（如果AI正确响应）
- **完整日志**：详细的处理日志便于调试

## 🚀 快速开始

### 1. 基本使用

```bash
# 处理单个视频
python youtube_story_creator_v3.py VIDEO_ID

# 指定输出目录
python youtube_story_creator_v3.py VIDEO_ID -o /path/to/output
```

### 2. 测试运行

```bash
# 运行测试脚本
python test_v3.py VIDEO_ID
```

## 📁 输出结构

```
story_v3/
└── VIDEO_ID/
    ├── metadata/                    # 元数据文件夹
    │   ├── video_info.json         # 视频信息
    │   ├── comments.json           # 评论数据
    │   ├── subtitle_zh.txt         # 中文字幕
    │   └── subtitle_en.txt         # 英文字幕（备选）
    ├── framework_response.txt       # AI原始响应
    ├── framework.json              # 解析后的框架JSON
    └── report.md                   # 处理报告
```

## 💻 程序化调用

```python
from youtube_story_creator_v3 import YouTubeStoryCreatorV3

# 创建处理器
creator = YouTubeStoryCreatorV3(
    video_id="your_video_id",
    output_dir="custom_output"
)

# 运行完整流程
framework = creator.run()

# 或分步执行
metadata = creator.extract_metadata()  # 提取元数据
framework = creator.generate_framework(metadata)  # 生成框架
```

## 📝 输入数据格式

V3版本使用特定的输入格式：

```
[START_OF_INPUT_DATA]
Original Title
[视频标题]
Original Reference Word Count
[字幕字数]
Hot Comments
[评论1]
[评论2]
...
Original Story Text
[完整字幕文本]
[END_OF_INPUT_DATA]
```

## 🔧 框架JSON结构

成功时返回的JSON结构：

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
      "amplificationPlan": "增强计划"
    },
    "mainCharacters": [
      {
        "originalName": "原名",
        "newName": "新名",
        "personalityTraits": "性格特征",
        "physicalFeatures": "外貌特征",
        "coreMotivation": "核心动机"
      }
    ]
  },
  "storyBlueprint": [
    {
      "step": 1,
      "stepTitle": "步骤标题",
      "plotPlan": "情节计划",
      "pacingAndWordCount": "节奏和字数"
    }
  ]
}
```

## 🔍 日志输出

程序会输出详细的日志信息：

1. **元数据提取阶段**
   - 视频信息获取
   - 评论提取
   - 字幕下载

2. **框架生成阶段**
   - 输入数据构建（完整打印）
   - AI响应（完整打印）
   - JSON解析结果

3. **文件保存**
   - 各文件保存路径
   - 处理状态

## ⚠️ 注意事项

1. **API密钥**：确保设置了正确的Gemini API密钥
   ```bash
   export NEWAPI_API_KEY="your_api_key"
   # 或
   export GEMINI_API_KEY="your_api_key"
   ```

2. **字幕要求**：视频必须有可用的字幕（中文或英文）

3. **JSON解析**：AI可能不总是返回正确的JSON格式，此时会保存原始文本

4. **输出查看**：
   - 控制台会直接打印AI的完整响应
   - 查看 `framework_response.txt` 获取原始响应
   - 查看 `framework.json` 获取解析后的JSON（如果成功）

## 📊 处理流程

```
1. 提取元数据
   ├── 获取视频信息
   ├── 获取评论（前20条）
   └── 获取字幕

2. 生成框架
   ├── 构建输入数据
   ├── 调用Gemini API
   └── 解析响应

3. 保存结果
   ├── 保存原始响应
   ├── 保存JSON（如果成功解析）
   └── 生成报告
```

## 🐛 调试技巧

1. **查看完整输入**：日志中会打印完整的输入数据
2. **查看AI响应**：控制台和 `framework_response.txt` 都有完整响应
3. **检查JSON解析**：如果JSON解析失败，检查原始响应格式
4. **验证元数据**：确保 `metadata/` 文件夹中有必要的文件

## 📚 与V2版本的区别

| 特性 | V2版本 | V3版本 |
|------|--------|--------|
| 提示词 | 多个提示词文件 | 单一framework_generatorv3.md |
| 输入格式 | 自定义格式 | 标准[START_OF_INPUT_DATA]格式 |
| 处理阶段 | 5个阶段 | 2个阶段（元数据+框架） |
| 输出 | 完整故事 | 仅框架JSON |
| 复杂度 | 高 | 低 |

## 🤝 故障排除

**问题：无法获取字幕**
- 解决：检查视频是否有可用字幕，尝试不同语言

**问题：JSON解析失败**
- 解决：查看原始响应，可能需要调整提示词

**问题：API调用失败**
- 解决：检查API密钥和网络连接

---
*YouTube Story Creator V3 - 简化版框架生成器*