# 提示词格式问题修复说明

## 问题描述

运行V3 Pipeline时出现错误：
```
KeyError: '\n  "adaptationAnalysis"'
```

### 根本原因

`PromptManager`将所有提示词文件当作Python格式化字符串（f-string）处理，使用`str.format()`方法。当`framework_generatorv3.md`中包含JSON示例时，花括号`{}`被误认为是格式化占位符。

例如：
```json
{
  "adaptationAnalysis": {
    "newStoryTitle": "..."
  }
}
```

Python的`format()`方法会尝试将`"adaptationAnalysis"`作为变量名进行替换，导致KeyError。

## 解决方案

### 1. 修改PromptTemplate类

在`pipeline_architecture.py`中，修改`format()`方法：

```python
def format(self, **kwargs) -> str:
    # 如果没有提供变量，直接返回原始模板（不进行格式化）
    if not kwargs and not self.variables:
        return self.template
    # 只有在有变量时才格式化
    if self.variables:
        return self.template.format(**kwargs)
    return self.template
```

### 2. 不自动解析变量

修改`load_prompt()`方法，不再自动从内容中提取变量：

```python
# 不自动解析变量，避免JSON中的花括号被误识别
variables = []

# 如果配置中指定了变量，使用配置中的
if name in self.prompt_configs:
    config = self.prompt_configs[name]
    variables = config.get('variables', [])
```

### 3. 更新配置文件

在`pipeline_config.json`中明确指定哪些提示词有变量：

```json
"framework_generatorv3": {
  "variables": [],  // 明确指定无变量
  "note": "No variables - contains JSON examples with braces"
}
```

## 测试验证

运行测试脚本验证修复：

```bash
python test_prompt_fix.py
```

应该看到：
```
测试加载: framework_generatorv3
  ✅ 成功加载，包含JSON结构
  - 长度: XXXX 字符
  - 变量: []
```

## 使用建议

### 1. 定义需要格式化的提示词

如果提示词需要变量替换，在配置中明确指定：

```json
"my_prompt": {
  "file": "prompts/my_prompt.md",
  "variables": ["name", "age"]
}
```

在提示词中使用：
```
Hello {name}, you are {age} years old.
```

### 2. 包含特殊字符的提示词

如果提示词包含花括号但不需要格式化：

```json
"json_example_prompt": {
  "file": "prompts/json_example.md",
  "variables": []  // 空数组表示不格式化
}
```

### 3. 转义花括号

如果确实需要在格式化的提示词中包含花括号，使用双花括号转义：

```
这是一个JSON示例：{{ "key": "value" }}
这里是变量：{variable_name}
```

## 影响范围

此修复只影响提示词加载逻辑，不影响其他功能：

- ✅ `framework_generatorv3.md` - 可以正常包含JSON示例
- ✅ `story_header.md` - 不需要变量，直接使用
- ✅ `segment_generator.md` - 如需变量，在配置中指定
- ✅ 其他提示词 - 根据需要配置

## 总结

这个修复让提示词系统更加灵活：

1. **明确控制** - 通过配置决定哪些提示词需要格式化
2. **避免冲突** - JSON、代码示例等可以安全地包含在提示词中
3. **向后兼容** - 现有的格式化功能仍然可用

现在可以安全地在提示词中包含任何内容，包括JSON示例、代码片段等，而不用担心被误解析。