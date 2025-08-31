import React, { useState } from 'react';
import { Tabs, Card, Button, Space, Tooltip, Badge, Alert } from 'antd';
import {
  TeamOutlined,
  SettingOutlined,
  CalendarOutlined,
  ExperimentOutlined,
  DashboardOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import AccountGroupManager from './AccountGroupManager';
import PublishConfigManager from './PublishConfigManager';
import ScheduleCalendar from './ScheduleCalendar';
import StrategyManager from './StrategyManager';
import ExecutorDashboard from './ExecutorDashboard';

const { TabPane } = Tabs;

const AutoPublish: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [executorStatus, setExecutorStatus] = useState<'running' | 'stopped'>('stopped');

  const handleExecutorToggle = () => {
    // 切换执行器状态
    setExecutorStatus(prev => prev === 'running' ? 'stopped' : 'running');
  };

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
                <TeamOutlined />
                账号组管理
              </Space>
            }
            key="groups"
          >
            <AccountGroupManager />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <SettingOutlined />
                发布配置
              </Space>
            }
            key="configs"
          >
            <PublishConfigManager />
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