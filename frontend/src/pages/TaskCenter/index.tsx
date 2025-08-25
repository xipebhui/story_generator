import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Empty,
  Tooltip,
  Badge,
  Statistic,
  message,
  Spin,
  Segmented
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  EditOutlined,
  CloudUploadOutlined,
  RocketOutlined,
  ExperimentOutlined,
  AppstoreOutlined,
  BarsOutlined
} from '@ant-design/icons';
import { workflows } from '../../config/workflows';
import CreateTaskModal from '../../components/CreateTaskModal';
import TaskDetailDrawer from '../../components/TaskDetailDrawer';
import PublishModal from '../../components/PublishModal';
import RealtimeMonitor from '../../components/RealtimeMonitor';
import { pipelineService } from '../../services/pipeline';
import { Task, TaskStatus } from '../../types/task';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import '../../styles/theme.css';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Option } = Select;

const TaskCenter: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [publishModalVisible, setPublishModalVisible] = useState(false);
  const [monitorModalVisible, setMonitorModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  const [statistics, setStatistics] = useState({
    total: 0,
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0
  });

  // 加载任务列表
  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await pipelineService.listTasks();
      setTasks(response.tasks || []);
      
      // 计算统计数据
      const stats = {
        total: response.total || 0,
        pending: 0,
        running: 0,
        completed: 0,
        failed: 0
      };
      
      response.tasks?.forEach((task: Task) => {
        stats[task.status]++;
      });
      
      setStatistics(stats);
    } catch (error) {
      message.error('加载任务列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载和定时刷新
  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 10000); // 每10秒刷新
    return () => clearInterval(interval);
  }, []);

  // 过滤任务
  const filteredTasks = tasks.filter(task => {
    const matchSearch = !searchText || 
      task.task_id.toLowerCase().includes(searchText.toLowerCase());
    const matchStatus = statusFilter === 'all' || task.status === statusFilter;
    return matchSearch && matchStatus;
  });

  // 获取状态图标
  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case 'pending': return 'default';
      case 'running': return 'processing';
      case 'completed': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // 处理创建任务
  const handleCreateTask = (workflowKey: string) => {
    setSelectedWorkflow(workflowKey);
    setCreateModalVisible(true);
  };

  // 处理任务操作
  const handleViewDetail = (task: Task) => {
    setSelectedTask(task);
    setDetailDrawerVisible(true);
  };

  const handleMonitor = (task: Task) => {
    setSelectedTask(task);
    setMonitorModalVisible(true);
  };

  const handlePublish = (task: Task) => {
    if (task.status !== 'completed') {
      message.warning('只能发布已完成的任务');
      return;
    }
    setSelectedTask(task);
    setPublishModalVisible(true);
  };

  // 渲染任务卡片
  const renderTaskCard = (task: Task) => {
    const workflowConfig = workflows.find(w => 
      task.task_id.includes('story') ? w.key === 'youtube-story' :
      task.task_id.includes('comic') ? w.key === 'youtube-comic' :
      w.key === 'youtube-relief'
    );

    return (
      <div 
        key={task.task_id}
        className={`task-card status-${task.status}`}
      >
        <Row align="middle" gutter={16}>
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Space>
                <Badge status={getStatusColor(task.status)} />
                <span style={{ fontWeight: 500 }}>{task.task_id}</span>
                {workflowConfig && (
                  <Tag color={workflowConfig.color}>
                    {workflowConfig.icon}
                    <span style={{ marginLeft: 4 }}>{workflowConfig.name}</span>
                  </Tag>
                )}
              </Space>
              <Space size={16} style={{ fontSize: 12, color: '#8c8c8c' }}>
                <span>创建于 {dayjs(task.created_at).fromNow()}</span>
                {task.completed_at && (
                  <span>完成于 {dayjs(task.completed_at).fromNow()}</span>
                )}
              </Space>
            </Space>
          </Col>
          <Col>
            <Space>
              <Tooltip title="查看详情">
                <Button 
                  type="text" 
                  icon={<EyeOutlined />}
                  onClick={() => handleViewDetail(task)}
                />
              </Tooltip>
              {task.status === 'running' && (
                <Tooltip title="实时监控">
                  <Button 
                    type="text" 
                    icon={<SyncOutlined spin />}
                    onClick={() => handleMonitor(task)}
                  />
                </Tooltip>
              )}
              {task.status === 'completed' && (
                <Tooltip title="发布">
                  <Button 
                    type="text" 
                    icon={<CloudUploadOutlined />}
                    onClick={() => handlePublish(task)}
                  />
                </Tooltip>
              )}
            </Space>
          </Col>
        </Row>
      </div>
    );
  };

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <h1 className="page-title">
        <RocketOutlined style={{ marginRight: 12 }} />
        创作任务中心
      </h1>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="beautiful-card">
            <Statistic
              title="总任务数"
              value={statistics.total}
              prefix={<AppstoreOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="beautiful-card">
            <Statistic
              title="运行中"
              value={statistics.running}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="beautiful-card">
            <Statistic
              title="已完成"
              value={statistics.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="beautiful-card">
            <Statistic
              title="失败"
              value={statistics.failed}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 工作流选择卡片 */}
      <div style={{ marginBottom: 24 }}>
        <h2 className="section-title">
          <ExperimentOutlined style={{ marginRight: 8 }} />
          选择工作流类型
        </h2>
        <Row gutter={16}>
          {workflows.map(workflow => (
            <Col xs={24} md={8} key={workflow.key}>
              <div 
                className="workflow-card"
                onClick={() => handleCreateTask(workflow.key)}
                style={{ 
                  borderTop: `4px solid transparent`,
                  borderImage: `${workflow.gradient} 1`
                }}
              >
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Space>
                    <div style={{ 
                      fontSize: 32, 
                      background: workflow.gradient,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent'
                    }}>
                      {workflow.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: 18, fontWeight: 600 }}>
                        {workflow.name}
                      </div>
                      <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                        {workflow.description}
                      </div>
                    </div>
                  </Space>
                  <Space wrap>
                    {workflow.tags.map(tag => (
                      <Tag key={tag} color={workflow.color}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              </div>
            </Col>
          ))}
        </Row>
      </div>

      {/* 任务列表 */}
      <Card className="beautiful-card">
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          {/* 工具栏 */}
          <Row justify="space-between" align="middle">
            <Col>
              <h2 className="section-title" style={{ marginBottom: 0 }}>
                <BarsOutlined style={{ marginRight: 8 }} />
                任务列表
              </h2>
            </Col>
            <Col>
              <Space>
                <Input
                  placeholder="搜索任务ID"
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={e => setSearchText(e.target.value)}
                  style={{ width: 200 }}
                />
                <Select
                  value={statusFilter}
                  onChange={setStatusFilter}
                  style={{ width: 120 }}
                >
                  <Option value="all">全部状态</Option>
                  <Option value="pending">待处理</Option>
                  <Option value="running">运行中</Option>
                  <Option value="completed">已完成</Option>
                  <Option value="failed">失败</Option>
                </Select>
                <Segmented
                  options={[
                    { value: 'card', icon: <AppstoreOutlined /> },
                    { value: 'list', icon: <BarsOutlined /> }
                  ]}
                  value={viewMode}
                  onChange={setViewMode as any}
                />
                <Button 
                  icon={<ReloadOutlined />}
                  onClick={loadTasks}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            </Col>
          </Row>

          {/* 任务列表内容 */}
          {loading ? (
            <div className="loading-container">
              <Spin size="large" />
            </div>
          ) : filteredTasks.length === 0 ? (
            <Empty
              className="empty-state"
              description={
                <Space direction="vertical">
                  <div className="empty-state-icon">📋</div>
                  <div className="empty-state-text">
                    {searchText || statusFilter !== 'all' 
                      ? '没有符合条件的任务' 
                      : '暂无任务，点击上方工作流卡片创建'}
                  </div>
                </Space>
              }
            />
          ) : (
            <Space direction="vertical" size={0} style={{ width: '100%' }}>
              {filteredTasks.map(renderTaskCard)}
            </Space>
          )}
        </Space>
      </Card>

      {/* 浮动创建按钮 */}
      <div 
        className="float-button"
        onClick={() => setCreateModalVisible(true)}
      >
        <PlusOutlined />
      </div>

      {/* 弹窗组件 */}
      <CreateTaskModal
        visible={createModalVisible}
        workflowKey={selectedWorkflow}
        onClose={() => {
          setCreateModalVisible(false);
          setSelectedWorkflow('');
        }}
        onSuccess={() => {
          setCreateModalVisible(false);
          setSelectedWorkflow('');
          loadTasks();
          message.success('任务创建成功');
        }}
      />

      <TaskDetailDrawer
        visible={detailDrawerVisible}
        task={selectedTask}
        onClose={() => {
          setDetailDrawerVisible(false);
          setSelectedTask(null);
        }}
      />

      <PublishModal
        visible={publishModalVisible}
        task={selectedTask}
        onClose={() => {
          setPublishModalVisible(false);
          setSelectedTask(null);
        }}
        onSuccess={() => {
          setPublishModalVisible(false);
          setSelectedTask(null);
          message.success('发布成功');
        }}
      />

      <RealtimeMonitor
        visible={monitorModalVisible}
        taskId={selectedTask?.task_id}
        onClose={() => {
          setMonitorModalVisible(false);
          setSelectedTask(null);
        }}
      />
    </div>
  );
};

export default TaskCenter;