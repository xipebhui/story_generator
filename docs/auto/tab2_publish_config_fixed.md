# Tab 2: 发布配置管理（修复数组输入）

> 参考：[global_context.md](./global_context.md) - 全局上下文和规范

## 修复：Pipeline参数动态表单（支持数组类型）

### 改进后的动态表单渲染组件

```tsx
// components/AutoPublish/DynamicPipelineForm.tsx
import React from 'react';
import {
  Form, Input, InputNumber, Select, Switch, Button, Space, Card
} from 'antd';
import {
  PlusOutlined, MinusCircleOutlined, DeleteOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;

/**
 * 渲染数组类型的输入组件
 */
const renderArrayField = (key: string, param: any, isRequired: boolean) => {
  // 获取数组元素的类型
  const itemType = param.items?.type || 'string';
  const itemEnum = param.items?.enum;
  
  return (
    <Form.Item 
      key={key}
      label={param.title || key}
      tooltip={param.description}
      required={isRequired}>
      <Form.List name={['pipeline_config', key]}>
        {(fields, { add, remove }) => (
          <>
            {fields.map(({ key: fieldKey, name, ...restField }) => (
              <Space 
                key={fieldKey} 
                style={{ display: 'flex', marginBottom: 8 }} 
                align="baseline">
                
                {/* 根据数组元素类型渲染不同的输入组件 */}
                {itemType === 'string' && itemEnum ? (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    noStyle
                    rules={[{ required: isRequired, message: '请选择或输入值' }]}>
                    <Select style={{ minWidth: 200 }} placeholder={`选择${param.title || key}`}>
                      {itemEnum.map((v: string) => (
                        <Option key={v} value={v}>{v}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                ) : itemType === 'string' ? (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    noStyle
                    rules={[{ required: isRequired, message: '请输入值' }]}>
                    <Input 
                      style={{ minWidth: 300 }} 
                      placeholder={`输入${param.title || key}`} />
                  </Form.Item>
                ) : itemType === 'number' || itemType === 'integer' ? (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    noStyle
                    rules={[{ required: isRequired, message: '请输入数字' }]}>
                    <InputNumber
                      style={{ minWidth: 150 }}
                      min={param.items?.minimum}
                      max={param.items?.maximum}
                      placeholder={`输入${param.title || key}`} />
                  </Form.Item>
                ) : itemType === 'boolean' ? (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    valuePropName="checked"
                    noStyle>
                    <Switch checkedChildren="是" unCheckedChildren="否" />
                  </Form.Item>
                ) : itemType === 'object' ? (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    noStyle
                    rules={[{ required: isRequired, message: '请输入JSON对象' }]}>
                    <TextArea 
                      style={{ minWidth: 400 }}
                      rows={2}
                      placeholder={`输入JSON对象，如: {"key": "value"}`} />
                  </Form.Item>
                ) : (
                  <Form.Item
                    {...restField}
                    name={[name]}
                    noStyle
                    rules={[{ required: isRequired, message: '请输入值' }]}>
                    <Input 
                      style={{ minWidth: 300 }}
                      placeholder={`输入${param.title || key}`} />
                  </Form.Item>
                )}
                
                {/* 删除按钮 */}
                <MinusCircleOutlined onClick={() => remove(name)} />
              </Space>
            ))}
            
            {/* 添加按钮 */}
            <Form.Item>
              <Button 
                type="dashed" 
                onClick={() => {
                  // 根据类型设置默认值
                  let defaultValue;
                  switch (itemType) {
                    case 'number':
                    case 'integer':
                      defaultValue = param.items?.default || 0;
                      break;
                    case 'boolean':
                      defaultValue = false;
                      break;
                    case 'object':
                      defaultValue = {};
                      break;
                    default:
                      defaultValue = param.items?.default || '';
                  }
                  add(defaultValue);
                }} 
                block 
                icon={<PlusOutlined />}>
                添加 {param.title || key}
              </Button>
            </Form.Item>
            
            {/* 如果有最小/最大限制，显示提示 */}
            {(param.minItems || param.maxItems) && (
              <div style={{ color: '#999', fontSize: 12, marginTop: -12, marginBottom: 12 }}>
                {param.minItems && `最少 ${param.minItems} 项`}
                {param.minItems && param.maxItems && '，'}
                {param.maxItems && `最多 ${param.maxItems} 项`}
              </div>
            )}
          </>
        )}
      </Form.List>
    </Form.Item>
  );
};

/**
 * 渲染对象类型的输入组件
 */
const renderObjectField = (key: string, param: any, isRequired: boolean) => {
  // 如果对象有具体的属性定义，递归渲染
  if (param.properties) {
    return (
      <Card 
        key={key}
        title={param.title || key} 
        size="small"
        style={{ marginBottom: 16 }}>
        {Object.entries(param.properties).map(([subKey, subParam]: [string, any]) => {
          const subRequired = param.required?.includes(subKey);
          return renderField(
            ['pipeline_config', key, subKey], 
            subKey, 
            subParam, 
            subRequired
          );
        })}
      </Card>
    );
  }
  
  // 否则使用JSON文本框
  return (
    <Form.Item
      key={key}
      name={['pipeline_config', key]}
      label={param.title || key}
      rules={[
        { required: isRequired, message: `请输入${param.title || key}` },
        {
          validator: (_, value) => {
            if (!value) return Promise.resolve();
            try {
              if (typeof value === 'string') {
                JSON.parse(value);
              }
              return Promise.resolve();
            } catch (e) {
              return Promise.reject(new Error('请输入有效的JSON对象'));
            }
          }
        }
      ]}
      tooltip={param.description}>
      <TextArea
        rows={4}
        placeholder={`输入JSON对象，例如: ${param.example || '{"key": "value"}'}`}
        onBlur={(e) => {
          // 尝试格式化JSON
          try {
            const value = e.target.value;
            if (value) {
              const parsed = JSON.parse(value);
              e.target.value = JSON.stringify(parsed, null, 2);
            }
          } catch {}
        }} />
    </Form.Item>
  );
};

/**
 * 递归渲染表单字段
 */
const renderField = (
  name: string | string[], 
  key: string, 
  param: any, 
  isRequired: boolean
) => {
  // 处理数组类型
  if (param.type === 'array') {
    return renderArrayField(key, param, isRequired);
  }
  
  // 处理对象类型
  if (param.type === 'object') {
    return renderObjectField(key, param, isRequired);
  }
  
  // 处理基本类型
  switch (param.type) {
    case 'string':
      if (param.enum) {
        return (
          <Form.Item 
            key={key}
            name={Array.isArray(name) ? name : ['pipeline_config', key]} 
            label={param.title || key}
            rules={[{ required: isRequired, message: `请选择${param.title || key}` }]}
            tooltip={param.description}>
            <Select placeholder={`选择${param.title || key}`}>
              {param.enum.map((v: string) => (
                <Option key={v} value={v}>{v}</Option>
              ))}
            </Select>
          </Form.Item>
        );
      }
      // 长文本
      if (param.format === 'textarea' || param.maxLength > 100) {
        return (
          <Form.Item 
            key={key}
            name={Array.isArray(name) ? name : ['pipeline_config', key]} 
            label={param.title || key}
            rules={[
              { required: isRequired, message: `请输入${param.title || key}` },
              param.minLength && { min: param.minLength, message: `最少${param.minLength}个字符` },
              param.maxLength && { max: param.maxLength, message: `最多${param.maxLength}个字符` }
            ].filter(Boolean)}
            tooltip={param.description}>
            <TextArea 
              rows={3}
              maxLength={param.maxLength}
              showCount={!!param.maxLength}
              placeholder={param.description || `请输入${param.title || key}`} />
          </Form.Item>
        );
      }
      return (
        <Form.Item 
          key={key}
          name={Array.isArray(name) ? name : ['pipeline_config', key]} 
          label={param.title || key}
          rules={[
            { required: isRequired, message: `请输入${param.title || key}` },
            param.pattern && { pattern: new RegExp(param.pattern), message: param.patternMessage || '格式不正确' },
            param.minLength && { min: param.minLength, message: `最少${param.minLength}个字符` },
            param.maxLength && { max: param.maxLength, message: `最多${param.maxLength}个字符` }
          ].filter(Boolean)}
          tooltip={param.description}>
          <Input 
            maxLength={param.maxLength}
            placeholder={param.description || `请输入${param.title || key}`} />
        </Form.Item>
      );
    
    case 'integer':
    case 'number':
      return (
        <Form.Item 
          key={key}
          name={Array.isArray(name) ? name : ['pipeline_config', key]} 
          label={param.title || key}
          rules={[
            { required: isRequired, message: `请输入${param.title || key}` },
            { type: 'number', message: '请输入有效的数字' }
          ]}
          tooltip={param.description}>
          <InputNumber 
            min={param.minimum} 
            max={param.maximum}
            step={param.type === 'integer' ? 1 : undefined}
            precision={param.type === 'integer' ? 0 : undefined}
            style={{ width: '100%' }}
            placeholder={param.description || `请输入${param.title || key}`} />
        </Form.Item>
      );
    
    case 'boolean':
      return (
        <Form.Item 
          key={key}
          name={Array.isArray(name) ? name : ['pipeline_config', key]} 
          label={param.title || key}
          valuePropName="checked"
          initialValue={param.default || false}
          tooltip={param.description}>
          <Switch 
            checkedChildren={param.trueText || "是"} 
            unCheckedChildren={param.falseText || "否"} />
        </Form.Item>
      );
    
    default:
      // 默认使用文本输入
      return (
        <Form.Item 
          key={key}
          name={Array.isArray(name) ? name : ['pipeline_config', key]} 
          label={param.title || key}
          rules={[{ required: isRequired, message: `请输入${param.title || key}` }]}
          tooltip={param.description}>
          <Input placeholder={param.description || `请输入${param.title || key}`} />
        </Form.Item>
      );
  }
};

/**
 * 主组件：渲染Pipeline参数表单
 */
export const renderPipelineParams = (schema: any) => {
  if (!schema || !schema.properties) return null;
  
  return (
    <>
      {Object.entries(schema.properties).map(([key, param]: [string, any]) => {
        const isRequired = schema.required?.includes(key);
        return renderField(['pipeline_config', key], key, param, isRequired);
      })}
    </>
  );
};

// 使用示例
const PipelineConfigForm: React.FC<{ schema: any }> = ({ schema }) => {
  const [form] = Form.useForm();
  
  const handleSubmit = async (values: any) => {
    try {
      // 处理数组和对象类型的数据
      const processedConfig = processConfigValues(values.pipeline_config);
      console.log('Processed config:', processedConfig);
      
      // 提交到后端
      await createPublishConfig({
        ...values,
        pipeline_config: processedConfig
      });
      
      message.success('配置创建成功');
    } catch (error) {
      message.error('配置创建失败');
    }
  };
  
  // 处理配置值，确保正确的类型
  const processConfigValues = (config: any) => {
    if (!config) return config;
    
    const processed: any = {};
    
    Object.entries(config).forEach(([key, value]) => {
      // 如果是字符串但应该是JSON对象，尝试解析
      if (typeof value === 'string' && schema.properties[key]?.type === 'object') {
        try {
          processed[key] = JSON.parse(value);
        } catch {
          processed[key] = value;
        }
      } else {
        processed[key] = value;
      }
    });
    
    return processed;
  };
  
  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        pipeline_config: schema.default || {}
      }}>
      
      {renderPipelineParams(schema)}
      
      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit">
            提交配置
          </Button>
          <Button onClick={() => form.resetFields()}>
            重置
          </Button>
          <Button 
            onClick={() => {
              // 预览当前表单值
              const values = form.getFieldsValue();
              console.log('Current form values:', values);
              Modal.info({
                title: 'Pipeline配置预览',
                content: (
                  <pre style={{ maxHeight: 400, overflow: 'auto' }}>
                    {JSON.stringify(values.pipeline_config, null, 2)}
                  </pre>
                ),
                width: 600
              });
            }}>
            预览JSON
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
};
```

