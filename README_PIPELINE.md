# Pipeline架构设计文档

## 概述

新的Pipeline架构完全解耦了提示词和业务逻辑，使得调试和维护变得更加容易。采用了Pipeline模式、策略模式和配置驱动的设计理念。

## 核心优势

### 1. 完全解耦
- **提示词独立管理**：所有提示词存放在 `prompts/` 目录，通过 `PromptManager` 统一管理
- **业务逻辑模块化**：每个处理步骤都是独立的类，可以单独测试和替换
- **配置驱动**：通过 `pipeline_config.json` 灵活配置流程，无需修改代码

### 2. 灵活可扩展
- **Pipeline组合**：可以自由组合不同的步骤创建新的Pipeline
- **策略模式**：同一个步骤可以有多种实现策略（如片段生成的simple/contextual/fast模式）
- **钩子机制**：支持在步骤执行前后添加自定义逻辑

### 3. 易于调试
- **步骤隔离**：每个步骤独立执行，便于定位问题
- **缓存机制**：自动缓存中间结果，支持断点续传
- **详细日志**：每个步骤都有清晰的日志输出

## 架构组件

### 1. Pipeline架构 (`pipeline_architecture.py`)

#### PipelineContext
数据在整个流程中的载体：
```python
context = PipelineContext(
    video_id="xxx",
    creator_name="creator",
    target_length=30000,
    num_segments=9
)
```

#### PipelineStep
所有步骤的基类：
```python
class MyStep(PipelineStep):
    def execute(self, context: PipelineContext) -> StepResult:
        # 实现具体逻辑
        pass
```

#### PromptManager
统一管理所有提示词：
```python
manager = PromptManager()
prompt = manager.get_prompt('dna_extractor', story_text="...")
```

### 2. 具体步骤实现 (`pipeline_steps.py`)

包含所有具体的处理步骤：
- `FetchYouTubeDataStep`：获取YouTube数据
- `ExtractDNAStep`：提取故事DNA
- `GenerateFrameworkStep`：生成故事框架
- `GenerateSegmentsStep`：生成故事片段
- `PolishStoryStep`：润色故事
- `GenerateReportStep`：生成报告

### 3. 配置文件 (`pipeline_config.json`)

集中管理所有配置：
```json
{
  "pipelines": {
    "story_generation": {
      "steps": [...]
    }
  },
  "prompts": {
    "dna_extractor": {
      "file": "prompts/dna_extractor.md",
      "variables": ["story_text"]
    }
  },
  "strategies": {...}
}
```

### 4. 运行器 (`story_pipeline_runner.py`)

主入口，协调整个流程：
```python
runner = StoryPipelineRunner()
runner.run(video_id="xxx", creator_name="creator")
```

## 使用方法

### 基础使用

```bash
# 使用默认配置运行
python story_pipeline_runner.py VIDEO_ID --creator CREATOR_NAME

# 使用自定义配置
python story_pipeline_runner.py VIDEO_ID --config my_config.json

# 指定Pipeline类型
python story_pipeline_runner.py VIDEO_ID --pipeline quick_generation
```

### 编程使用

```python
from story_pipeline_runner import StoryPipelineRunner

# 创建运行器
runner = StoryPipelineRunner("custom_config.json")

# 运行Pipeline
success = runner.run(
    video_id="xxx",
    creator_name="creator",
    target_length=30000,
    num_segments=9
)
```

### 自定义Pipeline

```python
from pipeline_architecture import Pipeline, PipelineContext
from pipeline_steps import ExtractDNAStep, GenerateSegmentsStep

# 创建自定义Pipeline
pipeline = Pipeline("custom_pipeline")
pipeline.add_step(ExtractDNAStep(gemini_client))
pipeline.add_step(GenerateSegmentsStep(gemini_client))

# 运行
context = PipelineContext(video_id="xxx", creator_name="creator")
pipeline.execute(context)
```

## 提示词管理

### 添加新提示词

1. 在 `prompts/` 目录创建新的 `.md` 文件
2. 在提示词中使用 `{variable}` 格式定义变量
3. 在 `pipeline_config.json` 中注册：
```json
{
  "prompts": {
    "my_prompt": {
      "file": "prompts/my_prompt.md",
      "variables": ["var1", "var2"]
    }
  }
}
```

### 动态修改提示词

```python
# 运行时注册自定义提示词
prompt_manager.register_template(
    name="custom_prompt",
    template="Generate a story about {topic}",
    variables=["topic"]
)
```

## 扩展指南

### 添加新步骤

1. 继承 `PipelineStep` 基类：
```python
class MyCustomStep(PipelineStep):
    def __init__(self):
        super().__init__("my_custom_step")
    
    def execute(self, context: PipelineContext) -> StepResult:
        # 实现逻辑
        return StepResult(success=True, data=result)
```

2. 在配置中添加步骤：
```json
{
  "pipelines": {
    "my_pipeline": {
      "steps": [
        {"name": "my_custom_step", "class": "MyCustomStep"}
      ]
    }
  }
}
```

### 添加新策略

```python
class MyStrategy(ProcessingStrategy):
    def process(self, input_data: Any, **kwargs) -> Any:
        # 实现策略逻辑
        return processed_data
```

### 添加钩子

```python
def my_hook(step, context):
    print(f"Processing: {step.name}")

pipeline.add_hook('before_step', my_hook)
```

## 调试技巧

### 1. 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 单步调试
```python
# 只运行特定步骤
step = ExtractDNAStep(gemini_client)
result = step.execute(context)
```

### 3. 查看缓存
缓存文件存储在 `story_result/creator_name/video_id/` 目录

### 4. 修改提示词
直接编辑 `prompts/` 目录下的文件，无需重启程序

## 性能优化

### 1. 并行处理
配置 `parallel: true` 启用并行处理：
```json
{
  "strategies": {
    "segment_generation": {
      "fast": {
        "parallel": true
      }
    }
  }
}
```

### 2. 缓存策略
- 自动缓存所有中间结果
- 支持TTL（生存时间）配置
- 可选择性禁用某些步骤的缓存

### 3. API调用优化
- 配置重试次数和延迟
- 批量处理请求
- 智能限流

## 迁移指南

从旧版本迁移到新架构：

1. **提示词迁移**：将硬编码的提示词移到 `prompts/` 目录
2. **配置迁移**：将硬编码的参数移到 `pipeline_config.json`
3. **代码适配**：将原有的阶段函数重构为Pipeline步骤
4. **测试验证**：使用相同的输入验证输出一致性

## 总结

新的Pipeline架构提供了：
- ✅ 清晰的关注点分离
- ✅ 灵活的配置管理
- ✅ 强大的扩展能力
- ✅ 便捷的调试体验
- ✅ 可靠的缓存机制

这使得整个系统更加健壮、可维护和可扩展。