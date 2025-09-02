import React, { useState, useEffect } from 'react';
import { Form, Input, Select, InputNumber, Switch, Button, Space, Card, Tooltip, message } from 'antd';
import { PlusOutlined, DeleteOutlined, QuestionCircleOutlined } from '@ant-design/icons';

const { Option } = Select;

interface SchemaField {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: any;
  minimum?: number;
  maximum?: number;
  enum?: string[];
}

interface SchemaFormBuilderProps {
  value?: any;
  onChange?: (value: any) => void;
}

const SchemaFormBuilder: React.FC<SchemaFormBuilderProps> = ({ value, onChange }) => {
  const [fields, setFields] = useState<SchemaField[]>([]);

  // 从JSON Schema解析字段
  useEffect(() => {
    if (value && typeof value === 'object') {
      const properties = value.properties || {};
      const required = value.required || [];
      
      const parsedFields: SchemaField[] = Object.keys(properties).map(key => {
        const prop = properties[key];
        return {
          name: key,
          type: prop.type || 'string',
          description: prop.description || '',
          required: required.includes(key) || prop.required === true,
          default: prop.default,
          minimum: prop.minimum,
          maximum: prop.maximum,
          enum: prop.enum
        };
      });
      
      setFields(parsedFields);
    }
  }, [value]);

  // 添加新字段
  const addField = () => {
    const newField: SchemaField = {
      name: `field_${fields.length + 1}`,
      type: 'string',
      description: '',
      required: false
    };
    const newFields = [...fields, newField];
    setFields(newFields);
    updateSchema(newFields);
  };

  // 删除字段
  const removeField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
    updateSchema(newFields);
  };

  // 更新字段
  const updateField = (index: number, field: Partial<SchemaField>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...field };
    setFields(newFields);
    updateSchema(newFields);
  };

  // 组装成JSON Schema
  const updateSchema = (fieldsToUpdate: SchemaField[]) => {
    const properties: any = {};
    const required: string[] = [];
    
    fieldsToUpdate.forEach(field => {
      const prop: any = {
        type: field.type,
        description: field.description
      };
      
      if (field.required) {
        required.push(field.name);
        prop.required = true;
      }
      
      if (field.default !== undefined && field.default !== '') {
        prop.default = field.type === 'number' ? Number(field.default) : 
                       field.type === 'boolean' ? Boolean(field.default) : 
                       field.default;
      }
      
      if (field.type === 'number') {
        if (field.minimum !== undefined) prop.minimum = field.minimum;
        if (field.maximum !== undefined) prop.maximum = field.maximum;
      }
      
      if (field.enum && field.enum.length > 0) {
        prop.enum = field.enum;
      }
      
      properties[field.name] = prop;
    });
    
    const schema = {
      type: 'object',
      properties,
      required: required.length > 0 ? required : undefined
    };
    
    if (onChange) {
      onChange(schema);
    }
  };

  // 生成示例字段
  const generateExample = () => {
    const exampleFields: SchemaField[] = [
      {
        name: 'video_id',
        type: 'string',
        description: '视频ID',
        required: true
      },
      {
        name: 'image_library',
        type: 'string',
        description: '图库名称',
        required: false,
        default: 'default_library'
      },
      {
        name: 'duration_per_image',
        type: 'number',
        description: '单张图片持续时间（秒）',
        required: false,
        default: 3,
        minimum: 1,
        maximum: 10
      },
      {
        name: 'enable_subtitles',
        type: 'boolean',
        description: '是否启用字幕',
        required: false,
        default: true
      }
    ];
    
    setFields(exampleFields);
    updateSchema(exampleFields);
    message.success('已生成示例Schema');
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<PlusOutlined />} onClick={addField}>
            添加字段
          </Button>
          <Button onClick={generateExample}>
            生成示例
          </Button>
        </Space>
      </div>

      {fields.map((field, index) => (
        <Card 
          key={index} 
          size="small" 
          style={{ marginBottom: 16 }}
          extra={
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => removeField(index)}
            />
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space style={{ width: '100%' }} align="baseline">
              <Input
                placeholder="字段名称"
                value={field.name}
                onChange={e => updateField(index, { name: e.target.value })}
                style={{ width: 200 }}
                addonBefore="名称"
              />
              
              <Select
                value={field.type}
                onChange={type => updateField(index, { type })}
                style={{ width: 120 }}
              >
                <Option value="string">字符串</Option>
                <Option value="number">数字</Option>
                <Option value="boolean">布尔值</Option>
                <Option value="array">数组</Option>
                <Option value="object">对象</Option>
              </Select>

              <Switch
                checked={field.required}
                onChange={required => updateField(index, { required })}
                checkedChildren="必填"
                unCheckedChildren="选填"
              />
            </Space>

            <Input
              placeholder="字段描述"
              value={field.description}
              onChange={e => updateField(index, { description: e.target.value })}
              addonBefore="描述"
            />

            {field.type === 'string' && (
              <Input
                placeholder="默认值"
                value={field.default}
                onChange={e => updateField(index, { default: e.target.value })}
                addonBefore="默认"
              />
            )}

            {field.type === 'number' && (
              <Space>
                <InputNumber
                  placeholder="默认值"
                  value={field.default}
                  onChange={default_value => updateField(index, { default: default_value })}
                  addonBefore="默认"
                  style={{ width: 150 }}
                />
                <InputNumber
                  placeholder="最小值"
                  value={field.minimum}
                  onChange={minimum => updateField(index, { minimum })}
                  addonBefore="最小"
                  style={{ width: 150 }}
                />
                <InputNumber
                  placeholder="最大值"
                  value={field.maximum}
                  onChange={maximum => updateField(index, { maximum })}
                  addonBefore="最大"
                  style={{ width: 150 }}
                />
              </Space>
            )}

            {field.type === 'boolean' && (
              <Space>
                <span>默认值：</span>
                <Switch
                  checked={field.default}
                  onChange={checked => updateField(index, { default: checked })}
                  checkedChildren="True"
                  unCheckedChildren="False"
                />
              </Space>
            )}

            {field.type === 'string' && (
              <Input
                placeholder="枚举值（用逗号分隔，如: small,medium,large）"
                value={field.enum?.join(',')}
                onChange={e => {
                  const values = e.target.value ? e.target.value.split(',').map(v => v.trim()) : [];
                  updateField(index, { enum: values.length > 0 ? values : undefined });
                }}
                addonBefore={
                  <Tooltip title="如果设置了枚举值，字段将只能选择这些值">
                    枚举 <QuestionCircleOutlined />
                  </Tooltip>
                }
              />
            )}
          </Space>
        </Card>
      ))}

      {fields.length === 0 && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: '#999' }}>暂无字段，点击"添加字段"或"生成示例"开始配置</p>
        </Card>
      )}
    </div>
  );
};

export default SchemaFormBuilder;