## 示例：Pipeline Schema配置

```typescript
// 示例Pipeline的配置schema
const examplePipelineSchema = {
  type: 'object',
  title: 'Story Full Pipeline配置',
  properties: {
    // 字符串数组示例（创作者列表）
    creator_list: {
      type: 'array',
      title: '创作者列表',
      description: '按优先级排序的创作者ID列表',
      items: {
        type: 'string',
        description: '创作者ID或handle'
      },
      minItems: 1,
      maxItems: 10,
      default: []
    },
    
    // 枚举数组示例
    enabled_stages: {
      type: 'array',
      title: '启用的阶段',
      description: '选择要启用的处理阶段',
      items: {
        type: 'string',
        enum: ['story', 'tts', 'draft', 'video_export', 'publish']
      },
      default: ['story', 'tts', 'draft']
    },
    
    // 数字数组示例
    priority_weights: {
      type: 'array',
      title: '优先级权重',
      description: '每个创作者的优先级权重',
      items: {
        type: 'number',
        minimum: 0,
        maximum: 100
      },
      default: [100, 80, 60]
    },
    
    // 对象数组示例
    custom_params: {
      type: 'array',
      title: '自定义参数',
      description: '额外的配置参数',
      items: {
        type: 'object',
        properties: {
          key: {
            type: 'string',
            title: '参数名'
          },
          value: {
            type: 'string',
            title: '参数值'
          }
        },
        required: ['key', 'value']
      }
    },
    
    // 单个字符串
    account_id: {
      type: 'string',
      title: '账号ID',
      description: '用于发布的YouTube账号ID',
      pattern: '^yt_[0-9]+_[a-z]+_[0-9]+$',
      patternMessage: '账号ID格式：yt_xxx_xxx_xxx'
    },
    
    // 单个数字
    duration: {
      type: 'integer',
      title: '视频时长',
      description: '目标视频时长（秒）',
      minimum: 60,
      maximum: 600,
      default: 300
    },
    
    // 布尔值
    enable_subtitle: {
      type: 'boolean',
      title: '启用字幕',
      description: '是否生成字幕',
      default: false,
      trueText: '启用',
      falseText: '禁用'
    },
    
    // 嵌套对象
    video_fetch_config: {
      type: 'object',
      title: '视频获取配置',
      properties: {
        days_back: {
          type: 'integer',
          title: '回溯天数',
          description: '获取最近N天的视频',
          minimum: 1,
          maximum: 30,
          default: 7
        },
        max_videos: {
          type: 'integer',
          title: '最大视频数',
          description: '每个创作者最多检查的视频数',
          minimum: 1,
          maximum: 50,
          default: 10
        }
      }
    }
  },
  required: ['creator_list', 'account_id']
};
```

