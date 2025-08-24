import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Button,
  Space,
  Typography,
  Tabs,
  Alert,
  Spin,
  Result,
  Tag,
  message,
  Row,
  Col,
} from 'antd';
import {
  DownloadOutlined,
  PlayCircleOutlined,
  RocketOutlined,
  CopyOutlined,
  FileTextOutlined,
  AudioOutlined,
  VideoCameraOutlined,
  FolderOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import pipelineService from '@/services/pipeline';
import { TaskResultResponse } from '@/types/task';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime } from '@/utils/format';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const TaskDetail: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  
  const [result, setResult] = useState<TaskResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取任务结果
  const fetchResult = async () => {
    if (!taskId) return;
    
    try {
      setLoading(true);
      const resultData = await pipelineService.getTaskResult(taskId);
      setResult(resultData);
    } catch (err: any) {
      setError(err.message || '获取任务结果失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResult();
  }, [taskId]);

  // 复制文本
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  // 发布视频（预留）
  const handlePublish = () => {
    navigate(`/publish/${taskId}`);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 20 }}>
          <Text type="secondary">加载任务详情...</Text>
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
          <Button key="retry" type="primary" onClick={fetchResult}>
            重试
          </Button>,
          <Button key="back" onClick={() => navigate('/tasks')}>
            返回列表
          </Button>,
        ]}
      />
    );
  }

  if (!result) {
    return (
      <Result
        status="404"
        title="任务不存在"
        subTitle={`找不到任务ID: ${taskId}`}
        extra={
          <Button type="primary" onClick={() => navigate('/tasks')}>
            返回列表
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/tasks')}
            style={{ marginBottom: 16 }}
          >
            返回列表
          </Button>
          
          <Title level={2}>任务详情</Title>
        </div>

        <Card>
          <Descriptions title="基础信息" bordered column={2}>
            <Descriptions.Item label="任务ID">
              {taskId}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <StatusBadge status={result.status} />
            </Descriptions.Item>
            {result.error && (
              <Descriptions.Item label="错误信息" span={2}>
                <Text type="danger">{result.error}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>

        {result.status === 'completed' && (
          <>
            <Card title="生成文件">
              <Row gutter={[16, 16]}>
                {result.story_path && (
                  <Col span={12}>
                    <Card size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <FileTextOutlined style={{ fontSize: 24 }} />
                          <Text strong>故事文本</Text>
                        </Space>
                        <Text type="secondary" ellipsis>
                          {result.story_path}
                        </Text>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={() => handleCopy(result.story_path!)}
                        >
                          复制路径
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                )}
                
                {result.audio_path && (
                  <Col span={12}>
                    <Card size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <AudioOutlined style={{ fontSize: 24 }} />
                          <Text strong>音频文件</Text>
                        </Space>
                        <Text type="secondary" ellipsis>
                          {result.audio_path}
                        </Text>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={() => handleCopy(result.audio_path!)}
                        >
                          复制路径
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                )}
                
                {result.draft_path && (
                  <Col span={12}>
                    <Card size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <FolderOutlined style={{ fontSize: 24 }} />
                          <Text strong>剪映草稿</Text>
                        </Space>
                        <Text type="secondary" ellipsis>
                          {result.draft_path}
                        </Text>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={() => handleCopy(result.draft_path!)}
                        >
                          复制路径
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                )}
                
                {result.video_path && (
                  <Col span={12}>
                    <Card size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <VideoCameraOutlined style={{ fontSize: 24 }} />
                          <Text strong>视频文件</Text>
                        </Space>
                        <Text type="secondary" ellipsis>
                          {result.video_path}
                        </Text>
                        <Space>
                          <Button
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => handleCopy(result.video_path!)}
                          >
                            复制路径
                          </Button>
                          {result.preview_url && (
                            <Button
                              size="small"
                              type="primary"
                              icon={<PlayCircleOutlined />}
                              onClick={() => window.open(result.preview_url, '_blank')}
                            >
                              预览
                            </Button>
                          )}
                        </Space>
                      </Space>
                    </Card>
                  </Col>
                )}
              </Row>
            </Card>

            {result.youtube_metadata && (
              <Card title="YouTube元数据">
                <Tabs defaultActiveKey="1">
                  <TabPane tab="基本信息" key="1">
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <div>
                        <Title level={5}>标题</Title>
                        <Paragraph copyable>
                          {result.youtube_metadata.title}
                        </Paragraph>
                      </div>
                      
                      <div>
                        <Title level={5}>描述</Title>
                        <Paragraph
                          copyable
                          ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}
                        >
                          {result.youtube_metadata.description}
                        </Paragraph>
                      </div>
                      
                      <div>
                        <Title level={5}>标签</Title>
                        <Space wrap>
                          {result.youtube_metadata.tags.map((tag, index) => (
                            <Tag key={index} color="blue">
                              {tag}
                            </Tag>
                          ))}
                        </Space>
                      </div>
                      
                      {result.youtube_metadata.category && (
                        <div>
                          <Title level={5}>分类</Title>
                          <Text>{result.youtube_metadata.category}</Text>
                        </div>
                      )}
                    </Space>
                  </TabPane>
                  
                  {result.youtube_metadata.thumbnail && (
                    <TabPane tab="缩略图建议" key="2">
                      <Descriptions bordered column={1}>
                        <Descriptions.Item label="文字内容">
                          {result.youtube_metadata.thumbnail.text}
                        </Descriptions.Item>
                        <Descriptions.Item label="风格">
                          {result.youtube_metadata.thumbnail.style}
                        </Descriptions.Item>
                        <Descriptions.Item label="配色方案">
                          {result.youtube_metadata.thumbnail.color_scheme}
                        </Descriptions.Item>
                        <Descriptions.Item label="情绪表达">
                          {result.youtube_metadata.thumbnail.emotion}
                        </Descriptions.Item>
                      </Descriptions>
                    </TabPane>
                  )}
                </Tabs>
              </Card>
            )}

            <Space>
              <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={handlePublish}
                disabled={!result.video_path}
              >
                发布视频
              </Button>
              <Button size="large" onClick={() => navigate('/tasks')}>
                返回列表
              </Button>
            </Space>
          </>
        )}

        {result.status === 'failed' && (
          <Alert
            message="任务执行失败"
            description={result.error || '未知错误'}
            type="error"
            showIcon
          />
        )}
      </Space>
    </div>
  );
};

export default TaskDetail;