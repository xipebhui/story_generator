import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Button,
  Space,
  Alert,
  Divider,
  Tooltip,
  Row,
  Col,
  Card
} from 'antd';
import {
  InfoCircleOutlined,
  SendOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { workflows, getWorkflowConfig, getWorkflowDefaults } from '../../config/workflows';
import { pipelineAdapter } from '../../services/pipelineAdapter';
import { PipelineRequest } from '../../types/api';
import { backendAccountService } from '../../services/backend';
import { YouTubeAccount, ImageLibrary } from '../../services/backend';

interface CreateTaskModalProps {
  visible: boolean;
  workflowKey?: string;
  onClose: () => void;
  onSuccess: (taskId: string) => void;
}

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
  visible,
  workflowKey,
  onClose,
  onSuccess
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>(workflowKey || '');
  const [accounts, setAccounts] = useState<YouTubeAccount[]>([]);
  const [imageLibraries, setImageLibraries] = useState<ImageLibrary[]>([]);

  // 加载账号列表和图库列表
  useEffect(() => {
    if (visible) {
      loadAccounts();
      loadImageLibraries();
    }
  }, [visible]);

  // 当workflowKey变化时更新选中的工作流
  useEffect(() => {
    if (workflowKey) {
      setSelectedWorkflow(workflowKey);
      // 设置默认值
      const defaults = getWorkflowDefaults(workflowKey);
      form.setFieldsValue(defaults);
    }
  }, [workflowKey, form]);
  
  // 加载账号列表
  const loadAccounts = async () => {
    try {
      const accountList = await backendAccountService.getAccounts();
      // 只保留激活的账号
      const activeAccounts = accountList.filter((acc: any) => acc.is_active);
      setAccounts(activeAccounts);
    } catch (error) {
      console.error('加载账号列表失败:', error);
      setAccounts([]);
    }
  };

  // 加载图库列表
  const loadImageLibraries = async () => {
    try {
      const libraries = await backendAccountService.getImageLibraries();
      setImageLibraries(libraries);
      
      // 如果有图库，设置默认选中第一个
      if (libraries.length > 0 && !form.getFieldValue('image_library')) {
        form.setFieldValue('image_library', libraries[0].library_name);
      }
    } catch (error) {
      console.error('加载图库列表失败:', error);
      setImageLibraries([]);
    }
  };

  // 获取当前工作流配置
  const currentWorkflow = getWorkflowConfig(selectedWorkflow);

  // 处理工作流切换
  const handleWorkflowChange = (key: string) => {
    setSelectedWorkflow(key);
    // 重置表单并设置新的默认值
    form.resetFields();
    const defaults = getWorkflowDefaults(key);
    form.setFieldsValue(defaults);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 构建请求参数
      const request: PipelineRequest = {
        video_id: values.video_id,
        creator_id: values.creator_id,
        account_name: values.account_name,  // 添加账号名称
        gender: values.gender || 1,
        duration: values.duration || 60,
        image_dir: values.image_dir,
        image_library: values.image_library,  // 添加图库名称
        export_video: values.export_video !== undefined ? values.export_video : true,
        enable_subtitle: values.enable_subtitle !== undefined ? values.enable_subtitle : true,
        // 添加工作流特定参数
        workflow_type: selectedWorkflow,
        ...values
      };

      // 使用适配器创建任务
      const task = await pipelineAdapter.createTask(selectedWorkflow, values);
      onSuccess(task.task_id);
    } catch (error: any) {
      console.error('创建任务失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 渲染表单字段
  const renderFormField = (field: any) => {
    const commonProps = {
      label: (
        <Space>
          {field.icon}
          {field.label}
          {field.tooltip && (
            <Tooltip title={field.tooltip}>
              <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
            </Tooltip>
          )}
        </Space>
      ),
      name: field.name,
      rules: field.required ? [{ required: true, message: `请输入${field.label}` }] : []
    };

    switch (field.type) {
      case 'text':
        return (
          <Form.Item {...commonProps}>
            <Input placeholder={field.placeholder} />
          </Form.Item>
        );
      
      case 'select':
        // 如果是账号选择字段，使用动态加载的账号列表
        if (field.name === 'account_name') {
          return (
            <Form.Item {...commonProps}>
              <Select 
                placeholder={field.placeholder || `请选择${field.label}`}
                allowClear
              >
                {accounts.map(account => (
                  <Select.Option key={account.account_name} value={account.account_name}>
                    {account.display_name || account.account_name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          );
        }
        // 如果是图库选择字段，使用动态加载的图库列表
        if (field.name === 'image_library') {
          return (
            <Form.Item {...commonProps}>
              <Select 
                placeholder={field.placeholder || `请选择${field.label}`}
                allowClear={false}
              >
                {imageLibraries.map(library => (
                  <Select.Option 
                    key={library.library_name} 
                    value={library.library_name}
                  >
                    <Tooltip title={library.library_path}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{library.library_name}</span>
                        <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                          {library.library_path.split('/').slice(-2).join('/')}
                        </span>
                      </div>
                    </Tooltip>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          );
        }
        return (
          <Form.Item {...commonProps}>
            <Select placeholder={`请选择${field.label}`}>
              {field.options?.map((option: any) => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
                ))}
            </Select>
          </Form.Item>
        );
      
      case 'number':
        return (
          <Form.Item {...commonProps}>
            <InputNumber
              min={field.min}
              max={field.max}
              style={{ width: '100%' }}
              placeholder={field.placeholder}
            />
          </Form.Item>
        );
      
      case 'switch':
        return (
          <Form.Item {...commonProps} valuePropName="checked">
            <Switch />
          </Form.Item>
        );
      
      case 'folder':
        // 如果是image_dir字段，改为图库选择
        if (field.name === 'image_dir') {
          return (
            <Form.Item 
              {...commonProps}
              name="image_library"
              label={
                <Space>
                  {field.icon}
                  图库选择
                  <Tooltip title="选择需要使用的图片库">
                    <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                  </Tooltip>
                </Space>
              }
            >
              <Select 
                placeholder="请选择图库"
                allowClear={false}
              >
                {imageLibraries.map(library => (
                  <Select.Option 
                    key={library.library_name} 
                    value={library.library_name}
                  >
                    <Tooltip title={library.library_path}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{library.library_name}</span>
                        <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                          {library.library_path.split('/').slice(-2).join('/')}
                        </span>
                      </div>
                    </Tooltip>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          );
        }
        return (
          <Form.Item {...commonProps}>
            <Input placeholder={field.placeholder} />
          </Form.Item>
        );
      
      default:
        return null;
    }
  };

  return (
    <Modal
      title={
        <div style={{ 
          fontSize: 20, 
          fontWeight: 600,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          创建任务
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={720}
      footer={null}
      className="beautiful-modal"
    >
      <Space direction="vertical" size={24} style={{ width: '100%' }}>
        {/* 工作流选择 */}
        {!workflowKey && (
          <>
            <div>
              <div style={{ marginBottom: 12, fontWeight: 500 }}>
                选择工作流类型
              </div>
              <Row gutter={12}>
                {workflows.map(workflow => (
                  <Col span={8} key={workflow.key}>
                    <Card
                      hoverable
                      className={selectedWorkflow === workflow.key ? 'selected-card' : ''}
                      onClick={() => handleWorkflowChange(workflow.key)}
                      style={{
                        borderColor: selectedWorkflow === workflow.key ? workflow.color : undefined,
                        borderWidth: selectedWorkflow === workflow.key ? 2 : 1
                      }}
                    >
                      <Space direction="vertical" align="center" style={{ width: '100%' }}>
                        <div style={{ 
                          fontSize: 32,
                          background: workflow.gradient,
                          backgroundClip: 'text',
                          WebkitBackgroundClip: 'text',
                          WebkitTextFillColor: 'transparent'
                        }}>
                          {workflow.icon}
                        </div>
                        <div style={{ fontWeight: 500 }}>{workflow.name}</div>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </div>
            <Divider />
          </>
        )}

        {/* 当前选中的工作流信息 */}
        {currentWorkflow && (
          <Alert
            message={currentWorkflow.name}
            description={currentWorkflow.description}
            type="info"
            showIcon
            icon={currentWorkflow.icon}
          />
        )}

        {/* 表单 */}
        {currentWorkflow && (
          <Form
            form={form}
            layout="vertical"
            initialValues={getWorkflowDefaults(selectedWorkflow)}
          >
            <Row gutter={16}>
              {currentWorkflow.fields.map(field => (
                <Col span={field.type === 'switch' ? 12 : 24} key={field.name}>
                  {renderFormField(field)}
                </Col>
              ))}
            </Row>
          </Form>
        )}

        {/* 操作按钮 */}
        <Row justify="end">
          <Space>
            <Button onClick={onClose} icon={<CloseOutlined />}>
              取消
            </Button>
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
              icon={<SendOutlined />}
              disabled={!currentWorkflow}
              className="gradient-button"
            >
              开始创作
            </Button>
          </Space>
        </Row>
      </Space>
    </Modal>
  );
};

export default CreateTaskModal;