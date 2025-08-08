# YouTube Story Generator V2 - 快速开始指南

## 5分钟快速上手

### 1. 环境准备

#### 安装Python依赖
```bash
pip install google-generativeai requests python-dotenv
```

#### 配置API密钥
创建 `.env` 文件：
```env
GEMINI_API_KEY=your_api_key_here
GEMINI_BASE_URL=https://api.openai-proxy.com/v1beta
```

### 2. 基础使用

#### 最简单的命令
```bash
python youtube_story_creator_v2.py VIDEO_ID CREATOR_NAME
```

**示例：**
```bash
python youtube_story_creator_v2.py dQw4w9WgXcQ my_first_story
```

### 3. 查看结果
生成的文件位于：
```
story_result/my_first_story/dQw4w9WgXcQ/final/
├── story.md          # 完整故事
├── report.md         # 生成报告
└── sd_prompts_v2.md  # 图片提示词
```

---

## 常用命令示例

### 生成短篇故事（15000字）
```bash
python youtube_story_creator_v2.py VIDEO_ID story_name --length 15000
```

### 生成详细的故事（15个片段）
```bash
python youtube_story_creator_v2.py VIDEO_ID story_name --segments 15
```

### 为每个片段生成多张图片
```bash
python youtube_story_creator_v2.py VIDEO_ID story_name --images-per-segment 3
```

### 完整配置示例
```bash
python youtube_story_creator_v2.py dQw4w9WgXcQ epic_story \
    --length 50000 \
    --segments 12 \
    --images-per-segment 2
```

---

## 工作流程简介

```
1. 获取视频 → 2. 提取DNA → 3. 生成框架 → 4. 创作片段 → 5. 润色 → 6. 生成图片
```

### 各阶段产出
| 阶段 | 输出文件 | 说明 |
|------|---------|------|
| 1 | `raw/subtitles.txt` | 视频字幕 |
| 2 | `processing/1_dna.txt` | 故事核心要素 |
| 3 | `processing/2_framework.txt` | 9步故事框架 |
| 4 | `segments/segment_*.txt` | 各个片段 |
| 5 | `final/story.md` | 完整故事 |
| 6 | `final/sd_prompts_v2.json` | SD提示词 |

---

## 核心特性

### 🎯 智能改编
- 自动识别观众"槽点"
- 放大争议性元素
- 保持故事连贯性

### 📝 9步叙事结构
1. 钩子开场
2. 角色与动机
3. 意外转折
4. 尝试与失败
5. 情绪低谷
6. 顿悟与转变
7. 最终行动
8. 胜利的代价
9. 新的悬念

### 🎨 图片生成
- 角色视觉一致性
- 智能场景提取
- 专业SD提示词

---

## 常见问题

### Q: 生成失败怎么办？
**A:** 程序支持断点续写，直接重新运行即可从中断处继续。

### Q: 如何控制故事长度？
**A:** 使用 `--length` 参数，单位是字数。

### Q: 能否自定义提示词？
**A:** 可以修改 `prompts/` 目录下的模板文件。

### Q: 支持哪些视频？
**A:** 需要视频有字幕（自动或手动），支持所有公开的YouTube视频。

---

## 进阶使用

### 批量处理
创建批处理脚本 `batch_process.py`：
```python
import subprocess

videos = [
    ("VIDEO_ID_1", "story_1"),
    ("VIDEO_ID_2", "story_2"),
    ("VIDEO_ID_3", "story_3"),
]

for video_id, name in videos:
    cmd = f"python youtube_story_creator_v2.py {video_id} {name}"
    subprocess.run(cmd, shell=True)
    print(f"✅ 完成: {name}")
```

### 自定义模板
修改 `prompts/segment_generator.md` 来改变生成风格：
```markdown
## 角色定位
你是一位[修改这里的风格描述]...

## 核心原则
1. [添加你的原则]
2. [添加更多原则]
```

---

## 输出示例

### 故事片段
```markdown
艾拉站在空荡荡的办公室里，窗外的城市灯火阑珊。
她的手机震动了一下，是母亲发来的消息："女儿，
你什么时候回家？"她深吸一口气，关掉了手机...
```

### SD提示词
```
masterpiece, best quality, ultra-detailed, 
young woman, office at night, city lights background, 
melancholic mood, cinematic lighting
```

---

## 获取帮助

- 查看完整文档：`docs/SYSTEM_DOCUMENTATION.md`
- 查看技术细节：`docs/TECHNICAL_ARCHITECTURE.md`
- 提交问题：创建GitHub Issue

---

## 下一步

1. ⭐ 尝试不同的视频类型
2. 🎨 调整图片生成参数
3. 📝 自定义提示词模板
4. 🚀 探索批量处理

---

*Happy Creating! 🎉*