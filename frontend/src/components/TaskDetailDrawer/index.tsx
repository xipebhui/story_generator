import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Descriptions,
  Tabs,
  Card,
  Tag,
  Space,
  Button,
  Tooltip,
  Typography,
  Divider,
  Timeline,
  Alert,
  Spin,
  message,
  Empty
} from 'antd';
import {
  CopyOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  FolderOutlined,
  FileTextOutlined,
  AudioOutlined,
  VideoCameraOutlined,
  YoutubeOutlined,
  TagsOutlined,
  PictureOutlined
} from '@ant-design/icons';
import { Task, TaskResult } from '../../types/task';
import { pipelineService } from '../../services/pipeline';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';

dayjs.extend(duration);

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface TaskDetailDrawerProps {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
}

const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  visible,
  task,
  onClose
}) => {
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载任务结果
  useEffect(() => {
    if (task && task.status === 'completed' && visible) {
      loadTaskResult();
    }
  }, [task, visible]);

  const loadTaskResult = async () => {
    if (!task) return;
    
    setLoading(true);
    try {
      const data = await pipelineService.getResult(task.task_id);
      setResult(data);
    } catch (error) {
      console.error('加载任务结果失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 复制到剪贴板
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    message.success(`${label}已复制到剪贴板`);
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
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
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'default';
      case 'running': return 'processing';
      case 'completed': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // 计算任务耗时
  const getTaskDuration = () => {
    if (!task) return '';
    if (!task.completed_at) return '进行中...';
    
    const start = dayjs(task.created_at);
    const end = dayjs(task.completed_at);
    const diff = end.diff(start);
    const duration = dayjs.duration(diff);
    
    if (duration.hours() > 0) {
      return `${duration.hours()}小时${duration.minutes()}分钟${duration.seconds()}秒`;
    } else if (duration.minutes() > 0) {
      return `${duration.minutes()}分钟${duration.seconds()}秒`;
    } else {
      return `${duration.seconds()}秒`;
    }
  };

  if (!task) return null;

  return (
    <Drawer
      title={
        <Space>
          {getStatusIcon(task.status)}
          <span>任务详情</span>
          <Tag color={getStatusColor(task.status)}>{task.status}</Tag>
        </Space>
      }
      placement="right"
      width={720}
      open={visible}
      onClose={onClose}
      className="task-detail-drawer"
    >
      <Tabs defaultActiveKey="basic">
        <TabPane tab="基本信息" key="basic">
          <Descriptions column={1} bordered>
            <Descriptions.Item label="任务ID">
              <Space>
                <Text code>{task.task_id}</Text>
                <Tooltip title="复制">
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(task.task_id, '任务ID')}
                  />
                </Tooltip>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={getStatusColor(task.status)}>
                {getStatusIcon(task.status)}
                <span style={{ marginLeft: 4 }}>{task.status}</span>
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            {task.completed_at && (
              <Descriptions.Item label="完成时间">
                {dayjs(task.completed_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="耗时">
              {getTaskDuration()}
            </Descriptions.Item>
          </Descriptions>

          {/* 执行进度时间线 */}
          {task.progress && (
            <>
              <Divider>执行进度</Divider>
              <Timeline>
                {Object.entries(task.progress || {}).map(([stage, status]) => (
                  <Timeline.Item
                    key={stage}
                    color={
                      status === '成功' ? 'green' :
                      status === '失败' ? 'red' :
                      status === '运行中' ? 'blue' :
                      'gray'
                    }
                    dot={
                      status === '运行中' ? <SyncOutlined spin /> : undefined
                    }
                  >
                    <Space>
                      <Text strong>{stage}</Text>
                      <Tag color={
                        status === '成功' ? 'success' :
                        status === '失败' ? 'error' :
                        status === '运行中' ? 'processing' :
                        'default'
                      }>
                        {status}
                      </Tag>
                    </Space>
                  </Timeline.Item>
                ))}
              </Timeline>
            </>
          )}
        </TabPane>

        <TabPane tab="生成结果" key="result">
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" />
            </div>
          ) : result ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* 文件路径 */}
              <Card title="生成文件" size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {result.story_path && (
                    <div>
                      <FileTextOutlined style={{ marginRight: 8 }} />
                      <Text>故事文件: </Text>
                      <Text code>{result.story_path}</Text>
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(result.story_path!, '路径')}
                      />
                    </div>
                  )}
                  {result.audio_path && (
                    <div>
                      <AudioOutlined style={{ marginRight: 8 }} />
                      <Text>音频文件: </Text>
                      <Text code>{result.audio_path}</Text>
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(result.audio_path!, '路径')}
                      />
                    </div>
                  )}
                  {result.draft_path && (
                    <div>
                      <FolderOutlined style={{ marginRight: 8 }} />
                      <Text>草稿目录: </Text>
                      <Text code>{result.draft_path}</Text>
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(result.draft_path!, '路径')}
                      />
                    </div>
                  )}
                  {result.video_path && (
                    <div>
                      <VideoCameraOutlined style={{ marginRight: 8 }} />
                      <Text>视频文件: </Text>
                      <Text code>{result.video_path}</Text>
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(result.video_path!, '路径')}
                      />
                    </div>
                  )}
                </Space>
              </Card>

              {/* 错误信息 */}
              {result.error && (
                <Alert
                  message="执行错误"
                  description={result.error}
                  type="error"
                  showIcon
                />
              )}
            </Space>
          ) : task.status === 'completed' ? (
            <Empty description="暂无结果数据" />
          ) : (
            <Alert
              message="任务未完成"
              description="任务完成后可查看详细结果"
              type="info"
              showIcon
            />
          )}
        </TabPane>

        <TabPane tab="YouTube元数据" key="metadata">
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" />
            </div>
          ) : result?.youtube_metadata ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* 标题 */}
              <Card title={<><YoutubeOutlined /> 标题</>} size="small">
                <Paragraph
                  copyable={{ text: result.youtube_metadata.title }}
                  style={{ marginBottom: 0 }}
                >
                  {result.youtube_metadata.title}
                </Paragraph>
              </Card>

              {/* 描述 */}
              <Card title="描述" size="small">
                <Paragraph
                  copyable={{ text: result.youtube_metadata.description }}
                  style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
                >
                  {result.youtube_metadata.description}
                </Paragraph>
              </Card>

              {/* 标签 */}
              <Card title={<><TagsOutlined /> 标签</>} size="small">
                <Space wrap>
                  {result.youtube_metadata.tags?.map((tag: string, index: number) => (
                    <Tag key={index} color="blue">
                      {tag}
                    </Tag>
                  ))}
                </Space>
                <div style={{ marginTop: 8 }}>
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(
                      result.youtube_metadata.tags.join(', '),
                      '标签'
                    )}
                  >
                    复制所有标签
                  </Button>
                </div>
              </Card>

              {/* 缩略图建议 */}
              {result.youtube_metadata.thumbnail_suggestions && (
                <Card title={<><PictureOutlined /> 缩略图建议</>} size="small">
                  <Space direction="vertical">
                    {result.youtube_metadata.thumbnail_suggestions.map((suggestion: any, index: number) => (
                      <div key={index}>
                        <Text strong>{suggestion.style}: </Text>
                        <Text>{suggestion.description}</Text>
                      </div>
                    ))}
                  </Space>
                </Card>
              )}
            </Space>
          ) : task.status === 'completed' ? (
            <Empty description="暂无YouTube元数据" />
          ) : (
            <Alert
              message="任务未完成"
              description="任务完成后可查看YouTube元数据"
              type="info"
              showIcon
            />
          )}
        </TabPane>
      </Tabs>
    </Drawer>
  );
};

export default TaskDetailDrawer;