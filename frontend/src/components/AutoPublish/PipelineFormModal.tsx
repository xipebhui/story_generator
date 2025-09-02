import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, Select, Radio, Button, Space, message, Tabs, Alert } from 'antd';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import SchemaFormBuilder from './SchemaFormBuilder';

const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface PipelineFormModalProps {
  visible: boolean;
  pipeline: any | null;
  onCancel: () => void;
  onOk: (values: any) => void;
}

const PipelineFormModal: React.FC<PipelineFormModalProps> = ({
  visible,
  pipeline,
  onCancel,
  onOk
}) => {
  const [form] = Form.useForm();
  const [configSchema, setConfigSchema] = useState<any>({});

  // 初始化表单
  useEffect(() => {
    if (visible) {
      if (pipeline) {
        form.setFieldsValue({
          ...pipeline,
          supported_platforms: pipeline.supported_platforms || ['youtube']
        });
        setConfigSchema(pipeline.config_schema || {});
      } else {
        form.resetFields();
        form.setFieldsValue({
          pipeline_type: 'content_generation',
          supported_platforms: ['youtube'],
          version: '1.0.0',
          status: 'testing'
        });
        setConfigSchema({
          type: 'object',
          properties: {},
          required: []
        });
      }
    }
  }, [visible, pipeline, form]);

  // 验证并提交
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // 构造提交数据
      const submitData = {
        ...values,
        config_schema: configSchema
      };

      onOk(submitData);
    } catch (error) {
      console.error('Form validation failed:', error);
    }
  };


  return (
    <Modal
      title={pipeline ? '编辑Pipeline' : '创建Pipeline'}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      width={800}
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        autoComplete="off"
      >
        <Tabs defaultActiveKey="basic">
          <TabPane tab="基本信息" key="basic">
            <Form.Item
              name="pipeline_id"
              label="Pipeline ID"
              rules={[
                { required: true, message: '请输入Pipeline ID' },
                { pattern: /^[a-z0-9_]+$/, message: '只能包含小写字母、数字和下划线' },
                { min: 3, max: 50, message: '长度3-50个字符' }
              ]}
              extra="格式：小写字母、数字和下划线，如 youtube_story_v3"
            >
              <Input placeholder="例如：youtube_story_v3" disabled={!!pipeline} />
            </Form.Item>

            <Form.Item
              name="pipeline_name"
              label="Pipeline名称"
              rules={[
                { required: true, message: '请输入Pipeline名称' },
                { max: 100, message: '最多100个字符' }
              ]}
            >
              <Input placeholder="例如：YouTube故事生成V3" />
            </Form.Item>

            <Form.Item
              name="pipeline_type"
              label="Pipeline类型"
              rules={[{ required: true, message: '请选择Pipeline类型' }]}
            >
              <Select>
                <Option value="content_generation">内容生成</Option>
                <Option value="metadata">元数据</Option>
                <Option value="processing">后处理</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="pipeline_class"
              label="Python类路径"
              rules={[
                { required: true, message: '请输入Python类路径' },
                { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$/, 
                  message: '请输入有效的Python类路径' }
              ]}
              extra="格式：module.ClassName，如 story_pipeline_v3_runner.StoryPipelineV3"
            >
              <Input placeholder="例如：story_pipeline_v3_runner.StoryPipelineV3" />
            </Form.Item>

            <Form.Item
              name="supported_platforms"
              label="支持平台"
              rules={[{ required: true, message: '请选择支持平台' }]}
            >
              <Select mode="multiple" disabled>
                <Option value="youtube">YouTube</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="version"
              label="版本号"
              rules={[
                { required: true, message: '请输入版本号' },
                { pattern: /^v?\d+\.\d+\.\d+$/, message: '格式：v1.0.0 或 1.0.0' }
              ]}
            >
              <Input placeholder="例如：1.0.0" />
            </Form.Item>

            <Form.Item
              name="status"
              label="状态"
              rules={[{ required: true, message: '请选择状态' }]}
            >
              <Radio.Group>
                <Radio value="testing">测试中</Radio>
                <Radio value="active">启用</Radio>
                <Radio value="inactive">停用</Radio>
              </Radio.Group>
            </Form.Item>
          </TabPane>

          <TabPane tab="参数配置" key="schema">
            <Alert
              message="参数配置定义"
              description="通过表单方式定义Pipeline的参数结构，系统会自动组装成JSON Schema格式"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <SchemaFormBuilder
              value={configSchema}
              onChange={setConfigSchema}
            />
          </TabPane>
        </Tabs>
      </Form>
    </Modal>
  );
};

export default PipelineFormModal;