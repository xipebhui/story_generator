import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Input,
  Select,
  Empty,
  Spin,
  message,
  Tabs,
  Avatar,
  Dropdown,
  Badge,
  Tooltip,
  Progress
} from 'antd';
import {
  PlusOutlined,
  VideoCameraOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  MoreOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  CloudUploadOutlined,
  BookOutlined,
  PictureOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined
} from '@ant-design/icons';
import CreateTaskModal from '../../components/CreateTaskModal';
import TaskDetailDrawer from '../../components/TaskDetailDrawer';
import PublishModal from '../../components/PublishModal';
import RealtimeMonitor from '../../components/RealtimeMonitor';
import { pipelineService } from '../../services/pipeline';
import { Task, TaskStatus } from '../../types/task';
import { workflows } from '../../config/workflows';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import '../../styles/modern.css';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { TabPane } = Tabs;
const { Option } = Select;

const Dashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [publishModalVisible, setPublishModalVisible] = useState(false);
  const [monitorModalVisible, setMonitorModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchText, setSearchText] = useState('');

  // 统计数据
  const [stats, setStats] = useState({
    total: 0,
    running: 0,
    completed: 0,
    failed: 0,
    successRate: 0,
    avgDuration: 0
  });

  // 加载任务列表
  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await pipelineService.listTasks();
      const taskList = response.tasks || [];
      setTasks(taskList);
      
      // 计算统计数据
      const newStats = {
        total: taskList.length,
        running: taskList.filter((t: Task) => t.status === 'running').length,
        completed: taskList.filter((t: Task) => t.status === 'completed').length,
        failed: taskList.filter((t: Task) => t.status === 'failed').length,
        successRate: 0,
        avgDuration: 0
      };
      
      if (newStats.total > 0) {
        newStats.successRate = Math.round((newStats.completed / newStats.total) * 100);
      }
      
      setStats(newStats);
    } catch (error) {
      message.error('加载任务失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 10000);
    return () => clearInterval(interval);
  }, []);

  // 过滤任务
  const getFilteredTasks = () => {
    let filtered = tasks;
    
    // 按标签过滤
    if (activeTab !== 'all') {
      filtered = filtered.filter(task => task.status === activeTab);
    }
    
    // 按搜索词过滤
    if (searchText) {
      filtered = filtered.filter(task => 
        task.task_id.toLowerCase().includes(searchText.toLowerCase())
      );
    }
    
    return filtered;
  };

  // 获取任务操作菜单
  const getTaskMenu = (task: Task) => ({
    items: [
      {
        key: 'view',
        label: '查看详情',
        icon: <EyeOutlined />,
        onClick: () => {
          setSelectedTask(task);
          setDetailDrawerVisible(true);
        }
      },
      {
        key: 'monitor',
        label: '实时监控',
        icon: <SyncOutlined />,
        disabled: task.status !== 'running',
        onClick: () => {
          setSelectedTask(task);
          setMonitorModalVisible(true);
        }
      },
      {
        key: 'publish',
        label: '发布',
        icon: <CloudUploadOutlined />,
        disabled: task.status !== 'completed',
        onClick: () => {
          setSelectedTask(task);
          setPublishModalVisible(true);
        }
      }
    ]
  });

  // 渲染统计卡片
  const renderStatCard = (title: string, value: number, icon: React.ReactNode, color: string, trend?: number) => (
    <div className="stat-card">
      <div className="stat-card-icon" style={{ background: `${color}20`, color }}>
        {icon}
      </div>
      <div className="stat-card-value" style={{ color }}>
        {value}
      </div>
      <div className="stat-card-label">{title}</div>
      {trend !== undefined && (
        <div className={`stat-card-change ${trend >= 0 ? 'positive' : 'negative'}`}>
          {trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {Math.abs(trend)}%
        </div>
      )}
    </div>
  );

  // 渲染任务项
  const renderTaskItem = (task: Task) => {
    const statusColors = {
      pending: '#8898aa',
      running: '#5e72e4',
      completed: '#2dce89',
      failed: '#f5365c'
    };

    const statusIcons = {
      pending: <ClockCircleOutlined />,
      running: <SyncOutlined spin />,
      completed: <CheckCircleOutlined />,
      failed: <CloseCircleOutlined />
    };

    const progress = task.status === 'running' ? 45 : 
                    task.status === 'completed' ? 100 : 
                    task.status === 'failed' ? 0 : 0;

    return (
      <div key={task.task_id} className="task-item animate-fadeIn">
        <div className="task-item-header">
          <div>
            <div className="task-item-title">{task.task_id}</div>
            <div className="task-item-meta">
              <span className={`status-tag ${task.status}`}>
                {statusIcons[task.status as TaskStatus]}
                {task.status}
              </span>
              <span>创建于 {dayjs(task.created_at).fromNow()}</span>
            </div>
          </div>
          <Dropdown menu={getTaskMenu(task)} trigger={['click']}>
            <Button 
              type="text" 
              icon={<MoreOutlined />}
              className="btn-icon btn-ghost"
            />
          </Dropdown>
        </div>
        {task.status === 'running' && (
          <div className="task-item-progress">
            <div className="task-progress-bar">
              <div 
                className="task-progress-fill"
                style={{ 
                  width: `${progress}%`,
                  background: statusColors[task.status as TaskStatus]
                }}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  const filteredTasks = getFilteredTasks();

  return (
    <div style={{ minHeight: '100vh', background: '#f6f9fc' }}>
      {/* 头部 */}
      <div className="modern-header">
        <div className="modern-container">
          <div className="modern-header-content">
            <div className="modern-logo">
              <div className="modern-logo-icon">
                <VideoCameraOutlined />
              </div>
              <span>视频创作工作台</span>
            </div>
            <Space>
              <Button 
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalVisible(true)}
                className="btn btn-primary"
              >
                创建任务
              </Button>
            </Space>
          </div>
        </div>
      </div>

      <div className="modern-container" style={{ paddingTop: 32, paddingBottom: 32 }}>
        {/* 统计卡片 */}
        <Row gutter={24} style={{ marginBottom: 32 }}>
          <Col xs={24} sm={12} md={6}>
            {renderStatCard('总任务', stats.total, <BarChartOutlined />, '#5e72e4')}
          </Col>
          <Col xs={24} sm={12} md={6}>
            {renderStatCard('运行中', stats.running, <SyncOutlined />, '#fb6340')}
          </Col>
          <Col xs={24} sm={12} md={6}>
            {renderStatCard('已完成', stats.completed, <CheckCircleOutlined />, '#2dce89', 12)}
          </Col>
          <Col xs={24} sm={12} md={6}>
            {renderStatCard('成功率', stats.successRate, <ThunderboltOutlined />, '#11cdef')}
          </Col>
        </Row>

        {/* 工作流选择 */}
        <Card 
          title="选择工作流" 
          style={{ marginBottom: 32 }}
          bordered={false}
          className="animate-fadeIn"
        >
          <Row gutter={24}>
            {workflows.map(workflow => (
              <Col xs={24} md={8} key={workflow.key}>
                <div 
                  className={`workflow-select-card ${selectedWorkflow === workflow.key ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedWorkflow(workflow.key);
                    setCreateModalVisible(true);
                  }}
                >
                  <div 
                    className="workflow-icon-wrapper"
                    style={{ background: workflow.gradient }}
                  >
                    {workflow.icon}
                  </div>
                  <div className="workflow-select-title">{workflow.name}</div>
                  <div className="workflow-select-desc">{workflow.description}</div>
                </div>
              </Col>
            ))}
          </Row>
        </Card>

        {/* 任务列表 */}
        <Card 
          title="任务列表"
          bordered={false}
          extra={
            <Space>
              <Input
                placeholder="搜索任务"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                style={{ width: 200 }}
              />
              <Button icon={<FilterOutlined />}>筛选</Button>
            </Space>
          }
        >
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            items={[
              { key: 'all', label: `全部 (${tasks.length})` },
              { key: 'running', label: `运行中 (${stats.running})` },
              { key: 'completed', label: `已完成 (${stats.completed})` },
              { key: 'failed', label: `失败 (${stats.failed})` }
            ]}
          />

          {loading ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">暂无任务</div>
              <div className="empty-state-desc">
                点击上方的工作流卡片创建你的第一个任务
              </div>
              <Button 
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalVisible(true)}
                className="btn btn-primary"
              >
                创建任务
              </Button>
            </div>
          ) : (
            <div style={{ marginTop: 24 }}>
              {filteredTasks.map(renderTaskItem)}
            </div>
          )}
        </Card>
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

export default Dashboard;