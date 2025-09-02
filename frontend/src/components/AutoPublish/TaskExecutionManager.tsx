import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Drawer, Descriptions, Tag, Space, Tabs,
  Upload, message, Timeline, Row, Col, Statistic, List, Badge,
  Alert, Collapse, Typography, Tooltip, Modal, Progress, Select,
  DatePicker, Avatar, Empty, Divider, Popconfirm
} from 'antd';
import {
  EyeOutlined, ReloadOutlined, UploadOutlined, BarChartOutlined,
  PlayCircleOutlined, TeamOutlined, FileTextOutlined, ClockCircleOutlined,
  SyncOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import moment from 'moment';
import { autoPublishService } from '../../services/autoPublish';

const { TabPane } = Tabs;
const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface TaskExecution {
  task_id: string;
  config_id: string;
  config_name: string;
  group_id: string;
  group_name: string;
  account_id: string;
  account_name?: string;
  pipeline_id: string;
  pipeline_name: string;
  pipeline_config?: any;
  pipeline_status: 'pending' | 'running' | 'completed' | 'failed';
  pipeline_result?: any;
  publish_status: 'pending' | 'published' | 'failed';
  publish_result?: any;
  priority: number;
  retry_count: number;
  error_message?: string;
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  metadata?: TaskMetadata;
}

interface TaskMetadata {
  subtitle_file?: string;
  video_url?: string;
  thumbnail_url?: string;
  performance?: PerformanceData;
  logs?: string[];
}

interface GroupExecutionDetail {
  config_id: string;
  config_name: string;
  group_id: string;
  group_name: string;
  execution_time: string;
  total_accounts: number;
  accounts: AccountExecution[];
  summary: {
    total: number;
    success: number;
    failed: number;
    running: number;
    pending: number;
    avg_duration: number;
    total_views: number;
    total_likes: number;
  };
}

interface AccountExecution {
  account_id: string;
  account_name: string;
  platform: string;
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  video_url?: string;
  duration?: number;
  error_message?: string;
  performance: PerformanceData;
}

interface PerformanceData {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  watch_time_minutes: number;
  ctr: number;
  retention_rate: number;
  subscriber_gained: number;
  revenue?: number;
}

const TaskExecutionManager: React.FC = () => {
  const [tasks, setTasks] = useState<TaskExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskExecution | null>(null);
  const [groupExecution, setGroupExecution] = useState<GroupExecutionDetail | null>(null);
  const [filters, setFilters] = useState({
    status: '',
    config_id: '',
    account_id: '',
    date_range: [] as any[]
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  });
  const [configs, setConfigs] = useState<any[]>([]);

  useEffect(() => {
    loadTasks();
    loadConfigs();
  }, [filters, pagination.current]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        status: filters.status || undefined,
        config_id: filters.config_id || undefined,
        account_id: filters.account_id || undefined,
        start_date: filters.date_range[0]?.format('YYYY-MM-DD') || undefined,
        end_date: filters.date_range[1]?.format('YYYY-MM-DD') || undefined
      };

      const response = await autoPublishService.getTasks(params);
      setTasks(response.tasks);
      setPagination(prev => ({
        ...prev,
        total: response.total
      }));
    } catch (error) {
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadConfigs = async () => {
    try {
      const response = await autoPublishService.getPublishConfigs();
      setConfigs(response.configs || []);
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  };

  const loadGroupExecutionDetail = async (task: TaskExecution) => {
    try {
      const response = await autoPublishService.getGroupExecutions(
        task.config_id,
        task.created_at
      );
      setGroupExecution(response);
    } catch (error) {
      message.error('加载账号组执行详情失败');
    }
  };

  const showTaskDetail = async (task: TaskExecution) => {
    setSelectedTask(task);
    setDetailVisible(true);
    await loadGroupExecutionDetail(task);
  };

  const retryTask = async (taskId: string) => {
    try {
      await autoPublishService.retryTask(taskId);
      message.success('任务重试已启动');
      loadTasks();
    } catch (error) {
      message.error('重试任务失败');
    }
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, any> = {
      'pending': { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
      'running': { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
      'completed': { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
      'failed': { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
    };
    return configs[status] || configs['pending'];
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'pending': '#d9d9d9',
      'running': '#1890ff',
      'completed': '#52c41a',
      'failed': '#ff4d4f'
    };
    return colors[status] || '#d9d9d9';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      'pending': '等待中',
      'running': '运行中',
      'completed': '已完成',
      'failed': '失败'
    };
    return texts[status] || status;
  };

  const getRankColor = (index: number) => {
    if (index === 0) return '#ff4d4f';
    if (index === 1) return '#faad14';
    if (index === 2) return '#52c41a';
    return '#d9d9d9';
  };

  const calculateAvgRetention = (accounts: AccountExecution[]) => {
    const validAccounts = accounts.filter(a => a.status === 'completed' && a.performance);
    if (validAccounts.length === 0) return 0;
    
    const total = validAccounts.reduce((sum, a) => sum + a.performance.retention_rate, 0);
    return Math.round(total / validAccounts.length);
  };

  const sortAccountsByPerformance = (accounts: AccountExecution[]) => {
    return [...accounts]
      .filter(a => a.status === 'completed' && a.performance)
      .sort((a, b) => {
        const scoreA = (a.performance.views * 0.5) + 
                      (a.performance.likes * 0.3) + 
                      (a.performance.retention_rate * 100 * 0.2);
        const scoreB = (b.performance.views * 0.5) + 
                      (b.performance.likes * 0.3) + 
                      (b.performance.retention_rate * 100 * 0.2);
        return scoreB - scoreA;
      });
  };

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text copyable>{id.substring(0, 8)}...</Text>
        </Tooltip>
      )
    },
    {
      title: '配置名称',
      dataIndex: 'config_name',
      width: 150,
      render: (name: string, record: TaskExecution) => (
        <Space direction="vertical" size={0}>
          <Text>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.group_name}
          </Text>
        </Space>
      )
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_name',
      width: 150
    },
    {
      title: '状态',
      dataIndex: 'pipeline_status',
      width: 100,
      render: (status: string) => {
        const config = getStatusConfig(status);
        return (
          <Badge status={config.color} text={
            <Space>
              {config.icon}
              {config.text}
            </Space>
          } />
        );
      }
    },
    {
      title: '执行时间',
      dataIndex: 'created_at',
      width: 150,
      render: (time: string) => moment(time).format('MM-DD HH:mm:ss')
    },
    {
      title: '耗时',
      width: 80,
      render: (_: any, record: TaskExecution) => {
        if (!record.started_at || !record.completed_at) return '-';
        const duration = moment(record.completed_at).diff(moment(record.started_at), 'seconds');
        return `${duration}秒`;
      }
    },
    {
      title: '操作',
      width: 200,
      fixed: 'right',
      render: (_: any, record: TaskExecution) => (
        <Space>
          <Button 
            type="link" 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => showTaskDetail(record)}>
            查看
          </Button>
          <Button 
            type="link" 
            size="small" 
            icon={<BarChartOutlined />}
            onClick={() => showPerformanceModal(record)}>
            数据
          </Button>
          {record.pipeline_status === 'failed' && (
            <Button 
              type="link" 
              size="small" 
              danger
              icon={<ReloadOutlined />}
              onClick={() => retryTask(record.task_id)}>
              重试
            </Button>
          )}
        </Space>
      )
    }
  ];

  const showPerformanceModal = async (task: TaskExecution) => {
    try {
      const data = await autoPublishService.getTaskPerformance(task.task_id);
      Modal.info({
        title: '任务性能数据',
        width: 600,
        content: (
          <div>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="平台">{data.platform}</Descriptions.Item>
              <Descriptions.Item label="视频链接">
                {data.video_url ? (
                  <a href={data.video_url} target="_blank" rel="noopener noreferrer">
                    查看视频
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="观看量">{data.performance.views}</Descriptions.Item>
              <Descriptions.Item label="点赞数">{data.performance.likes}</Descriptions.Item>
              <Descriptions.Item label="评论数">{data.performance.comments}</Descriptions.Item>
              <Descriptions.Item label="分享数">{data.performance.shares}</Descriptions.Item>
              <Descriptions.Item label="点击率">{data.performance.ctr}%</Descriptions.Item>
              <Descriptions.Item label="完播率">{data.performance.retention_rate}%</Descriptions.Item>
              <Descriptions.Item label="新增订阅">{data.performance.subscriber_gained}</Descriptions.Item>
              <Descriptions.Item label="收益">${data.performance.revenue || 0}</Descriptions.Item>
            </Descriptions>
          </div>
        )
      });
    } catch (error) {
      message.error('获取性能数据失败');
    }
  };

  const resetFilters = () => {
    setFilters({
      status: '',
      config_id: '',
      account_id: '',
      date_range: []
    });
  };

  const handleTableChange = (newPagination: any) => {
    setPagination({
      ...pagination,
      current: newPagination.current,
      pageSize: newPagination.pageSize
    });
  };

  return (
    <Card title="执行记录管理">
      {/* 筛选条件 */}
      <Space style={{ marginBottom: 16 }}>
        <Select 
          style={{ width: 120 }}
          placeholder="状态"
          allowClear
          value={filters.status}
          onChange={v => setFilters({ ...filters, status: v })}>
          <Option value="pending">等待中</Option>
          <Option value="running">运行中</Option>
          <Option value="completed">已完成</Option>
          <Option value="failed">失败</Option>
        </Select>
        
        <Select 
          style={{ width: 200 }}
          placeholder="选择配置"
          allowClear
          value={filters.config_id}
          onChange={v => setFilters({ ...filters, config_id: v })}>
          {configs.map(c => (
            <Option key={c.config_id} value={c.config_id}>
              {c.config_name}
            </Option>
          ))}
        </Select>
        
        <RangePicker 
          value={filters.date_range}
          onChange={v => setFilters({ ...filters, date_range: v || [] })} />
        
        <Button type="primary" onClick={loadTasks}>查询</Button>
        <Button onClick={resetFilters}>重置</Button>
      </Space>
      
      <Table
        columns={columns}
        dataSource={tasks}
        loading={loading}
        rowKey="task_id"
        pagination={pagination}
        onChange={handleTableChange}
        scroll={{ x: 1200 }}
      />

      {/* 任务详情抽屉 */}
      <Drawer
        title={
          <Space>
            <TeamOutlined />
            任务执行详情 - {selectedTask?.config_name}
          </Space>
        }
        width={1000}
        visible={detailVisible}
        onClose={() => {
          setDetailVisible(false);
          setSelectedTask(null);
          setGroupExecution(null);
        }}>
        
        {selectedTask && groupExecution && (
          <>
            {/* 顶部统计卡片 */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic 
                    title="账号总数" 
                    value={groupExecution.total_accounts} 
                    prefix={<TeamOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic 
                    title="成功率" 
                    value={groupExecution.summary.success}
                    suffix={`/ ${groupExecution.summary.total}`}
                    valueStyle={{ 
                      color: groupExecution.summary.success === 
                             groupExecution.summary.total ? '#3f8600' : '#cf1322' 
                    }} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic 
                    title="总观看量" 
                    value={groupExecution.summary.total_views} 
                    prefix={<EyeOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic 
                    title="平均耗时" 
                    value={groupExecution.summary.avg_duration} 
                    suffix="秒" 
                    prefix={<ClockCircleOutlined />} />
                </Card>
              </Col>
            </Row>
            
            <Tabs defaultActiveKey="overview">
              {/* Tab 1: 概览信息 */}
              <TabPane tab="概览" key="overview">
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="任务ID">{selectedTask.task_id}</Descriptions.Item>
                  <Descriptions.Item label="配置名称">{selectedTask.config_name}</Descriptions.Item>
                  <Descriptions.Item label="Pipeline">{selectedTask.pipeline_name}</Descriptions.Item>
                  <Descriptions.Item label="账号组">{selectedTask.group_name}</Descriptions.Item>
                  <Descriptions.Item label="执行时间">{selectedTask.created_at}</Descriptions.Item>
                  <Descriptions.Item label="完成时间">{selectedTask.completed_at || '-'}</Descriptions.Item>
                  <Descriptions.Item label="优先级">
                    <Progress percent={selectedTask.priority * 20} steps={5} size="small" showInfo={false} />
                  </Descriptions.Item>
                  <Descriptions.Item label="重试次数">{selectedTask.retry_count}</Descriptions.Item>
                </Descriptions>
                
                {/* 字幕文件状态 */}
                <Card title="字幕文件" size="small" style={{ marginTop: 16 }}>
                  {selectedTask.metadata?.subtitle_file ? (
                    <Alert 
                      message="已上传字幕文件" 
                      description={selectedTask.metadata.subtitle_file}
                      type="success" 
                      showIcon />
                  ) : (
                    <Alert 
                      message="未上传字幕文件" 
                      description="暂无字幕文件"
                      type="info" 
                      showIcon />
                  )}
                </Card>
              </TabPane>
              
              {/* Tab 2: 账号执行详情 */}
              <TabPane 
                tab={
                  <Badge count={groupExecution.accounts.length} offset={[10, 0]}>
                    账号执行详情
                  </Badge>
                } 
                key="accounts">
                <List
                  dataSource={groupExecution.accounts}
                  renderItem={(account: AccountExecution) => (
                    <Card 
                      size="small" 
                      style={{ marginBottom: 16 }}
                      title={
                        <Space>
                          <Avatar style={{ backgroundColor: getStatusColor(account.status) }}>
                            {account.account_name.substring(0, 1)}
                          </Avatar>
                          <Text strong>{account.account_name}</Text>
                          <Tag>{account.platform}</Tag>
                          <Tag color={getStatusColor(account.status)}>
                            {getStatusText(account.status)}
                          </Tag>
                        </Space>
                      }
                      extra={
                        <Space>
                          {account.video_url && (
                            <Button 
                              type="link" 
                              icon={<PlayCircleOutlined />}
                              href={account.video_url} 
                              target="_blank">
                              查看视频
                            </Button>
                          )}
                          {account.status === 'failed' && (
                            <Button 
                              type="link" 
                              danger
                              onClick={() => retryTask(account.task_id)}>
                              重试
                            </Button>
                          )}
                        </Space>
                      }>
                      
                      <Row gutter={16}>
                        <Col span={12}>
                          <Descriptions column={1} size="small">
                            <Descriptions.Item label="任务ID">
                              {account.task_id.substring(0, 8)}...
                            </Descriptions.Item>
                            <Descriptions.Item label="执行耗时">
                              {account.duration ? `${account.duration}秒` : '-'}
                            </Descriptions.Item>
                            {account.error_message && (
                              <Descriptions.Item label="错误信息">
                                <Text type="danger">{account.error_message}</Text>
                              </Descriptions.Item>
                            )}
                          </Descriptions>
                        </Col>
                        
                        <Col span={12}>
                          {account.status === 'completed' && account.performance && (
                            <Card size="small" title="发布数据" bordered={false}>
                              <Row gutter={8}>
                                <Col span={12}>
                                  <Statistic 
                                    title="观看" 
                                    value={account.performance.views} 
                                    valueStyle={{ fontSize: 14 }} />
                                </Col>
                                <Col span={12}>
                                  <Statistic 
                                    title="点赞" 
                                    value={account.performance.likes}
                                    valueStyle={{ fontSize: 14 }} />
                                </Col>
                                <Col span={12}>
                                  <Statistic 
                                    title="评论" 
                                    value={account.performance.comments}
                                    valueStyle={{ fontSize: 14 }} />
                                </Col>
                                <Col span={12}>
                                  <Statistic 
                                    title="完播率" 
                                    value={account.performance.retention_rate}
                                    suffix="%"
                                    valueStyle={{ fontSize: 14 }} />
                                </Col>
                              </Row>
                            </Card>
                          )}
                        </Col>
                      </Row>
                    </Card>
                  )}
                />
              </TabPane>
              
              {/* Tab 3: 汇总数据 */}
              <TabPane tab="汇总数据" key="summary">
                <Card title="整体表现" size="small">
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card size="small" bordered={false}>
                        <Statistic 
                          title="总观看量" 
                          value={groupExecution.summary.total_views} />
                        <Progress 
                          percent={100} 
                          strokeColor="#52c41a" 
                          showInfo={false} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" bordered={false}>
                        <Statistic 
                          title="总点赞数" 
                          value={groupExecution.summary.total_likes} />
                        <Progress 
                          percent={75} 
                          strokeColor="#1890ff" 
                          showInfo={false} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" bordered={false}>
                        <Statistic 
                          title="平均完播率" 
                          value={calculateAvgRetention(groupExecution.accounts)}
                          suffix="%" />
                        <Progress 
                          percent={calculateAvgRetention(groupExecution.accounts)} 
                          strokeColor="#faad14" 
                          showInfo={false} />
                      </Card>
                    </Col>
                  </Row>
                </Card>
                
                {/* 账号排名 */}
                <Card title="账号表现排名" size="small" style={{ marginTop: 16 }}>
                  <List
                    dataSource={sortAccountsByPerformance(groupExecution.accounts)}
                    renderItem={(account: AccountExecution, index: number) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <Badge count={index + 1} 
                              style={{ backgroundColor: getRankColor(index) }} />
                          }
                          title={account.account_name}
                          description={`观看: ${account.performance.views} | 点赞: ${account.performance.likes}`}
                        />
                        <div>
                          <Tag color="blue">CTR: {account.performance.ctr}%</Tag>
                          <Tag color="green">完播: {account.performance.retention_rate}%</Tag>
                        </div>
                      </List.Item>
                    )}
                  />
                </Card>
              </TabPane>
              
              {/* Tab 4: 执行日志 */}
              <TabPane tab="执行日志" key="logs">
                <Timeline>
                  {selectedTask.metadata?.logs?.map((log, index) => (
                    <Timeline.Item key={index}>
                      <Text code>{log}</Text>
                    </Timeline.Item>
                  )) || <Empty description="暂无日志" />}
                </Timeline>
              </TabPane>
            </Tabs>
          </>
        )}
      </Drawer>
    </Card>
  );
};

export default TaskExecutionManager;