import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Space,
  Tag,
  Switch,
  Tooltip,
  Popconfirm,
  Drawer,
  Descriptions,
  Timeline
} from 'antd';
import {
  PlusOutlined,
  SettingOutlined,
  EditOutlined,
  DeleteOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { autoPublishService } from '../../services/autoPublish';

interface PublishConfig {
  config_id: string;
  config_name: string;
  group_id: string;
  pipeline_id: string;
  trigger_type: 'scheduled' | 'monitor';
  trigger_config: any;
  strategy_id?: string;
  priority: number;
  is_active: boolean;
  created_at: string;
}

const PublishConfigManager: React.FC = () => {
  const [configs, setConfigs] = useState<PublishConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<PublishConfig | null>(null);
  const [form] = Form.useForm();
  const [groups, setGroups] = useState<any[]>([]);
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);

  useEffect(() => {
    loadConfigs();
    loadGroups();
    loadPipelines();
    loadStrategies();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const response = await autoPublishService.listPublishConfigs();
      const data = response?.configs || response || [];
      setConfigs(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载发布配置失败:', error);
      message.error('加载发布配置失败');
      setConfigs([]);
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await autoPublishService.listAccountGroups();
      const data = response?.groups || response || [];
      setGroups(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载账号组失败:', error);
      setGroups([]);
    }
  };

  const loadPipelines = async () => {
    try {
      const data = await autoPublishService.listPipelines();
      setPipelines(data.pipelines || []);
    } catch (error) {
      console.error('加载Pipeline失败:', error);
    }
  };

  const loadStrategies = async () => {
    try {
      const response = await autoPublishService.listStrategies();
      const data = response?.strategies || response || [];
      setStrategies(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载策略失败:', error);
      setStrategies([]);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      // 构建触发器配置
      const triggerConfig: any = {};
      if (values.trigger_type === 'scheduled') {
        triggerConfig.interval = values.interval;
        triggerConfig.time = values.time;
        if (values.days_of_week) {
          triggerConfig.days_of_week = values.days_of_week;
        }
      } else if (values.trigger_type === 'monitor') {
        triggerConfig.monitor_id = values.monitor_id;
        triggerConfig.threshold = values.threshold;
      }

      await autoPublishService.createPublishConfig({
        config_name: values.config_name,
        group_id: values.group_id,
        pipeline_id: values.pipeline_id,
        trigger_type: values.trigger_type,
        trigger_config: triggerConfig,
        strategy_id: values.strategy_id,
        priority: values.priority || 50
      });

      message.success('创建发布配置成功');
      setModalVisible(false);
      loadConfigs();
    } catch (error) {
      message.error('创建发布配置失败');
    }
  };

  const handleDelete = async (configId: string) => {
    try {
      await autoPublishService.deletePublishConfig(configId);
      message.success('删除发布配置成功');
      loadConfigs();
    } catch (error) {
      message.error('删除发布配置失败');
    }
  };

  const handleToggleActive = async (config: PublishConfig) => {
    try {
      await autoPublishService.updatePublishConfig(config.config_id, {
        is_active: !config.is_active
      });
      message.success(`${config.is_active ? '停用' : '启用'}配置成功`);
      loadConfigs();
    } catch (error) {
      message.error('更新配置状态失败');
    }
  };

  const showDetail = (config: PublishConfig) => {
    setSelectedConfig(config);
    setDetailVisible(true);
  };

  const columns = [
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
      render: (text: string, record: PublishConfig) => (
        <Space>
          <SettingOutlined />
          <a onClick={() => showDetail(record)}>{text}</a>
        </Space>
      )
    },
    {
      title: '账号组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (groupId: string) => {
        const group = groups.find(g => g.group_id === groupId);
        return group ? (
          <Tag color="blue">{group.group_name}</Tag>
        ) : groupId;
      }
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_id',
      key: 'pipeline_id',
      render: (pipelineId: string) => {
        const pipeline = pipelines.find(p => p.pipeline_id === pipelineId);
        return pipeline ? (
          <Tag color="green">{pipeline.pipeline_name}</Tag>
        ) : pipelineId;
      }
    },
    {
      title: '触发方式',
      dataIndex: 'trigger_type',
      key: 'trigger_type',
      width: 100,
      render: (type: string) => {
        const icon = type === 'scheduled' ? <ClockCircleOutlined /> : <ThunderboltOutlined />;
        const text = type === 'scheduled' ? '定时' : '监控';
        const color = type === 'scheduled' ? 'blue' : 'orange';
        return (
          <Tag icon={icon} color={color}>{text}</Tag>
        );
      }
    },
    {
      title: '策略',
      dataIndex: 'strategy_id',
      key: 'strategy_id',
      render: (strategyId?: string) => {
        if (!strategyId) return <Tag>无策略</Tag>;
        const strategy = strategies.find(s => s.strategy_id === strategyId);
        return strategy ? (
          <Tag color="purple">{strategy.strategy_name}</Tag>
        ) : strategyId;
      }
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: number) => {
        const color = priority >= 70 ? 'red' : priority >= 40 ? 'orange' : 'default';
        return <Tag color={color}>{priority}</Tag>;
      }
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean, record: PublishConfig) => (
        <Switch
          checked={active}
          onChange={() => handleToggleActive(record)}
          checkedChildren="启用"
          unCheckedChildren="停用"
        />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: PublishConfig) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              icon={<EyeOutlined />}
              size="small"
              onClick={() => showDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button icon={<EditOutlined />} size="small" />
          </Tooltip>
          <Popconfirm
            title="确定删除此配置？"
            onConfirm={() => handleDelete(record.config_id)}
          >
            <Tooltip title="删除">
              <Button danger icon={<DeleteOutlined />} size="small" />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <>
      <Card
        title="发布配置管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建配置
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={configs}
          rowKey="config_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个配置`
          }}
        />
      </Card>

      <Modal
        title="创建发布配置"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="config_name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：每日故事发布" />
          </Form.Item>

          <Form.Item
            name="group_id"
            label="账号组"
            rules={[{ required: true, message: '请选择账号组' }]}
          >
            <Select placeholder="选择账号组">
              {groups.map(group => (
                <Select.Option key={group.group_id} value={group.group_id}>
                  {group.group_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="pipeline_id"
            label="Pipeline"
            rules={[{ required: true, message: '请选择Pipeline' }]}
          >
            <Select placeholder="选择Pipeline">
              {pipelines.map(pipeline => (
                <Select.Option key={pipeline.pipeline_id} value={pipeline.pipeline_id}>
                  {pipeline.pipeline_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="trigger_type"
            label="触发方式"
            rules={[{ required: true, message: '请选择触发方式' }]}
            initialValue="scheduled"
          >
            <Select>
              <Select.Option value="scheduled">定时触发</Select.Option>
              <Select.Option value="monitor">监控触发</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.trigger_type !== currentValues.trigger_type
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('trigger_type') === 'scheduled' ? (
                <>
                  <Form.Item
                    name="interval"
                    label="触发间隔"
                    rules={[{ required: true, message: '请选择触发间隔' }]}
                  >
                    <Select>
                      <Select.Option value="daily">每天</Select.Option>
                      <Select.Option value="weekly">每周</Select.Option>
                      <Select.Option value="custom">自定义</Select.Option>
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name="time"
                    label="触发时间"
                    rules={[{ required: true, message: '请输入触发时间' }]}
                  >
                    <Input placeholder="例如：09:00" />
                  </Form.Item>
                </>
              ) : (
                <>
                  <Form.Item
                    name="monitor_id"
                    label="监控配置"
                    rules={[{ required: true, message: '请输入监控配置ID' }]}
                  >
                    <Input placeholder="监控配置ID" />
                  </Form.Item>

                  <Form.Item
                    name="threshold"
                    label="触发阈值"
                  >
                    <InputNumber min={0} placeholder="触发阈值" style={{ width: '100%' }} />
                  </Form.Item>
                </>
              )
            }
          </Form.Item>

          <Form.Item
            name="strategy_id"
            label="策略"
          >
            <Select placeholder="选择策略（可选）" allowClear>
              {strategies.map(strategy => (
                <Select.Option key={strategy.strategy_id} value={strategy.strategy_id}>
                  {strategy.strategy_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            initialValue={50}
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="配置详情"
        placement="right"
        width={600}
        visible={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {selectedConfig && (
          <>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="配置ID">
                {selectedConfig.config_id}
              </Descriptions.Item>
              <Descriptions.Item label="配置名称">
                {selectedConfig.config_name}
              </Descriptions.Item>
              <Descriptions.Item label="账号组">
                {groups.find(g => g.group_id === selectedConfig.group_id)?.group_name || selectedConfig.group_id}
              </Descriptions.Item>
              <Descriptions.Item label="Pipeline">
                {pipelines.find(p => p.pipeline_id === selectedConfig.pipeline_id)?.pipeline_name || selectedConfig.pipeline_id}
              </Descriptions.Item>
              <Descriptions.Item label="触发方式">
                <Tag color={selectedConfig.trigger_type === 'scheduled' ? 'blue' : 'orange'}>
                  {selectedConfig.trigger_type === 'scheduled' ? '定时触发' : '监控触发'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="触发配置">
                <pre>{JSON.stringify(selectedConfig.trigger_config, null, 2)}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="策略">
                {selectedConfig.strategy_id ? 
                  strategies.find(s => s.strategy_id === selectedConfig.strategy_id)?.strategy_name || selectedConfig.strategy_id
                  : '无策略'}
              </Descriptions.Item>
              <Descriptions.Item label="优先级">
                <Tag color={selectedConfig.priority >= 70 ? 'red' : selectedConfig.priority >= 40 ? 'orange' : 'default'}>
                  {selectedConfig.priority}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={selectedConfig.is_active ? 'green' : 'default'}>
                  {selectedConfig.is_active ? '启用' : '停用'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedConfig.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Card title="最近执行记录" style={{ marginTop: 16 }}>
              <Timeline>
                <Timeline.Item color="green">
                  2024-01-10 09:00 - 执行成功
                </Timeline.Item>
                <Timeline.Item color="green">
                  2024-01-09 09:00 - 执行成功
                </Timeline.Item>
                <Timeline.Item color="red">
                  2024-01-08 09:00 - 执行失败（Pipeline错误）
                </Timeline.Item>
              </Timeline>
            </Card>
          </>
        )}
      </Drawer>
    </>
  );
};

export default PublishConfigManager;