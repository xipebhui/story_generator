import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, List, Tag, Radio, Button, message, Spin } from 'antd';
import { ReloadOutlined, RightOutlined, PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { autoPublishService } from '../../services/autoPublish';
import './GlobalOverview.less';

interface OverviewStats {
  pipelines: number;
  configs: number;
  tasks: {
    total: number;
    today: number;
    week: number;
    month: number;
    success: number;
    failed: number;
    running: number;
    pending: number;
  };
  accounts: {
    groups: number;
    total: number;
    active: number;
  };
  taskTimeDistribution: {
    timeRange: string;
    count: number;
    percentage: number;
  }[];
  successRate: {
    today: number;
    week: number;
    month: number;
  };
}

interface TopAccount {
  account_id: string;
  account_name: string;
  metrics: {
    views: number;
    likes: number;
    comments: number;
    subscribers_gained: number;
  };
}

interface RecentTask {
  task_id: string;
  pipeline_name: string;
  account_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  duration?: number;
}

const GlobalOverview: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState<'today' | 'week' | 'month'>('today');
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [topAccounts, setTopAccounts] = useState<TopAccount[]>([]);
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([]);
  const [timeDistribution, setTimeDistribution] = useState<any[]>([]);

  // 加载概览数据
  const loadOverviewData = async () => {
    try {
      setLoading(true);
      
      // 并行加载所有数据
      const [statsData, distributionData, accountsData, tasksData] = await Promise.all([
        autoPublishService.getOverviewStats(period),
        autoPublishService.getTaskTimeDistribution(period),
        autoPublishService.getTopAccounts({ limit: 5, period, metric: 'views' }),
        autoPublishService.getRecentTasks(10)
      ]);

      setStats(statsData);
      setTimeDistribution(distributionData);
      setTopAccounts(accountsData);
      setRecentTasks(tasksData);
    } catch (error) {
      console.error('Failed to load overview data:', error);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载和period变化时重新加载
  useEffect(() => {
    loadOverviewData();
  }, [period]);

  // 手动刷新
  const handleRefresh = () => {
    setLoading(true);
    loadOverviewData().finally(() => {
      setLoading(false);
      message.success('数据已刷新');
    });
  };

  // 跳转到指定Tab
  const handleCardClick = (target: string) => {
    switch(target) {
      case 'pipeline':
        navigate('/auto-publish?tab=pipeline');
        break;
      case 'config':
        navigate('/auto-publish?tab=config');
        break;
      case 'task':
        navigate('/auto-publish?tab=task');
        break;
      case 'account':
        navigate('/auto-publish?tab=account');
        break;
    }
  };

  // 获取任务状态图标
  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      case 'running':
        return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return null;
    }
  };

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`;
    return `${Math.floor(minutes / 1440)}天前`;
  };

  // 格式化数字
  const formatNumber = (num: number) => {
    if (num >= 10000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
  };

  return (
    <Spin spinning={loading}>
      <div className="global-overview">
        {/* 顶部操作栏 */}
        <div className="overview-header">
          <h2>全局概览</h2>
          <div className="header-actions">
            <Radio.Group value={period} onChange={(e) => setPeriod(e.target.value)}>
              <Radio.Button value="today">今日</Radio.Button>
              <Radio.Button value="week">本周</Radio.Button>
              <Radio.Button value="month">本月</Radio.Button>
            </Radio.Group>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} style={{ marginLeft: 16 }}>
              刷新
            </Button>
          </div>
        </div>

        {/* 统计卡片 */}
        <Row gutter={[16, 16]} className="stats-cards">
          <Col xs={24} sm={12} md={6}>
            <Card 
              hoverable 
              onClick={() => handleCardClick('pipeline')}
              className="stat-card"
            >
              <Statistic 
                title="Pipeline" 
                value={stats?.pipelines || 0} 
                suffix="个"
                valueStyle={{ color: '#1890ff' }}
              />
              <div className="card-footer">
                <span>查看详情</span>
                <RightOutlined />
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card 
              hoverable 
              onClick={() => handleCardClick('config')}
              className="stat-card"
            >
              <Statistic 
                title="发布配置" 
                value={stats?.configs || 0} 
                suffix="个"
                valueStyle={{ color: '#52c41a' }}
              />
              <div className="card-footer">
                <span>查看详情</span>
                <RightOutlined />
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card 
              hoverable 
              onClick={() => handleCardClick('task')}
              className="stat-card"
            >
              <Statistic 
                title="执行任务" 
                value={stats?.tasks?.[period] || stats?.tasks?.total || 0} 
                suffix="个"
                valueStyle={{ color: '#faad14' }}
              />
              <div className="card-footer">
                <span>查看详情</span>
                <RightOutlined />
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card 
              hoverable 
              onClick={() => handleCardClick('account')}
              className="stat-card"
            >
              <Statistic 
                title="账号" 
                value={`${stats?.accounts?.groups || 0}组/${stats?.accounts?.total || 0}个`}
                valueStyle={{ color: '#722ed1' }}
              />
              <div className="card-footer">
                <span>查看详情</span>
                <RightOutlined />
              </div>
            </Card>
          </Col>
        </Row>

        {/* 图表区域 */}
        <Row gutter={[16, 16]} className="charts-row">
          <Col xs={24} md={12}>
            <Card title="执行成功率" className="chart-card">
              <div className="success-rate">
                <Progress 
                  percent={stats?.successRate?.[period] || 0} 
                  strokeColor="#52c41a"
                  format={percent => `${percent}%`}
                />
                <div className="rate-detail">
                  {period === 'today' && `今日: ${stats?.tasks?.success || 0}/${stats?.tasks?.today || 0} 成功`}
                  {period === 'week' && `本周: ${stats?.tasks?.success || 0}/${stats?.tasks?.week || 0} 成功`}
                  {period === 'month' && `本月: ${stats?.tasks?.success || 0}/${stats?.tasks?.month || 0} 成功`}
                </div>
              </div>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="任务时间分布" className="chart-card">
              <div className="time-distribution">
                {timeDistribution.map((item) => (
                  <div key={item.timeRange} className="distribution-item">
                    <span className="time-label">{item.timeRange}时:</span>
                    <Progress 
                      percent={item.percentage} 
                      size="small"
                      format={() => `${item.count}个 (${item.percentage}%)`}
                    />
                  </div>
                ))}
              </div>
            </Card>
          </Col>
        </Row>

        {/* 列表区域 */}
        <Row gutter={[16, 16]} className="lists-row">
          <Col xs={24} md={12}>
            <Card 
              title="账号表现TOP5" 
              className="list-card"
              extra={<a onClick={() => handleCardClick('account')}>查看全部</a>}
            >
              <List
                dataSource={topAccounts}
                renderItem={(item, index) => (
                  <List.Item>
                    <div className="account-item">
                      <span className="rank">{index + 1}</span>
                      <span className="name">{item.account_name}</span>
                      <span className="metric">
                        观看: {formatNumber(item.metrics.views)}
                      </span>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card 
              title="最近执行任务" 
              className="list-card"
              extra={<a onClick={() => handleCardClick('task')}>查看全部</a>}
            >
              <List
                dataSource={recentTasks}
                renderItem={(item) => (
                  <List.Item>
                    <div className="task-item">
                      <span className="task-id">{item.task_id}</span>
                      {getStatusIcon(item.status)}
                      <span className="time">{formatTime(item.created_at)}</span>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
};

export default GlobalOverview;