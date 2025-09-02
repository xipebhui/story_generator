import React, { useState, useEffect } from 'react';
import { Tabs, Card, Button, Space, Tooltip, Badge, Alert } from 'antd';
import {
  TeamOutlined,
  SettingOutlined,
  CalendarOutlined,
  ExperimentOutlined,
  DashboardOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  BarChartOutlined,
  AppstoreOutlined,
  ControlOutlined
} from '@ant-design/icons';
import GlobalOverview from './GlobalOverview';
import PipelineManagement from './PipelineManagement';
import PublishConfigManagement from './PublishConfigManagement';
import TaskExecutionManager from './TaskExecutionManager';
import AccountGroupManagerEnhanced from './AccountGroupManagerEnhanced';
import AccountGroupManager from './AccountGroupManager';
import ScheduleCalendar from './ScheduleCalendar';
import StrategyManager from './StrategyManager';
import ExecutorDashboard from './ExecutorDashboard';

const { TabPane } = Tabs;

const AutoPublish: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [executorStatus, setExecutorStatus] = useState<'running' | 'stopped'>('stopped');

  const handleExecutorToggle = () => {
    // 切换执行器状态
    setExecutorStatus(prev => prev === 'running' ? 'stopped' : 'running');
  };

  // 监听全局概览组件的tab切换事件
  useEffect(() => {
    const handleTabChange = (event: CustomEvent) => {
      const { activeTab } = event.detail;
      setActiveTab(activeTab);
    };

    window.addEventListener('tabChange', handleTabChange as EventListener);
    
    // 从URL参数中获取初始tab
    const urlParams = new URLSearchParams(window.location.search);
    const tabFromUrl = urlParams.get('tab');
    if (tabFromUrl) {
      setActiveTab(tabFromUrl);
    }

    return () => {
      window.removeEventListener('tabChange', handleTabChange as EventListener);
    };
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <DashboardOutlined />
            <span>账号驱动自动发布系统</span>
            <Badge
              status={executorStatus === 'running' ? 'processing' : 'default'}
              text={executorStatus === 'running' ? '运行中' : '已停止'}
            />
          </Space>
        }
        extra={
          <Space>
            <Tooltip title={executorStatus === 'running' ? '停止执行器' : '启动执行器'}>
              <Button
                type={executorStatus === 'running' ? 'default' : 'primary'}
                icon={executorStatus === 'running' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handleExecutorToggle}
              >
                {executorStatus === 'running' ? '停止' : '启动'}
              </Button>
            </Tooltip>
            <Tooltip title="刷新">
              <Button icon={<ReloadOutlined />} />
            </Tooltip>
          </Space>
        }
      >
        <Alert
          message="系统说明"
          description="账号驱动自动发布系统支持多账号组管理、Pipeline动态配置、环形调度、A/B测试等功能。请先配置账号组和发布配置，然后启动执行器开始自动发布。"
          type="info"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <Space>
                <BarChartOutlined />
                全局概览
              </Space>
            }
            key="overview"
          >
            <GlobalOverview />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <AppstoreOutlined />
                Pipeline管理
              </Space>
            }
            key="pipelines"
          >
            <PipelineManagement />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <ControlOutlined />
                发布配置
              </Space>
            }
            key="configs"
          >
            <PublishConfigManagement />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <PlayCircleOutlined />
                执行记录
              </Space>
            }
            key="tasks"
          >
            <TaskExecutionManager />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <TeamOutlined />
                账号组管理
              </Space>
            }
            key="groups"
          >
            <AccountGroupManagerEnhanced />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <CalendarOutlined />
                调度日历
              </Space>
            }
            key="schedule"
          >
            <ScheduleCalendar />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <DashboardOutlined />
                执行器仪表盘
              </Space>
            }
            key="dashboard"
          >
            <ExecutorDashboard status={executorStatus} />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <ExperimentOutlined />
                策略管理
              </Space>
            }
            key="strategies"
          >
            <StrategyManager />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default AutoPublish;