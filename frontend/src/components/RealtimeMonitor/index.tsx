import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Progress,
  Space,
  Tag,
  Timeline,
  Card,
  Row,
  Col,
  Statistic,
  Alert,
  Button,
  Typography,
  Divider
} from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  RocketOutlined,
  FieldTimeOutlined,
  FileTextOutlined,
  AudioOutlined,
  VideoCameraOutlined,
  FolderOutlined
} from '@ant-design/icons';
import { pipelineService } from '../../services/pipeline';
import { TaskStatus as TaskStatusType } from '../../types/task';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import '../../styles/theme.css';

dayjs.extend(duration);

const { Title, Text } = Typography;
const { Countdown } = Statistic;

interface RealtimeMonitorProps {
  visible: boolean;
  taskId?: string;
  onClose: () => void;
}

interface StageInfo {
  name: string;
  status: string;
  icon: React.ReactNode;
  color: string;
}

const RealtimeMonitor: React.FC<RealtimeMonitorProps> = ({
  visible,
  taskId,
  onClose
}) => {
  const [status, setStatus] = useState<TaskStatusType>('pending');
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [progress, setProgress] = useState<Record<string, string>>({});
  const [startTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 阶段配置
  const stages: StageInfo[] = [
    {
      name: '故事二创',
      status: progress['故事二创'] || '待处理',
      icon: <FileTextOutlined />,
      color: '#722ED1'
    },
    {
      name: '语音生成',
      status: progress['语音生成'] || '待处理',
      icon: <AudioOutlined />,
      color: '#1890FF'
    },
    {
      name: '剪映草稿生成',
      status: progress['剪映草稿生成'] || '待处理',
      icon: <FolderOutlined />,
      color: '#52C41A'
    },
    {
      name: '视频导出',
      status: progress['视频导出'] || '待处理',
      icon: <VideoCameraOutlined />,
      color: '#FA8C16'
    }
  ];

  // 获取任务状态
  const fetchStatus = async () => {
    if (!taskId) return;

    try {
      const data = await pipelineService.getStatus(taskId);
      setStatus(data.status);
      setCurrentStage(data.current_stage);
      setProgress(data.progress || {});

      // 如果任务完成或失败，停止轮询
      if (data.status === 'completed' || data.status === 'failed') {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (error) {
      console.error('获取任务状态失败:', error);
    }
  };

  // 更新运行时间
  const updateElapsedTime = () => {
    setElapsedTime(Date.now() - startTime);
  };

  // 启动监控
  useEffect(() => {
    if (visible && taskId) {
      // 立即获取一次状态
      fetchStatus();
      
      // 设置定时获取状态
      intervalRef.current = setInterval(() => {
        fetchStatus();
        updateElapsedTime();
      }, 3000);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [visible, taskId]);

  // 获取阶段状态图标
  const getStageIcon = (status: string) => {
    switch (status) {
      case '成功':
        return <CheckCircleOutlined style={{ color: '#52C41A' }} />;
      case '失败':
        return <CloseCircleOutlined style={{ color: '#FF4D4F' }} />;
      case '运行中':
        return <LoadingOutlined style={{ color: '#1890FF' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#8C8C8C' }} />;
    }
  };

  // 获取阶段颜色
  const getStageColor = (status: string) => {
    switch (status) {
      case '成功':
        return 'green';
      case '失败':
        return 'red';
      case '运行中':
        return 'blue';
      default:
        return 'gray';
    }
  };

  // 计算总体进度
  const calculateProgress = () => {
    const total = Object.keys(progress).length;
    if (total === 0) return 0;
    
    const completed = Object.values(progress).filter(s => s === '成功').length;
    return Math.round((completed / total) * 100);
  };

  // 格式化运行时间
  const formatDuration = (ms: number) => {
    const d = dayjs.duration(ms);
    if (d.hours() > 0) {
      return `${d.hours()}小时${d.minutes()}分${d.seconds()}秒`;
    } else if (d.minutes() > 0) {
      return `${d.minutes()}分${d.seconds()}秒`;
    } else {
      return `${d.seconds()}秒`;
    }
  };

  return (
    <Modal
      title={
        <Space>
          <SyncOutlined spin={status === 'running'} />
          <span>实时监控</span>
          {status === 'running' && (
            <Tag color="processing">执行中</Tag>
          )}
          {status === 'completed' && (
            <Tag color="success">已完成</Tag>
          )}
          {status === 'failed' && (
            <Tag color="error">失败</Tag>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>
      ]}
      className="monitor-modal"
    >
      <Space direction="vertical" size={24} style={{ width: '100%' }}>
        {/* 任务信息 */}
        <Card size="small" style={{ background: '#f0f2f5' }}>
          <Row gutter={16}>
            <Col span={16}>
              <Space>
                <Text type="secondary">任务ID:</Text>
                <Text code>{taskId}</Text>
              </Space>
            </Col>
            <Col span={8} style={{ textAlign: 'right' }}>
              <Space>
                <FieldTimeOutlined />
                <Text>运行时长: {formatDuration(elapsedTime)}</Text>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 总体进度 */}
        <div>
          <div style={{ marginBottom: 12, fontWeight: 500 }}>
            总体进度
          </div>
          <Progress
            percent={calculateProgress()}
            status={
              status === 'failed' ? 'exception' :
              status === 'completed' ? 'success' :
              'active'
            }
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068'
            }}
            className="beautiful-progress"
          />
        </div>

        {/* 阶段进度 */}
        <div>
          <div style={{ marginBottom: 16, fontWeight: 500 }}>
            <RocketOutlined style={{ marginRight: 8 }} />
            执行阶段
          </div>
          <Timeline mode="left">
            {stages.map((stage, index) => (
              <Timeline.Item
                key={stage.name}
                color={getStageColor(stage.status)}
                dot={
                  stage.status === '运行中' ? 
                  <LoadingOutlined style={{ fontSize: 16 }} /> : 
                  getStageIcon(stage.status)
                }
              >
                <Card
                  size="small"
                  className={`stage-card ${stage.status === '运行中' ? 'active' : ''}`}
                  style={{
                    borderLeft: `3px solid ${
                      stage.status === '成功' ? '#52C41A' :
                      stage.status === '失败' ? '#FF4D4F' :
                      stage.status === '运行中' ? '#1890FF' :
                      '#D9D9D9'
                    }`,
                    background: stage.status === '运行中' ? 
                      'linear-gradient(90deg, rgba(24, 144, 255, 0.05) 0%, white 100%)' : 
                      undefined
                  }}
                >
                  <Row align="middle">
                    <Col flex="auto">
                      <Space>
                        <span style={{ fontSize: 20, color: stage.color }}>
                          {stage.icon}
                        </span>
                        <div>
                          <div style={{ fontWeight: 500 }}>{stage.name}</div>
                          <Tag color={
                            stage.status === '成功' ? 'success' :
                            stage.status === '失败' ? 'error' :
                            stage.status === '运行中' ? 'processing' :
                            'default'
                          }>
                            {stage.status}
                          </Tag>
                        </div>
                      </Space>
                    </Col>
                    <Col>
                      {stage.status === '运行中' && (
                        <div className="running-indicator">
                          <div className="pulse"></div>
                        </div>
                      )}
                    </Col>
                  </Row>
                </Card>
              </Timeline.Item>
            ))}
          </Timeline>
        </div>

        {/* 当前执行阶段提示 */}
        {currentStage && status === 'running' && (
          <Alert
            message={`正在执行: ${currentStage}`}
            description="请耐心等待，任务正在处理中..."
            type="info"
            showIcon
            icon={<LoadingOutlined />}
          />
        )}

        {/* 任务完成提示 */}
        {status === 'completed' && (
          <Alert
            message="任务执行成功"
            description="所有阶段已完成，您可以查看任务结果"
            type="success"
            showIcon
          />
        )}

        {/* 任务失败提示 */}
        {status === 'failed' && (
          <Alert
            message="任务执行失败"
            description="请查看任务详情了解失败原因"
            type="error"
            showIcon
          />
        )}
      </Space>
    </Modal>
  );
};

export default RealtimeMonitor;