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
  Badge,
  Tooltip,
  Progress,
  Modal,
  Dropdown,
  Menu
} from 'antd';
import {
  PlusOutlined,
  VideoCameraOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  CloudUploadOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  UserOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  LogoutOutlined,
  KeyOutlined,
  SettingOutlined
} from '@ant-design/icons';
import CreateTaskModal from '../../components/CreateTaskModal';
import TaskDetailDrawer from '../../components/TaskDetailDrawer';
import PublishModal from '../../components/PublishModal';
import AccountManager from '../../components/AccountManager';
import PublishStatus from '../../components/PublishStatus';
import { pipelineAdapter } from '../../services/pipelineAdapter';
import { Task, TaskStatus } from '../../types/task';
import { workflows } from '../../config/workflows';
import { authService } from '../../services/auth';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import '../../styles/modern.css';
import '../../styles/dashboard.css';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { TabPane } = Tabs;
const { Option } = Select;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [publishModalVisible, setPublishModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchText, setSearchText] = useState('');
  const [mainTab, setMainTab] = useState<string>('tasks');
  const [lastRefreshTime, setLastRefreshTime] = useState<Date>(new Date());

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
  const loadTasks = async (isManualRefresh: boolean = false) => {
    setLoading(true);
    try {
      const response = await pipelineAdapter.listTasks();
      const taskList = response.tasks || [];
      setTasks(taskList);
      setLastRefreshTime(new Date());
      
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
      
      // 手动刷新时显示成功提示
      if (isManualRefresh) {
        message.success('刷新成功');
      }
    } catch (error) {
      message.error('加载任务失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    // 改为20秒刷新一次
    const interval = setInterval(loadTasks, 20000);
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
      running: <SyncOutlined />,
      completed: <CheckCircleOutlined />,
      failed: <CloseCircleOutlined />,
      cancelled: <CloseCircleOutlined />
    };

    const progress = typeof task.progress === 'number' 
                    ? task.progress 
                    : task.status === 'running' ? 45 
                    : task.status === 'completed' ? 100 
                    : task.status === 'failed' ? 0 : 0;

    return (
      <div key={task.task_id} className={`task-item animate-fadeIn ${task.status}`}>
        <div className="task-item-header">
          <div style={{ flex: 1 }}>
            <div 
              className="task-item-title"
              style={{ cursor: 'pointer', color: '#1890ff' }}
              onClick={() => {
                setSelectedTask(task);
                setDetailDrawerVisible(true);
              }}
            >
              {task.task_id}
            </div>
            <div className="task-item-meta">
              <span className={`status-tag ${task.status}`}>
                {statusIcons[task.status as TaskStatus]}
                {task.status}
              </span>
              <span>创建于 {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}</span>
              {(task.total_duration || task.duration) && (
                <span>
                  耗时: {Math.round(task.total_duration || task.duration || 0)}秒
                </span>
              )}
              {task.status === 'running' && task.current_stage && (
                <span className="task-stage-info running">
                  {task.current_stage}
                </span>
              )}
            </div>
            {task.status === 'failed' && (
              <div className="error-info">
                <ExclamationCircleOutlined />
                <div>
                  <span className="error-stage">
                    失败阶段: {(() => {
                      // 从 progress 对象中找到失败的阶段
                      if (task.progress && typeof task.progress === 'object' && !Array.isArray(task.progress)) {
                        const failedStage = Object.entries(task.progress).find(([_, status]) => 
                          status === '失败' || status === 'failed'
                        );
                        return failedStage ? failedStage[0] : task.current_stage || '未知';
                      }
                      return task.current_stage || '未知';
                    })()}
                  </span>
                  {task.error_message && (
                    <div className="error-message">
                      {task.error_message}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          <Space>
            {task.status === 'failed' && (
              <Button 
                type="primary"
                danger
                icon={<ReloadOutlined />}
                onClick={async () => {
                  try {
                    message.loading('正在重试任务...');
                    // 立即更新UI状态为running
                    setTasks(prevTasks => 
                      prevTasks.map(t => 
                        t.task_id === task.task_id 
                          ? { ...t, status: 'pending' as TaskStatus, progress: 0, error_message: undefined }
                          : t
                      )
                    );
                    
                    // 调用重试接口
                    const updatedTask = await pipelineAdapter.retryTask(task.task_id);
                    
                    // 更新本地任务状态
                    setTasks(prevTasks => 
                      prevTasks.map(t => 
                        t.task_id === task.task_id ? updatedTask : t
                      )
                    );
                    
                    message.success('任务重试成功');
                  } catch (error) {
                    message.error('重试任务失败');
                    console.error('重试任务失败:', error);
                    // 失败时恢复原状态
                    loadTasks();
                  }
                }}
              >
                重试
              </Button>
            )}
            <Button 
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除任务 ${task.task_id} 吗？此操作不可恢复。`,
                  okText: '确认删除',
                  cancelText: '取消',
                  okButtonProps: { danger: true },
                  onOk: async () => {
                    try {
                      message.loading('正在删除任务...');
                      await pipelineAdapter.deleteTask(task.task_id);
                      message.success('任务删除成功');
                      // 刷新任务列表
                      loadTasks();
                    } catch (error) {
                      message.error('删除任务失败');
                      console.error('删除任务失败:', error);
                    }
                  }
                });
              }}
            >
              删除
            </Button>
          </Space>
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

  // 处理登出
  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  // 用户下拉菜单
  const userMenu = (
    <Menu>
      <Menu.Item key="user" disabled>
        <UserOutlined /> {authService.getUsername()}
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="apikey" icon={<KeyOutlined />} onClick={() => message.info('API密钥管理功能开发中')}>
        API密钥管理
      </Menu.Item>
      <Menu.Item key="settings" icon={<SettingOutlined />} onClick={() => message.info('设置功能开发中')}>
        设置
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={handleLogout}>
        退出登录
      </Menu.Item>
    </Menu>
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
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
              <Dropdown overlay={userMenu} placement="bottomRight">
                <Button type="text" icon={<UserOutlined />}>
                  {authService.getUsername()}
                </Button>
              </Dropdown>
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

        {/* 主内容Tab */}
        <Tabs
          activeKey={mainTab}
          onChange={setMainTab}
          size="large"
          items={[
            {
              key: 'tasks',
              label: (
                <Space>
                  <BarChartOutlined />
                  任务管理
                </Space>
              ),
              children: (
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
                      <Tooltip title="手动刷新 (每20秒自动刷新)">
                        <Button 
                          icon={<ReloadOutlined />}
                          onClick={() => loadTasks(true)}
                          loading={loading}
                        >
                          刷新
                        </Button>
                      </Tooltip>
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
              )
            },
            {
              key: 'publish',
              label: (
                <Space>
                  <CloudUploadOutlined />
                  发布状态
                </Space>
              ),
              children: <PublishStatus />
            },
            {
              key: 'accounts',
              label: (
                <Space>
                  <UserOutlined />
                  账号管理
                </Space>
              ),
              children: <AccountManager />
            }
          ]}
        />
        
        {/* 自动刷新指示器 */}
        <div className="auto-refresh-indicator">
          <SyncOutlined />
          <span>上次刷新: {dayjs(lastRefreshTime).format('HH:mm:ss')}</span>
          <span style={{ color: '#595959' }}>· 每20秒自动刷新</span>
        </div>
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
        onPublish={(task) => {
          setPublishModalVisible(true);
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
    </div>
  );
};

export default Dashboard;