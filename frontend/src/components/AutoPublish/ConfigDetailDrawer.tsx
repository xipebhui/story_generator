import React, { useEffect, useState } from 'react';
import {
  Drawer,
  Descriptions,
  Tag,
  Table,
  Tabs,
  Button,
  Space,
  Timeline,
  Statistic,
  Row,
  Col,
  Card,
  Alert,
  Badge,
  Progress,
  Spin,
  message,
  Empty
} from 'antd';
import {
  EditOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  CalendarOutlined,
  RocketOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { autoPublishService } from '../../services/autoPublish';
import moment from 'moment';

const { TabPane } = Tabs;

interface ConfigDetailDrawerProps {
  visible: boolean;
  config: any | null;
  pipelines: any[];
  groups: any[];
  onClose: () => void;
  onEdit: (config: any) => void;
}

interface Task {
  task_id: string;
  pipeline_id: string;
  account_name: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
}

interface ConfigStats {
  total_tasks: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  avg_duration: number;
  period: string;
}

const ConfigDetailDrawer: React.FC<ConfigDetailDrawerProps> = ({
  visible,
  config,
  pipelines,
  groups,
  onClose,
  onEdit
}) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<ConfigStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('detail');
  const [selectedPeriod, setSelectedPeriod] = useState('week');

  useEffect(() => {
    if (visible && config) {
      loadConfigData();
    }
  }, [visible, config, selectedPeriod]);

  // 加载配置数据
  const loadConfigData = async () => {
    if (!config) return;
    
    setLoading(true);
    try {
      const [tasksRes, statsRes] = await Promise.all([
        autoPublishService.getConfigTasks(config.config_id, { limit: 20 }),
        autoPublishService.getConfigStats(config.config_id, selectedPeriod)
      ]);
      
      setTasks(tasksRes.tasks || []);
      setStats(statsRes);
    } catch (error: any) {
      console.error('加载配置数据失败:', error);
      message.error('加载数据失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取Pipeline信息
  const getPipeline = () => {
    return pipelines.find(p => p.pipeline_id === config?.pipeline_id);
  };

  // 获取账号组信息
  const getGroup = () => {
    return groups.find(g => g.group_id === config?.group_id);
  };

  // 获取触发类型标签
  const getTriggerTypeTag = (type: string) => {
    const typeMap: Record<string, { color: string; text: string; icon: any }> = {
      scheduled: { color: 'blue', text: '定时触发', icon: <ClockCircleOutlined /> },
      manual: { color: 'orange', text: '手动触发', icon: <PlayCircleOutlined /> },
      event: { color: 'purple', text: '事件触发', icon: <ExclamationCircleOutlined /> }
    };
    const cfg = typeMap[type] || { color: 'default', text: type, icon: null };
    return (
      <Tag color={cfg.color}>
        {cfg.icon} {cfg.text}
      </Tag>
    );
  };

  // 获取任务状态标签
  const getTaskStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; icon: any }> = {
      pending: { color: 'default', text: '待执行', icon: <ClockCircleOutlined /> },
      running: { color: 'processing', text: '执行中', icon: <PlayCircleOutlined /> },
      completed: { color: 'success', text: '成功', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', text: '失败', icon: <CloseCircleOutlined /> }
    };
    const cfg = statusMap[status] || { color: 'default', text: status, icon: null };
    return (
      <Tag color={cfg.color}>
        {cfg.icon} {cfg.text}
      </Tag>
    );
  };

  // 渲染触发配置详情
  const renderTriggerConfig = () => {
    if (!config?.trigger_config) return '无';
    
    const triggerConfig = config.trigger_config;
    
    if (config.trigger_type === 'scheduled') {
      const scheduleType = triggerConfig.schedule_type;
      
      let scheduleDesc = '';
      switch (scheduleType) {
        case 'daily':
          scheduleDesc = `每天 ${triggerConfig.time || '未设置'}`;
          break;
        case 'weekly':
          const days = triggerConfig.days?.map((d: number) => {
            const dayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
            return dayNames[d];
          }).join(', ') || '未设置';
          scheduleDesc = `每周 ${days} ${triggerConfig.time || ''}`;
          break;
        case 'monthly':
          const dates = triggerConfig.dates?.join(', ') || '未设置';
          scheduleDesc = `每月 ${dates}日 ${triggerConfig.time || ''}`;
          break;
        case 'interval':
          scheduleDesc = `每 ${triggerConfig.interval} ${triggerConfig.unit || '小时'}`;
          break;
        case 'cron':
          scheduleDesc = `Cron: ${triggerConfig.cron}`;
          break;
        default:
          scheduleDesc = JSON.stringify(triggerConfig);
      }
      
      return (
        <Space direction="vertical" size="small">
          <div>调度类型: {scheduleType}</div>
          <div>调度规则: {scheduleDesc}</div>
          <div>时区: {triggerConfig.timezone || 'Asia/Shanghai'}</div>
        </Space>
      );
    }
    
    if (config.trigger_type === 'event') {
      return (
        <Space direction="vertical" size="small">
          <div>事件类型: {triggerConfig.event_type}</div>
          {triggerConfig.event_filter && (
            <div>过滤条件: <code>{JSON.stringify(triggerConfig.event_filter)}</code></div>
          )}
        </Space>
      );
    }
    
    return '手动触发';
  };

  // 任务列表列定义
  const taskColumns: ColumnsType<Task> = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 150,
      ellipsis: true
    },
    {
      title: '账号',
      dataIndex: 'account_name',
      key: 'account_name'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getTaskStatusTag(status)
    },
    {
      title: '执行时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => moment(text).format('MM-DD HH:mm')
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration) => duration ? `${duration}秒` : '-'
    }
  ];

  // 渲染统计卡片
  const renderStatistics = () => {
    if (!stats) return <Empty description="暂无统计数据" />;
    
    return (
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.total_tasks}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats.success_rate}
              suffix="%"
              valueStyle={{ 
                color: stats.success_rate >= 90 ? '#3f8600' : stats.success_rate >= 70 ? '#faad14' : '#cf1322' 
              }}
              prefix={stats.success_rate >= 90 ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功/失败"
              value={stats.success_count}
              suffix={`/ ${stats.failed_count}`}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均耗时"
              value={stats.avg_duration}
              suffix="秒"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  // 渲染执行时间线
  const renderTimeline = () => {
    if (tasks.length === 0) {
      return <Empty description="暂无执行记录" />;
    }
    
    return (
      <Timeline mode="left">
        {tasks.slice(0, 10).map(task => (
          <Timeline.Item
            key={task.task_id}
            color={
              task.status === 'completed' ? 'green' : 
              task.status === 'failed' ? 'red' : 
              task.status === 'running' ? 'blue' : 'gray'
            }
            label={moment(task.created_at).format('MM-DD HH:mm')}
          >
            <Space direction="vertical" size="small">
              <div>
                <strong>{task.account_name}</strong>
              </div>
              <div>
                {getTaskStatusTag(task.status)}
                {task.duration && <span style={{ marginLeft: 8 }}>耗时: {task.duration}秒</span>}
              </div>
            </Space>
          </Timeline.Item>
        ))}
      </Timeline>
    );
  };

  if (!config) return null;

  const pipeline = getPipeline();
  const group = getGroup();

  return (
    <Drawer
      title={`配置详情: ${config.config_name}`}
      placement="right"
      width={800}
      onClose={onClose}
      visible={visible}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadConfigData}>
            刷新
          </Button>
          <Button type="primary" icon={<EditOutlined />} onClick={() => onEdit(config)}>
            编辑
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="基础信息" key="detail">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="配置ID">
                {config.config_id}
              </Descriptions.Item>
              <Descriptions.Item label="配置名称">
                {config.config_name}
              </Descriptions.Item>
              <Descriptions.Item label="Pipeline">
                <Space>
                  <span>{pipeline?.pipeline_name || config.pipeline_id}</span>
                  <Tag color="blue">{pipeline?.pipeline_type}</Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="账号组">
                {group?.group_name || config.group_id}
              </Descriptions.Item>
              <Descriptions.Item label="触发方式">
                {getTriggerTypeTag(config.trigger_type)}
              </Descriptions.Item>
              <Descriptions.Item label="触发配置">
                {renderTriggerConfig()}
              </Descriptions.Item>
              <Descriptions.Item label="分配策略">
                {config.strategy_id || '默认轮询'}
              </Descriptions.Item>
              <Descriptions.Item label="优先级">
                <Badge 
                  count={config.priority} 
                  style={{ 
                    backgroundColor: config.priority >= 80 ? '#f5222d' : 
                      config.priority >= 50 ? '#fa8c16' : '#52c41a' 
                  }} 
                />
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={config.is_active ? 'success' : 'default'}>
                  {config.is_active ? '启用' : '禁用'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {moment(config.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {config.updated_at && (
                <Descriptions.Item label="更新时间">
                  {moment(config.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
            </Descriptions>
            
            {config.pipeline_params && Object.keys(config.pipeline_params).length > 0 && (
              <Card title="Pipeline参数" style={{ marginTop: 16 }}>
                <Descriptions column={1} size="small">
                  {Object.entries(config.pipeline_params).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            )}
          </TabPane>
          
          <TabPane tab="执行统计" key="stats">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Space style={{ marginBottom: 16 }}>
                  <span>统计周期:</span>
                  <Button.Group>
                    <Button 
                      type={selectedPeriod === 'today' ? 'primary' : 'default'}
                      onClick={() => setSelectedPeriod('today')}
                    >
                      今天
                    </Button>
                    <Button 
                      type={selectedPeriod === 'week' ? 'primary' : 'default'}
                      onClick={() => setSelectedPeriod('week')}
                    >
                      本周
                    </Button>
                    <Button 
                      type={selectedPeriod === 'month' ? 'primary' : 'default'}
                      onClick={() => setSelectedPeriod('month')}
                    >
                      本月
                    </Button>
                  </Button.Group>
                </Space>
                
                {renderStatistics()}
              </div>
              
              {stats && stats.total_tasks > 0 && (
                <Card title="成功率趋势">
                  <Progress
                    percent={stats.success_rate}
                    strokeColor={{
                      '0%': '#ff4d4f',
                      '50%': '#faad14',
                      '100%': '#52c41a'
                    }}
                    format={(percent) => (
                      <span style={{ fontSize: 16 }}>
                        {percent}%
                      </span>
                    )}
                  />
                </Card>
              )}
            </Space>
          </TabPane>
          
          <TabPane tab="执行记录" key="tasks">
            <Table
              columns={taskColumns}
              dataSource={tasks}
              rowKey="task_id"
              pagination={{
                pageSize: 10,
                showTotal: (total) => `共 ${total} 条记录`
              }}
              size="small"
            />
          </TabPane>
          
          <TabPane tab="执行时间线" key="timeline">
            {renderTimeline()}
          </TabPane>
        </Tabs>
      </Spin>
    </Drawer>
  );
};

export default ConfigDetailDrawer;