# Pipeline Schema 表单配置功能

## 功能概述

将原来的JSON编辑器改为表单式配置，让用户通过可视化界面配置Pipeline参数，系统自动组装成标准JSON Schema格式。

## 实现细节

### 1. 新增组件

#### SchemaFormBuilder.tsx
- **位置**: `frontend/src/components/AutoPublish/SchemaFormBuilder.tsx`
- **功能**: 
  - 提供表单界面配置Schema字段
  - 自动将表单数据转换为JSON Schema格式
  - 支持多种字段类型和配置选项

### 2. 修改组件

#### PipelineFormModal.tsx
- **修改内容**:
  - 移除Monaco Editor依赖
  - 集成SchemaFormBuilder组件
  - 保持后端接口数据格式不变

## 功能特性

### 支持的字段类型
- **字符串** (string)
  - 支持默认值
  - 支持枚举值（下拉选择）
- **数字** (number)
  - 支持默认值
  - 支持最小值/最大值限制
- **布尔值** (boolean)
  - 支持默认true/false
- **数组** (array)
- **对象** (object)

### 字段配置选项
- **基础配置**:
  - 字段名称
  - 字段类型
  - 字段描述
  - 是否必填

- **高级配置**:
  - 默认值设置
  - 数值范围（最小值/最大值）
  - 枚举值列表
  - 必填项标记

### 操作功能
- 添加字段
- 删除字段
- 编辑字段属性
- 生成示例Schema
- 实时JSON预览

## 使用方法

### 1. 创建Pipeline
1. 访问 http://localhost:51083/auto-publish?tab=pipeline
2. 点击"创建Pipeline"
3. 填写基本信息
4. 切换到"参数配置"标签
5. 使用表单配置参数

### 2. 添加字段
1. 点击"添加字段"按钮
2. 配置字段属性：
   - 名称：唯一标识符
   - 类型：选择合适的数据类型
   - 描述：字段说明
   - 必填：是否为必填项

### 3. 配置特殊属性
- **数字类型**: 设置最小值、最大值、默认值
- **字符串类型**: 设置枚举值（逗号分隔）
- **布尔类型**: 设置默认true或false

### 4. 生成示例
点击"生成示例"按钮，自动创建常用的字段配置

## 自动生成的JSON Schema示例

```json
{
  "type": "object",
  "properties": {
    "video_id": {
      "type": "string",
      "description": "视频ID",
      "required": true
    },
    "image_library": {
      "type": "string",
      "description": "图库名称",
      "default": "default_library"
    },
    "duration_per_image": {
      "type": "number",
      "description": "单张图片持续时间（秒）",
      "default": 3,
      "minimum": 1,
      "maximum": 10
    },
    "enable_subtitles": {
      "type": "boolean",
      "description": "是否启用字幕",
      "default": true
    },
    "quality_level": {
      "type": "string",
      "description": "视频质量级别",
      "enum": ["low", "medium", "high", "ultra"],
      "default": "high"
    }
  },
  "required": ["video_id"]
}
```

## 优势

1. **用户友好**: 无需了解JSON Schema语法
2. **错误减少**: 通过表单验证减少配置错误
3. **效率提升**: 快速配置复杂的参数结构
4. **向后兼容**: 后端接口保持不变
5. **实时验证**: 即时检查配置合法性
6. **可视化**: 直观的界面操作

## 技术实现

- **前端框架**: React + TypeScript
- **UI组件**: Ant Design
- **状态管理**: React Hooks
- **数据转换**: 实时将表单数据转换为JSON Schema

## 后续优化建议

1. 添加更多字段类型支持（如日期、时间等）
2. 支持嵌套对象和数组配置
3. 添加字段依赖关系配置
4. 支持导入/导出Schema配置
5. 添加Schema模板库
6. 支持字段验证规则配置