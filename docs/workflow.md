# YouTube故事内容创作优化工作流程

创建时间：2025-08-06

---

## 概述

本工作流程采用"框架-改编-生成"三阶段模型，解决了处理超长文本时的上下文窗口限制问题，实现了高质量的YouTube故事内容创作。

## 工作流程图

```
原始故事 (数万字)
    ↓
[阶段1: 故事DNA提取] → 输出: 故事DNA (800-1200字)
    ↓
[阶段2: 改编框架设计] → 输出: 改编框架 + 营销材料 + 视觉素材
    ↓
[阶段3: 完整故事生成] → 输出: 改编后完整故事
    ↓
[安全检测] → 输出: 内容安全报告
    ↓
发布就绪的YouTube内容包
```

## 详细步骤说明

### 第一阶段：故事DNA提取
**使用提示词**：`@prompts\2025-08-06_story_dna_extractor_prompt.md`

**输入**：原始Reddit故事全文（可能数万字）

**输出**：高度浓缩的故事DNA，包括：
- 故事类型和核心前提
- 结构框架（起承转合）
- 角色详细描述（包含外貌特征）
- 核心冲突和闪光点
- 情感内核和观众吸引点

**关键优势**：将海量信息压缩到1000字左右，为后续处理创造可控的上下文环境。

### 第二阶段：改编框架与营销设计
**使用提示词**：`@prompts\2025-08-06_story_adaptation_framework_generator_prompt.md`

**输入**：
- 第一阶段产出的故事DNA
- 参考视频标题和热门评论
- 目标平台要求

**输出**：
1. **改编策略**：目标受众、叙事调整、节奏设计
2. **角色视觉标准化**：详细的外貌描述（用于AI绘图一致性）
3. **关键场景设计**：3-5个视觉场景及其SD提示词
4. **YouTube营销材料**：
   - 3个标题选项
   - 缩略图设计提示词
   - 视频描述和标签
   - 开场钩子脚本
5. **内容生成指导**：为第三阶段提供详细要求

**特色功能**：
- 集成了Stable Diffusion提示词生成
- 确保人物视觉一致性
- 优化了YouTube算法要素

### 第三阶段：完整故事生成
**使用提示词**：`@prompts\2025-08-06_story_final_generator_prompt.md`

**输入**：第二阶段的改编框架和写作要求

**输出**：
- 完整的改编故事（英文）
- 故事统计信息（字数、阅读时间等）

**写作特点**：
- 强调开场吸引力（5秒规则）
- 自然的对话风格
- 适合视频配音的节奏
- 情感高潮的充分渲染

### 内容安全检测
**使用提示词**：`@prompts\2025-08-06_content_safety_checker_prompt.md`

**功能**：
- 检测敏感内容和违规风险
- 提供具体修改建议
- 评估平台兼容性
- 给出年龄分级建议

## JSON格式使用说明

### 为什么使用JSON格式？
所有提示词现已更新为输出结构化的JSON格式，带来以下优势：
- **程序化处理**：轻松解析和提取特定字段
- **数据一致性**：确保输出格式统一
- **自动化集成**：便于API调用和工作流自动化
- **版本控制**：易于追踪数据结构变化

### JSON数据流示例
```python
# 第一阶段：提取故事DNA
story_dna = ai_extract_dna(original_story)
dna_json = json.loads(story_dna)

# 第二阶段：生成改编框架
adaptation_input = {
    "story_dna": dna_json["story_dna"],
    "reference_title": "...",
    "top_comments": ["..."]
}
framework_json = json.loads(ai_generate_framework(adaptation_input))

# 第三阶段：生成完整故事
story_instructions = framework_json["adaptation_framework"]["story_generation_instructions"]
final_story_json = json.loads(ai_generate_story(story_instructions))

# 安全检测
safety_json = json.loads(ai_check_safety(final_story_json["generated_story"]["story_content"]["full_text"]))
```

### 关键字段速查

#### 故事DNA (story_dna_extractor)
- `story_dna.characters[].physical_appearance` - 角色外貌（用于AI绘图）
- `story_dna.excellent_points.dramatic_scenes` - 关键场景列表
- `story_dna.audience_appeal.engagement_triggers` - 观众吸引点

#### 改编框架 (adaptation_framework_generator)
- `adaptation_framework.visual_scenes[].sd_prompt` - SD绘图提示词
- `adaptation_framework.youtube_assets.video_titles` - 视频标题选项
- `adaptation_framework.character_visuals` - 标准化角色视觉

#### 最终故事 (story_final_generator)
- `generated_story.story_content.full_text` - 完整故事文本
- `generated_story.story_content.key_dialogues` - 关键对话
- `generated_story.quality_metrics` - 质量评分

#### 安全报告 (content_safety_checker)
- `safety_report.final_verdict.recommendation` - 发布建议
- `safety_report.detected_issues` - 问题列表
- `safety_report.modifications.required` - 必需修改

## 实施建议

### 1. 批处理优化
可以同时处理多个故事的第一阶段，因为这个阶段独立且计算密集。

### 2. 人工检查点
- 第一阶段后：确认故事DNA质量
- 第二阶段后：审核改编方向和营销策略
- 第三阶段后：最终内容审核

### 3. 迭代改进
保存每个阶段的输出，便于：
- A/B测试不同的改编策略
- 根据表现优化提示词
- 建立成功案例库

### 4. 工具集成建议
- 使用API串联各阶段，实现自动化
- 集成Stable Diffusion API直接生成图片
- 添加YouTube Analytics反馈循环

### 5. 自动化脚本示例
```bash
#!/bin/bash
# YouTube内容创作自动化流程

# 阶段1: 提取DNA
DNA_OUTPUT=$(curl -X POST api/extract-dna -d @original_story.txt)

# 阶段2: 生成框架
FRAMEWORK_OUTPUT=$(curl -X POST api/generate-framework -d "$DNA_OUTPUT")

# 阶段3: 生成故事
STORY_OUTPUT=$(curl -X POST api/generate-story -d "$FRAMEWORK_OUTPUT")

# 安全检测
SAFETY_CHECK=$(curl -X POST api/check-safety -d "$STORY_OUTPUT")

# 解析结果
if [ $(echo $SAFETY_CHECK | jq -r '.safety_report.final_verdict.recommendation') == "SAFE_TO_PUBLISH" ]; then
    echo "Content ready for publishing!"
else
    echo "Content needs modification"
fi
```

## 质量保证清单

- [ ] 故事DNA是否准确捕捉原作精髓？
- [ ] 改编是否增强了故事吸引力？
- [ ] 角色描述是否足够详细以确保视觉一致性？
- [ ] 营销材料是否创造了足够的"信息缺口"？
- [ ] 最终故事是否保持了高度的可读性？
- [ ] 内容是否通过了安全检测？

## 常见问题处理

### Q: 如果原始故事特别长怎么办？
A: 可以将故事分成几个部分，分别进行第一阶段处理，然后合并故事DNA。

### Q: 如何确保生成的图片风格一致？
A: 第二阶段的角色视觉标准化非常关键，建议创建角色参考表并在每个SD提示词中引用。

### Q: 怎样提高病毒传播潜力？
A: 重点关注第二阶段的情感共鸣点识别和标题优化，可以参考同类爆款视频的模式。

---

## 总结

这个优化后的工作流程通过分层处理和任务专门化，成功解决了超长文本处理的技术限制，同时提升了内容质量和营销效果。每个阶段都可以独立优化，整体系统具有良好的可扩展性和适应性。