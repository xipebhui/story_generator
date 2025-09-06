import React, { useEffect, useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Radio,
  TimePicker,
  DatePicker,
  Switch,
  Tabs,
  Space,
  Button,
  Alert,
  Divider,
  Row,
  Col,
  Card,
  Tag
} from 'antd';
import {
  ClockCircleOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  CalendarOutlined,
  FieldTimeOutlined,
  PlusOutlined,
  MinusCircleOutlined
} from '@ant-design/icons';
import moment from 'moment';
import { autoPublishService } from '../../services/autoPublish';

const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

interface ConfigFormModalProps {
  visible: boolean;
  config: any | null;
  pipelines: any[];
  groups: any[];
  onSave: (values: any) => void;
  onCancel: () => void;
}

const ConfigFormModal: React.FC<ConfigFormModalProps> = ({
  visible,
  config,
  pipelines,
  groups,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [triggerType, setTriggerType] = useState('scheduled');
  const [scheduleType, setScheduleType] = useState('daily');
  const [selectedPipeline, setSelectedPipeline] = useState<any>(null);
  const [pipelineParams, setPipelineParams] = useState<any>({});

  useEffect(() => {
    if (visible) {
      if (config) {
        // 编辑模式：加载现有配置
        form.setFieldsValue({
          config_name: config.config_name,
          group_id: config.group_id,
          pipeline_id: config.pipeline_id,
          trigger_type: config.trigger_type,
          priority: config.priority,
          strategy_id: config.strategy_id
        });
        
        setTriggerType(config.trigger_type);
        
        // 解析触发配置
        if (config.trigger_config) {
          const triggerConfig = config.trigger_config;
          if (config.trigger_type === 'scheduled') {
            setScheduleType(triggerConfig.schedule_type || 'daily');
            form.setFieldsValue({
              schedule_type: triggerConfig.schedule_type,
              schedule_time: triggerConfig.time ? moment(triggerConfig.time, 'HH:mm') : undefined,
              schedule_days: triggerConfig.days,
              schedule_dates: triggerConfig.dates,
              schedule_interval: triggerConfig.interval,
              schedule_cron: triggerConfig.cron
            });
          }
        }
        
        // 设置Pipeline参数
        const pipeline = pipelines.find(p => p.pipeline_id === config.pipeline_id);
        setSelectedPipeline(pipeline);
        if (config.pipeline_params) {
          setPipelineParams(config.pipeline_params);
        }
      } else {
        // 创建模式：重置表单
        form.resetFields();
        setTriggerType('scheduled');
        setScheduleType('daily');
        setPipelineParams({});
        setSelectedPipeline(null);
      }
    }
  }, [visible, config, form, pipelines]);

  // Pipeline变更处理
  const handlePipelineChange = (pipelineId: string) => {
    const pipeline = pipelines.find(p => p.pipeline_id === pipelineId);
    setSelectedPipeline(pipeline);
    
    // 根据Pipeline的Schema初始化参数
    if (pipeline?.config_schema?.properties) {
      const defaultParams: any = {};
      Object.entries(pipeline.config_schema.properties).forEach(([key, prop]: [string, any]) => {
        if (prop.default !== undefined) {
          defaultParams[key] = prop.default;
        } else if (prop.type === 'array') {
          // 为数组类型设置空数组作为默认值
          defaultParams[key] = [];
        }
      });
      setPipelineParams(defaultParams);
    } else {
      setPipelineParams({});
    }
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 构建触发配置
      let triggerConfig: any = {};
      if (values.trigger_type === 'scheduled') {
        triggerConfig.schedule_type = values.schedule_type;
        triggerConfig.timezone = 'Asia/Shanghai';
        
        switch (values.schedule_type) {
          case 'daily':
            triggerConfig.time = values.schedule_time?.format('HH:mm');
            break;
          case 'weekly':
            triggerConfig.days = values.schedule_days;
            triggerConfig.time = values.schedule_time?.format('HH:mm');
            break;
          case 'monthly':
            triggerConfig.dates = values.schedule_dates;
            triggerConfig.time = values.schedule_time?.format('HH:mm');
            break;
          case 'interval':
            triggerConfig.interval = values.schedule_interval;
            triggerConfig.unit = values.schedule_interval_unit || 'hours';
            break;
          case 'cron':
            triggerConfig.cron = values.schedule_cron;
            break;
        }
      } else if (values.trigger_type === 'event') {
        triggerConfig.event_type = values.event_type;
        triggerConfig.event_filter = values.event_filter;
      }
      
      // 构建最终数据
      const submitData = {
        config_name: values.config_name,
        group_id: values.group_id,
        pipeline_id: values.pipeline_id,
        trigger_type: values.trigger_type,
        trigger_config: triggerConfig,
        strategy_id: values.strategy_id,
        priority: values.priority || 50,
        pipeline_params: pipelineParams
      };
      
      onSave(submitData);
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  // 渲染Pipeline参数表单
  const renderPipelineParams = () => {
    if (!selectedPipeline?.config_schema?.properties) {
      return <Alert message="选中的Pipeline没有配置参数" type="info" />;
    }
    
    const properties = selectedPipeline.config_schema.properties;
    const required = selectedPipeline.config_schema.required || [];
    
    return (
      <Card title="Pipeline参数配置" size="small">
        <Form layout="vertical">
          {Object.entries(properties).map(([key, prop]: [string, any]) => {
            const isRequired = required.includes(key) || prop.required;
            
            // 根据类型渲染不同的输入组件
            const renderInput = () => {
              if (prop.enum) {
                return (
                  <Select
                    value={pipelineParams[key]}
                    onChange={(value) => setPipelineParams({ ...pipelineParams, [key]: value })}
                  >
                    {prop.enum.map((option: string) => (
                      <Option key={option} value={option}>{option}</Option>
                    ))}
                  </Select>
                );
              }
              
              switch (prop.type) {
                case 'string':
                  return (
                    <Input
                      value={pipelineParams[key]}
                      onChange={(e) => setPipelineParams({ ...pipelineParams, [key]: e.target.value })}
                      placeholder={prop.description}
                    />
                  );
                case 'number':
                  return (
                    <InputNumber
                      value={pipelineParams[key]}
                      onChange={(value) => setPipelineParams({ ...pipelineParams, [key]: value })}
                      min={prop.minimum}
                      max={prop.maximum}
                      style={{ width: '100%' }}
                    />
                  );
                case 'boolean':
                  return (
                    <Switch
                      checked={pipelineParams[key]}
                      onChange={(checked) => setPipelineParams({ ...pipelineParams, [key]: checked })}
                    />
                  );
                case 'array':
                  // 动态数组输入
                  const arrayValue = pipelineParams[key] || [];
                  return (
                    <div>
                      {arrayValue.map((item: any, index: number) => (
                        <Space key={index} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                          <Input
                            value={item}
                            onChange={(e) => {
                              const newArray = [...arrayValue];
                              newArray[index] = e.target.value;
                              setPipelineParams({ ...pipelineParams, [key]: newArray });
                            }}
                            placeholder={`输入${prop.title || key} #${index + 1}`}
                            style={{ width: 300 }}
                          />
                          <MinusCircleOutlined
                            onClick={() => {
                              const newArray = arrayValue.filter((_: any, i: number) => i !== index);
                              setPipelineParams({ ...pipelineParams, [key]: newArray });
                            }}
                            style={{ color: '#ff4d4f', cursor: 'pointer' }}
                          />
                        </Space>
                      ))}
                      <Button
                        type="dashed"
                        onClick={() => {
                          const newArray = [...arrayValue, ''];
                          setPipelineParams({ ...pipelineParams, [key]: newArray });
                        }}
                        block
                        icon={<PlusOutlined />}
                      >
                        添加 {prop.title || key}
                      </Button>
                    </div>
                  );
                default:
                  // 对象或其他复杂类型，仍使用JSON输入
                  return (
                    <TextArea
                      value={pipelineParams[key] ? JSON.stringify(pipelineParams[key]) : ''}
                      onChange={(e) => {
                        try {
                          const value = JSON.parse(e.target.value);
                          setPipelineParams({ ...pipelineParams, [key]: value });
                        } catch {
                          // 忽略JSON解析错误
                        }
                      }}
                      placeholder={`JSON格式 (${prop.type})`}
                      rows={3}
                    />
                  );
              }
            };
            
            return (
              <Form.Item
                key={key}
                label={
                  <span>
                    {key} {isRequired && <span style={{ color: 'red' }}>*</span>}
                  </span>
                }
                help={prop.description}
              >
                {renderInput()}
              </Form.Item>
            );
          })}
        </Form>
      </Card>
    );
  };

  // 渲染触发配置
  const renderTriggerConfig = () => {
    if (triggerType === 'scheduled') {
      return (
        <Card title="定时触发配置" size="small">
          <Form.Item label="调度类型" name="schedule_type">
            <Radio.Group onChange={(e) => setScheduleType(e.target.value)}>
              <Radio value="daily">每天</Radio>
              <Radio value="weekly">每周</Radio>
              <Radio value="monthly">每月</Radio>
              <Radio value="interval">间隔</Radio>
              <Radio value="cron">Cron表达式</Radio>
            </Radio.Group>
          </Form.Item>
          
          {scheduleType === 'daily' && (
            <Form.Item
              label="执行时间"
              name="schedule_time"
              rules={[{ required: true, message: '请选择执行时间' }]}
            >
              <TimePicker format="HH:mm" />
            </Form.Item>
          )}
          
          {scheduleType === 'weekly' && (
            <>
              <Form.Item
                label="执行日期"
                name="schedule_days"
                rules={[{ required: true, message: '请选择执行日期' }]}
              >
                <Select mode="multiple" placeholder="选择星期几">
                  <Option value={1}>星期一</Option>
                  <Option value={2}>星期二</Option>
                  <Option value={3}>星期三</Option>
                  <Option value={4}>星期四</Option>
                  <Option value={5}>星期五</Option>
                  <Option value={6}>星期六</Option>
                  <Option value={0}>星期日</Option>
                </Select>
              </Form.Item>
              <Form.Item
                label="执行时间"
                name="schedule_time"
                rules={[{ required: true, message: '请选择执行时间' }]}
              >
                <TimePicker format="HH:mm" />
              </Form.Item>
            </>
          )}
          
          {scheduleType === 'monthly' && (
            <>
              <Form.Item
                label="执行日期"
                name="schedule_dates"
                rules={[{ required: true, message: '请选择执行日期' }]}
              >
                <Select mode="multiple" placeholder="选择日期">
                  {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                    <Option key={day} value={day}>{day}日</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item
                label="执行时间"
                name="schedule_time"
                rules={[{ required: true, message: '请选择执行时间' }]}
              >
                <TimePicker format="HH:mm" />
              </Form.Item>
            </>
          )}
          
          {scheduleType === 'interval' && (
            <Form.Item label="执行间隔">
              <Input.Group compact>
                <Form.Item
                  name="schedule_interval"
                  noStyle
                  rules={[{ required: true, message: '请输入间隔' }]}
                >
                  <InputNumber min={1} style={{ width: '60%' }} />
                </Form.Item>
                <Form.Item
                  name="schedule_interval_unit"
                  noStyle
                  initialValue="hours"
                >
                  <Select style={{ width: '40%' }}>
                    <Option value="minutes">分钟</Option>
                    <Option value="hours">小时</Option>
                    <Option value="days">天</Option>
                  </Select>
                </Form.Item>
              </Input.Group>
            </Form.Item>
          )}
          
          {scheduleType === 'cron' && (
            <Form.Item
              label="Cron表达式"
              name="schedule_cron"
              rules={[{ required: true, message: '请输入Cron表达式' }]}
              extra="格式: 分 时 日 月 周"
            >
              <Input placeholder="0 10 * * *" />
            </Form.Item>
          )}
        </Card>
      );
    }
    
    if (triggerType === 'event') {
      return (
        <Card title="事件触发配置" size="small">
          <Form.Item
            label="事件类型"
            name="event_type"
            rules={[{ required: true, message: '请选择事件类型' }]}
          >
            <Select>
              <Option value="video_uploaded">视频上传完成</Option>
              <Option value="task_completed">任务完成</Option>
              <Option value="schedule_missed">调度错过</Option>
              <Option value="error_occurred">错误发生</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="事件过滤条件"
            name="event_filter"
            extra="JSON格式的过滤条件"
          >
            <TextArea rows={3} placeholder='{"source": "upload", "type": "video"}' />
          </Form.Item>
        </Card>
      );
    }
    
    return (
      <Alert message="手动触发无需额外配置" type="info" />
    );
  };

  return (
    <Modal
      title={config ? '编辑发布配置' : '创建发布配置'}
      visible={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      width={800}
      okText="保存"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          trigger_type: 'scheduled',
          schedule_type: 'daily',
          priority: 50
        }}
      >
        <Tabs defaultActiveKey="basic">
          <TabPane tab="基础配置" key="basic">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="配置名称"
                  name="config_name"
                  rules={[{ required: true, message: '请输入配置名称' }]}
                >
                  <Input placeholder="输入配置名称" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="优先级"
                  name="priority"
                  extra="数值越大优先级越高 (0-100)"
                >
                  <InputNumber min={0} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="Pipeline"
                  name="pipeline_id"
                  rules={[{ required: true, message: '请选择Pipeline' }]}
                >
                  <Select 
                    placeholder="选择Pipeline"
                    onChange={handlePipelineChange}
                    showSearch
                    optionFilterProp="children"
                  >
                    {pipelines.map(p => (
                      <Option key={p.pipeline_id} value={p.pipeline_id}>
                        {p.pipeline_name}
                        <Tag style={{ marginLeft: 8 }} color="blue">{p.pipeline_type}</Tag>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="账号组"
                  name="group_id"
                  rules={[{ required: true, message: '请选择账号组' }]}
                >
                  <Select placeholder="选择账号组">
                    {groups.map(g => (
                      <Option key={g.group_id} value={g.group_id}>
                        {g.group_name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item
              label="分配策略"
              name="strategy_id"
              extra="选择账号分配策略（可选）"
            >
              <Select placeholder="默认轮询策略" allowClear>
                <Option value="round_robin">轮询分配</Option>
                <Option value="random">随机分配</Option>
                <Option value="weighted">权重分配</Option>
                <Option value="sticky">固定分配</Option>
              </Select>
            </Form.Item>
          </TabPane>
          
          <TabPane tab="触发配置" key="trigger">
            <Form.Item
              label="触发方式"
              name="trigger_type"
              rules={[{ required: true, message: '请选择触发方式' }]}
            >
              <Radio.Group onChange={(e) => setTriggerType(e.target.value)}>
                <Radio.Button value="scheduled">
                  <ClockCircleOutlined /> 定时触发
                </Radio.Button>
                <Radio.Button value="manual">
                  <PlayCircleOutlined /> 手动触发
                </Radio.Button>
                <Radio.Button value="event">
                  <ExclamationCircleOutlined /> 事件触发
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
            
            <Divider />
            
            {renderTriggerConfig()}
          </TabPane>
          
          {selectedPipeline && (
            <TabPane tab="参数配置" key="params">
              {renderPipelineParams()}
            </TabPane>
          )}
        </Tabs>
      </Form>
    </Modal>
  );
};

export default ConfigFormModal;