# 提示词调优指南

## 概述

本文档详细介绍V3 Pipeline中各个提示词的作用、输入输出格式，以及调优技巧。通过修改这些提示词，你可以控制故事生成的各个方面，而无需修改任何代码。

## 提示词文件结构

```
prompts/
├── framework_generatorv3.md   # 框架生成（核心）
├── story_header.md            # 开头生成
├── segment_generator.md       # 片段生成
└── final_polish.md           # 最终润色
```

## 1. Framework Generator V3 (`framework_generatorv3.md`)

### 作用
这是整个Pipeline的核心，负责分析原始故事并生成改编框架。

### 输入格式
```
[START_OF_INPUT_DATA]
Original Title
[视频标题]

Original Reference Word Count
[字数]

Hot Comments
[评论1]
[评论2]
...

Original Story Text
[完整字幕/故事文本]
[END_OF_INPUT_DATA]
```

### 输出格式
纯JSON，包含两个主要部分：
1. `adaptationAnalysis` - 改编分析
2. `storyBlueprint` - 故事蓝图（决定segment数量）

### 关键调优点

#### 1.1 控制Segment数量
修改提示词中对`storyBlueprint`的描述：
```markdown
# 原始（自动决定）
"storyBlueprint": [根据故事长度和复杂度决定步骤数量]

# 固定数量
"storyBlueprint": [生成恰好12个步骤，每个约1000字]

# 范围控制
"storyBlueprint": [生成8-15个步骤，根据情节需要调整]
```

#### 1.2 调整分析深度
在"核心改编哲学"部分添加具体要求：
```markdown
# 强调情感分析
- 深入挖掘每个情节点的情感价值
- 识别并放大情感转折点

# 强调冲突设计
- 为每个步骤设计明确的冲突点
- 确保冲突逐步升级
```

#### 1.3 优化角色设定
修改`mainCharacters`的要求：
```markdown
# 添加更多细节
"mainCharacters": [
  {
    "physicalFeatures": "详细的外貌描述，包括年龄、身高、穿着风格",
    "psychologicalProfile": "深层心理特征和创伤",
    "speechPattern": "说话方式和口头禅"
  }
]
```

### 调优示例

**目标**：生成更多悬疑元素

```markdown
# 在"核心改编哲学"后添加：
悬疑强化原则 (Suspense Amplification):
- 每个step必须包含至少一个未解之谜
- 信息逐步释放，保持读者好奇心
- 在storyBlueprint中明确标注悬念点和揭示点
```

## 2. Story Header (`story_header.md`)

### 当前内容
```
角色：内容运行专家，专门写爆款开头
职责：根据输入的故事框架内容，生成一个爆款的故事开头，可以是数字型，反差性，勾起用户的好奇心，让用户欲罢不能停下来，字数在100字左右
输入：json 格式的故事更改
输出：故事开头，纯英文文本
```

### 输入
完整的Framework V3 JSON结果

### 输出
100字左右的英文开头

### 关键调优点

#### 2.1 开头类型控制
```markdown
# 数字型开头
职责：生成数字型开头，如"3 seconds changed everything"

# 对话型开头
职责：以紧张的对话开始，直接进入冲突

# 场景型开头
职责：描述一个视觉冲击力强的场景
```

#### 2.2 字数控制
```markdown
# 超短开头（50字）
字数在50字左右，一句话制造最大冲击

# 标准开头（100字）
字数在100字左右，2-3句建立情境

# 长开头（200字）
字数在200字左右，完整的开场场景
```

#### 2.3 情绪定调
```markdown
# 添加情绪指导
基调：根据framework中的coreExperienceLoop，选择合适的情绪：
- 如果是"压抑-爆发"模式，开头要压抑
- 如果是"悬念-揭秘"模式，开头要神秘
- 如果是"温馨-转折"模式，开头要温暖
```

### 调优示例

**目标**：生成更吸引人的数字型开头

```markdown
角色：爆款开头专家，专精数字型钩子
职责：生成包含具体数字的开头，数字要精确、震撼、反常识
要求：
1. 必须在前10个词内出现数字
2. 数字要具体（不用"很多"、"几个"）
3. 创造认知反差（如"The $3 decision that cost me $3 million"）
输入：json格式的故事框架
输出：100字左右纯英文开头
```

## 3. Segment Generator (`segment_generator.md`)

### 作用
生成每个故事片段，需要保持连贯性和节奏控制。

### 输入格式
```markdown
==================================================
FRAMEWORK V3 (Complete JSON)
==================================================
[完整的framework JSON]

==================================================
CURRENT STEP NUMBER
==================================================
Step [N]

==================================================
CURRENT STEP TASK
==================================================
[当前step的JSON对象]

==================================================
PREVIOUS TEXT (Last 200 characters)
==================================================
[前一段的最后200字]
```

### 关键调优点

#### 3.1 连贯性控制
```markdown
# 强调衔接
## 工作流程
1. 必须从previous text的情绪和动作直接延续
2. 前50字内完成过渡
3. 不能突兀转换场景
```

