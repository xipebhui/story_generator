import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Progress,
  List,
  Tag,
  Space,
  Timeline,
  Button,
  Empty,
  Badge,
  Tooltip
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  RocketOutlined,
  VideoCameraOutlined,
  YoutubeOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';

interface ExecutorDashboardProps {
  status: 'running' | 'stopped';
}

const ExecutorDashboard: React.FC<ExecutorDashboardProps> = ({ status }) => {
  const [stats, setStats] = useState({
    totalTasks: 156,
    completedTasks: 120,
    runningTasks: 5,
    failedTasks: 8,
    pendingTasks: 23,
    successRate: 93.75
  });

  const [recentTasks, setRecentTasks] = useState([
    {
      task_id: 'task_001',
      account_id: 'yt_001_novel',
      pipeline_id: 'story_v3',
      status: 'completed',
      created_at: new Date().toISOString(),
      duration: 320
    },
    {
      task_id: 'task_002',
      account_id: 'yt_002_novel',
      pipeline_id: 'story_v3',
      status: 'running',
      created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      duration: 0
    },
    {
      task_id: 'task_003',
      account_id: 'yt_003_novel',
      pipeline_id: 'news_v1',
      status: 'failed',
      created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      duration: 180,
      error: 'Pipeline执行失败'
    }
  ]);

  // 性能数据
  const performanceData = [
    { time: '00:00', tasks: 12, success: 11 },
    { time: '04:00', tasks: 8, success: 8 },
    { time: '08:00', tasks: 15, success: 14 },
    { time: '12:00', tasks: 20, success: 18 },
    { time: '16:00', tasks: 18, success: 17 },
    { time: '20:00', tasks: 16, success: 15 }
  ];

  // 任务分布数据
  const distributionData = [
    { type: '故事生成', value: 65 },
    { type: '新闻汇总', value: 25 },
    { type: '教程制作', value: 10 }
  ];


  const getStatusIcon = (taskStatus: string) => {
    switch (taskStatus) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  const getStatusTag = (taskStatus: string) => {
    const statusMap = {
      completed: { text: '已完成', color: 'success' },
      running: { text: '执行中', color: 'processing' },
      failed: { text: '失败', color: 'error' },
      pending: { text: '待执行', color: 'warning' }
    };
    const config = statusMap[taskStatus as keyof typeof statusMap];
    return <Tag color={config?.color}>{config?.text}</Tag>;
  };

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.totalTasks}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completedTasks}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="执行中"
              value={stats.runningTasks}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#1890ff' }}
              suffix={
                <Badge
                  status="processing"
                  text=""
                  style={{ marginLeft: 8 }}
                />
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats.successRate}
              precision={2}
              suffix="%"
              valueStyle={{ color: stats.successRate >= 90 ? '#52c41a' : '#faad14' }}
            />
            <Progress
              percent={stats.successRate}
              strokeColor={stats.successRate >= 90 ? '#52c41a' : '#faad14'}
              showInfo={false}
              size="small"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表展示 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="24小时任务趋势">
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Space direction="vertical" align="center">
                <div style={{ fontSize: 48, color: '#1890ff' }}>📈</div>
                <div>任务执行趋势</div>
                <Space>
                  {performanceData.map((item, index) => (
                    <Tag key={index} color="blue">
                      {item.time}: {item.tasks}个
                    </Tag>
                  ))}
                </Space>
              </Space>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="任务类型分布">
            <div style={{ height: 300 }}>
              {distributionData.map((item, index) => (
                <div key={index} style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 4 }}>
                    <Space>
                      <span>{item.type}</span>
                      <Tag color="blue">{item.value}%</Tag>
                    </Space>
                  </div>
                  <Progress percent={item.value} strokeColor="#1890ff" />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 最近任务 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title="最近任务"
            extra={
              <Button type="link" size="small">
                查看全部
              </Button>
            }
          >
            <List
              dataSource={recentTasks}
              renderItem={task => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getStatusIcon(task.status)}
                    title={
                      <Space>
                        <span>{task.task_id}</span>
                        {getStatusTag(task.status)}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={0}>
                        <span>账号: {task.account_id}</span>
                        <span>Pipeline: {task.pipeline_id}</span>
                        {task.duration > 0 && (
                          <span>耗时: {Math.floor(task.duration / 60)}分{task.duration % 60}秒</span>
                        )}
                        {task.error && (
                          <span style={{ color: '#ff4d4f' }}>错误: {task.error}</span>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="执行时间线">
            <Timeline>
              <Timeline.Item color="green" dot={<CheckCircleOutlined />}>
                <p>09:00 - 账号组A 发布成功</p>
                <p style={{ fontSize: 12, color: '#999' }}>3个账号全部发布成功</p>
              </Timeline.Item>
              <Timeline.Item color="blue" dot={<SyncOutlined spin />}>
                <p>10:30 - 账号组B 正在执行</p>
                <p style={{ fontSize: 12, color: '#999' }}>已完成1/3个账号</p>
              </Timeline.Item>
              <Timeline.Item color="red" dot={<CloseCircleOutlined />}>
                <p>11:15 - 账号组C 执行失败</p>
                <p style={{ fontSize: 12, color: '#999' }}>Pipeline执行错误，已发送告警</p>
              </Timeline.Item>
              <Timeline.Item color="gray" dot={<ClockCircleOutlined />}>
                <p>14:00 - 账号组D 待执行</p>
                <p style={{ fontSize: 12, color: '#999' }}>预计5个账号待发布</p>
              </Timeline.Item>
            </Timeline>
          </Card>
        </Col>
      </Row>

      {/* 系统状态 */}
      <Card title="系统状态" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <span>执行器状态</span>
              <Tag color={status === 'running' ? 'success' : 'default'} style={{ fontSize: 14 }}>
                {status === 'running' ? '运行中' : '已停止'}
              </Tag>
            </Space>
          </Col>
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <span>Pipeline并发数</span>
              <Progress percent={60} steps={5} size="small" />
              <span style={{ fontSize: 12, color: '#999' }}>3/5</span>
            </Space>
          </Col>
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <span>发布并发数</span>
              <Progress percent={40} steps={5} size="small" />
              <span style={{ fontSize: 12, color: '#999' }}>2/5</span>
            </Space>
          </Col>
          <Col span={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <span>队列长度</span>
              <Badge count={stats.pendingTasks} showZero style={{ backgroundColor: '#faad14' }}>
                <span style={{ fontSize: 14 }}>{stats.pendingTasks} 个待执行</span>
              </Badge>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default ExecutorDashboard;