## 表单数据处理

### 前端提交时的数据转换

```typescript
// utils/formDataProcessor.ts
export const processFormData = (formValues: any, schema: any) => {
  const processed: any = {};
  
  Object.entries(formValues).forEach(([key, value]) => {
    const fieldSchema = schema.properties[key];
    
    if (!fieldSchema) {
      processed[key] = value;
      return;
    }
    
    switch (fieldSchema.type) {
      case 'array':
        // 确保数组类型正确
        processed[key] = Array.isArray(value) ? value : [];
        break;
      
      case 'object':
        // 如果是字符串，尝试解析为JSON
        if (typeof value === 'string') {
          try {
            processed[key] = JSON.parse(value);
          } catch {
            processed[key] = {};
          }
        } else {
          processed[key] = value || {};
        }
        break;
      
      case 'integer':
        processed[key] = parseInt(value) || 0;
        break;
      
      case 'number':
        processed[key] = parseFloat(value) || 0;
        break;
      
      case 'boolean':
        processed[key] = !!value;
        break;
      
      default:
        processed[key] = value;
    }
  });
  
  return processed;
};
```

### 后端接收时的数据验证

```python
# utils/schema_validator.py
def validate_pipeline_config(schema: dict, config: dict) -> bool:
    """验证Pipeline配置是否符合schema"""
    
    # 检查必需字段
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # 验证每个字段
    properties = schema.get('properties', {})
    for key, value in config.items():
        if key not in properties:
            continue  # 忽略未定义的字段
        
        field_schema = properties[key]
        validate_field(key, value, field_schema)
    
    return True

def validate_field(key: str, value: any, schema: dict):
    """验证单个字段"""
    field_type = schema.get('type')
    
    # 类型验证
    if field_type == 'array':
        if not isinstance(value, list):
            raise ValueError(f"{key} must be an array")
        
        # 验证数组元素
        items_schema = schema.get('items')
        if items_schema:
            for i, item in enumerate(value):
                validate_field(f"{key}[{i}]", item, items_schema)
        
        # 验证数组长度
        min_items = schema.get('minItems')
        max_items = schema.get('maxItems')
        if min_items and len(value) < min_items:
            raise ValueError(f"{key} must have at least {min_items} items")
        if max_items and len(value) > max_items:
            raise ValueError(f"{key} must have at most {max_items} items")
    
    elif field_type == 'object':
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        
        # 递归验证对象属性
        if 'properties' in schema:
            validate_pipeline_config(schema, value)
    
    elif field_type == 'string':
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        
        # 验证枚举值
        enum = schema.get('enum')
        if enum and value not in enum:
            raise ValueError(f"{key} must be one of {enum}")
        
        # 验证正则表达式
        pattern = schema.get('pattern')
        if pattern:
            import re
            if not re.match(pattern, value):
                raise ValueError(f"{key} does not match pattern {pattern}")
    
    elif field_type in ('integer', 'number'):
        if not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a number")
        
        # 验证范围
        minimum = schema.get('minimum')
        maximum = schema.get('maximum')
        if minimum is not None and value < minimum:
            raise ValueError(f"{key} must be >= {minimum}")
        if maximum is not None and value > maximum:
            raise ValueError(f"{key} must be <= {maximum}")
    
    elif field_type == 'boolean':
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
```

## 关键改进点

1. **数组输入优化**
   - 使用 `Form.List` 组件实现动态数组输入
   - 支持添加/删除数组项
   - 根据数组元素类型渲染相应的输入组件

2. **类型支持完善**
   - 支持所有JSON Schema基本类型
   - 支持嵌套对象和数组
   - 支持枚举、范围限制等验证规则

3. **用户体验提升**
   - 清晰的添加/删除按钮
   - 实时的表单验证
   - JSON预览功能
   - 格式化JSON输入

4. **数据处理**
   - 前端自动转换数据类型
   - 后端严格验证数据格式
   - 错误信息清晰明确

这样用户就可以通过友好的界面配置数组参数，而不需要手动输入JSON字符串了。