#### 3.2 节奏控制
```markdown
# 根据step位置调整节奏
## 节奏规则
- Step 1-3: 慢节奏，建立基础
- Step 4-6: 中等节奏，发展冲突
- Step 7-9: 快节奏，推向高潮
- 最后Step: 节奏放缓，emotional payoff
```

#### 3.3 字数精确控制
```markdown
# 添加严格字数要求
## 字数控制
解析current task中的pacingAndWordCount字段
- 如果包含"1000字"，输出950-1050字
- 如果包含"快节奏"，短句为主
- 如果包含"慢节奏"，长句描写
```

### 调优示例

**目标**：增强情感深度

```markdown
# 在"核心原则"后添加
## 情感深度要求
1. 每个segment必须包含至少一处内心独白
2. 通过感官细节传达情绪（不直接说"他很悲伤"）
3. 每500字至少一个情感爆发点
```

## 4. Final Polish (`final_polish.md`)

### 作用
最终润色，统一风格，优化节奏。

### 关键调优点

#### 4.1 风格统一
```markdown
# 指定具体风格
C. 语言和风格增强
统一语气：采用[具体风格]叙述
- 第一人称内心独白风格
- 第三人称全知视角
- 电影剧本式简洁风格
```

#### 4.2 YouTube优化
```markdown
# 增强YouTube特性
D. YouTube和观众适应性
钩子密度：每3分钟（约500字）设置一个小钩子
评论诱导：插入容易引发评论的元素
- 争议性选择
- 开放性问题
- 共鸣点
```

## 5. 实战调优流程

### Step 1: 确定优化目标
- 故事类型（悬疑/情感/动作）
- 目标受众（年龄/兴趣）
- 期望效果（催泪/燃爆/深思）

### Step 2: 分析当前输出
```bash
# 查看当前生成的框架
cat story_result/*/processing/framework_v3.json

# 检查segment质量
ls story_result/*/processing/segments/
```

### Step 3: 逐步调整

#### 调整顺序
1. **先调Framework** - 这决定整体结构
2. **再调Header** - 确保开头吸引人
3. **优化Segment** - 提升每段质量
4. **最后Polish** - 统一润色

#### 测试方法
```bash
# 修改提示词后立即测试
python test_v3_pipeline.py VIDEO_ID

# 只看特定步骤的输出
cat story_result/test/VIDEO_ID/processing/[具体文件]
```

### Step 4: A/B测试

创建多个版本的提示词：
```
prompts/
├── framework_generatorv3.md        # 原版
├── framework_generatorv3_emotional.md  # 情感版
├── framework_generatorv3_suspense.md   # 悬疑版
```

在代码中切换：
```python
# 在 story_pipeline_v3_runner.py 中
self.prompt_manager.load_prompt('framework_generatorv3_emotional')
```

## 6. 常见问题与解决

### 问题1: Segment数量不符合预期
**解决**: 在`framework_generatorv3.md`中明确指定：
```markdown
"storyBlueprint": [
  生成恰好10个steps，不多不少
]
```

### 问题2: 开头不够吸引人
**解决**: 在`story_header.md`中添加具体示例：
```markdown
示例开头：
- "The last text I sent was 'I love you.' She never read it."
- "4:17 AM. That's when everything I believed turned out to be a lie."
```

### 问题3: Segments之间断裂
**解决**: 在`segment_generator.md`中强化衔接：
```markdown
## 强制衔接规则
1. 复制previous text的最后一句
2. 用转折词连接（However/Meanwhile/Suddenly）
3. 保持相同的时态和人称
```

### 问题4: 字数偏差太大
**解决**: 添加字数监控：
```markdown
## 输出格式
在segment末尾添加：
[Word count: XXX]
确保在目标范围内
```

## 7. 高级技巧

### 7.1 条件化生成
根据不同类型的视频使用不同策略：
```markdown
# 在framework_generatorv3.md中
如果原故事是教程类：重点提取知识点
如果原故事是vlog类：重点保留个人特色
如果原故事是新闻类：重点强化冲突
```

### 7.2 模板库
创建常用模板：
```markdown
# templates/horror_opening.md
"It started with a knock at 3 AM. I lived alone."

# templates/romance_opening.md  
"The coffee shop where we met is gone now, but I still go there every morning."
```

### 7.3 质量检查清单
在每个提示词末尾添加：
```markdown
## 质量检查
生成后自检：
□ 是否符合字数要求
□ 是否保持角色一致性
□ 是否有语法错误
□ 是否足够吸引人
```

## 8. 性能优化

### 8.1 减少Token使用
- 简化指令，去除冗余
- 使用简洁的JSON键名
- 避免重复示例

### 8.2 提高生成速度
- 降低temperature（更确定性）
- 减少max_tokens限制
- 分批处理长内容

## 总结

提示词调优是一个迭代过程：

1. **明确目标** - 知道要优化什么
2. **小步调整** - 每次只改一个方面
3. **快速测试** - 利用缓存快速验证
4. **记录效果** - 保存好的版本
5. **持续优化** - 根据反馈改进

记住：好的提示词是具体的、有示例的、可验证的。