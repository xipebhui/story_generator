import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Space,
  Typography,
  Button,
  Alert,
  Spin,
  Divider,
  Row,
  Col,
  Statistic,
  Result,
} from 'antd';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  AudioOutlined,
  VideoCameraOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import pipelineService from '@/services/pipeline';
import { TaskStatusResponse, TaskResultResponse } from '@/types/task';
import TaskProgress from '@/components/TaskProgress';
import { formatDateTime, formatDuration } from '@/utils/format';

const { Title, Text, Paragraph } = Typography;

const TaskMonitor: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const [result, setResult] = useState<TaskResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // 获取任务状态
  const fetchStatus = useCallback(async () => {
    if (!taskId) return;
    
    try {
      const statusData = await pipelineService.getTaskStatus(taskId);
      setStatus(statusData);
      
      // 如果任务完成或失败，获取结果
      if (statusData.status === 'completed' || statusData.status === 'failed') {
        const resultData = await pipelineService.getTaskResult(taskId);
        setResult(resultData);
        
        // 停止轮询
        if (pollInterval) {
          clearInterval(pollInterval);
          setPollInterval(null);
        }
      }
      
      setLoading(false);
    } catch (err: any) {
      setError(err.message || '获取任务状态失败');
      setLoading(false);
      
      // 停止轮询
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }
    }
  }, [taskId, pollInterval]);

  // 设置轮询
  useEffect(() => {
    fetchStatus();
    
    // 每3秒轮询一次
    const interval = setInterval(() => {
      fetchStatus();
    }, 3000);
    
    setPollInterval(interval);
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [taskId]);

  // 计算耗时
  useEffect(() => {
    if (status?.created_at && !status?.completed_at) {
      const timer = setInterval(() => {
        const start = new Date(status.created_at).getTime();
        const now = new Date().getTime();
        setElapsedTime(Math.floor((now - start) / 1000));
      }, 1000);
      
      return () => clearInterval(timer);
    }
  }, [status]);

  if (loading && !status) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
        <div style={{ marginTop: 20 }}>
          <Text type="secondary">加载任务信息...</Text>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="error"
        title="加载失败"
        subTitle={error}
        extra={[
          <Button key="retry" type="primary" onClick={fetchStatus}>
            重试
          </Button>,
          <Button key="back" onClick={() => navigate('/tasks')}>
            返回列表
          </Button>,
        ]}
      />
    );
  }

  if (!status) {
    return (
      <Result
        status="404"
        title="任务不存在"
        subTitle={`找不到任务ID: ${taskId}`}
        extra={
          <Button type="primary" onClick={() => navigate('/create')}>
            创建新任务
          </Button>
        }
      />
    );
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />;
      case 'running':
        return <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9', fontSize: 24 }} />;
    }
  };

  return (
    <div>
      <Title level={2}>任务监控</Title>
      
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="任务ID"
              value={taskId}
              valueStyle={{ fontSize: 14 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="任务状态"
              value={status.status === 'completed' ? '已完成' : 
                     status.status === 'failed' ? '失败' :
                     status.status === 'running' ? '运行中' : '待处理'}
              prefix={getStatusIcon()}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="当前阶段"
              value={status.current_stage || '无'}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行时长"
              value={formatDuration(elapsedTime)}
            />
          </Card>
        </Col>
      </Row>

      <Card title="任务进度" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {Object.entries(status.progress).map(([stage, stageStatus]) => (
            <TaskProgress
              key={stage}
              stageName={stage}
              status={stageStatus}
            />
          ))}
        </Space>
      </Card>

      {result && result.status === 'completed' && (
        <>
          <Card title="生成结果" style={{ marginBottom: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {result.story_path && (
                <div>
                  <FileTextOutlined /> 故事文本：
                  <Text copyable={{ text: result.story_path }}>
                    {result.story_path}
                  </Text>
                </div>
              )}
              {result.audio_path && (
                <div>
                  <AudioOutlined /> 音频文件：
                  <Text copyable={{ text: result.audio_path }}>
                    {result.audio_path}
                  </Text>
                </div>
              )}
              {result.draft_path && (
                <div>
                  <FolderOutlined /> 剪映草稿：
                  <Text copyable={{ text: result.draft_path }}>
                    {result.draft_path}
                  </Text>
                </div>
              )}
              {result.video_path && (
                <div>
                  <VideoCameraOutlined /> 视频文件：
                  <Text copyable={{ text: result.video_path }}>
                    {result.video_path}
                  </Text>
                </div>
              )}
            </Space>
          </Card>

          {result.youtube_metadata && (
            <Card title="YouTube元数据" style={{ marginBottom: 24 }}>
              <Paragraph>
                <Text strong>标题：</Text>
                {result.youtube_metadata.title}
              </Paragraph>
              <Paragraph>
                <Text strong>描述：</Text>
                {result.youtube_metadata.description}
              </Paragraph>
              <Paragraph>
                <Text strong>标签：</Text>
                {result.youtube_metadata.tags.join(', ')}
              </Paragraph>
            </Card>
          )}

          <Space>
            <Button type="primary" onClick={() => navigate(`/task/${taskId}`)}>
              查看详情
            </Button>
            <Button onClick={() => navigate('/tasks')}>
              返回列表
            </Button>
          </Space>
        </>
      )}

      {result && result.status === 'failed' && (
        <Alert
          message="任务失败"
          description={result.error || '未知错误'}
          type="error"
          showIcon
        />
      )}
    </div>
  );
};

export default TaskMonitor;