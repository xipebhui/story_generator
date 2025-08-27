import React, { useState, useEffect, useRef } from 'react';
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
  Empty,
  Badge,
  Upload
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
  PictureOutlined,
  CloudUploadOutlined,
  GlobalOutlined,
  TranslationOutlined,
  UploadOutlined
} from '@ant-design/icons';
import { Task, TaskResult } from '../../types/task';
import { pipelineService } from '../../services/pipeline';
import { backendAccountService } from '../../services/backend';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';

dayjs.extend(duration);

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface TaskDetailDrawerProps {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onPublish?: (task: Task) => void;
}

const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  visible,
  task,
  onClose,
  onPublish
}) => {
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showChineseTitles, setShowChineseTitles] = useState(false);
  const [showChineseDesc, setShowChineseDesc] = useState(false);

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
        return <SyncOutlined style={{ color: '#1890ff' }} />;
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
    
    // 优先使用后端返回的 total_duration 或 duration
    if (task.total_duration || task.duration) {
      const seconds = Math.round(task.total_duration || task.duration || 0);
      const duration = dayjs.duration(seconds, 'seconds');
      
      if (duration.hours() > 0) {
        return `${duration.hours()}小时${duration.minutes()}分钟${duration.seconds()}秒`;
      } else if (duration.minutes() > 0) {
        return `${duration.minutes()}分钟${duration.seconds()}秒`;
      } else {
        return `${seconds}秒`;
      }
    }
    
    // 如果没有 duration 字段，尝试通过时间差计算
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            {getStatusIcon(task.status)}
            <span>任务详情</span>
            <Tag color={getStatusColor(task.status)}>{task.status}</Tag>
          </Space>
          {task.status === 'completed' && onPublish && (
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => onPublish(task)}
              style={{ 
                background: 'linear-gradient(87deg, #2dce89 0, #2dcecc 100%)',
                border: 'none'
              }}
            >
              发布到YouTube
            </Button>
          )}
        </div>
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

          {/* 字幕上传 - 移到基本信息页，无论任务成功或失败都可以上传 */}
          <Divider>字幕管理</Divider>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="字幕上传"
                description="您可以上传.txt格式的字幕文件，系统将自动同步到视频中。无论任务状态如何，都可以上传字幕。"
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
              />
              <Upload
                accept=".txt"
                showUploadList={false}
                beforeUpload={async (file) => {
                  // 检查文件类型
                  if (!file.name.endsWith('.txt')) {
                    message.error('请上传.txt格式的字幕文件');
                    return false;
                  }
                  
                  // 检查文件大小（限制5MB）
                  if (file.size > 5 * 1024 * 1024) {
                    message.error('字幕文件不能超过5MB');
                    return false;
                  }
                  
                  try {
                    message.loading('正在上传字幕...');
                    const response = await backendAccountService.uploadSubtitle(task.task_id, file);
                    message.success(`字幕上传成功！文件大小: ${(response.file_size / 1024).toFixed(2)}KB`);
                    
                    // 可选：刷新任务结果
                    loadTaskResult();
                  } catch (error: any) {
                    message.error(error.message || '字幕上传失败');
                  }
                  
                  return false; // 阻止默认上传
                }}
              >
                <Button icon={<UploadOutlined />} type="primary">
                  上传字幕文件
                </Button>
              </Upload>
              <Text type="secondary">
                支持格式：.txt | 最大大小：5MB | 任务ID：{task.task_id}
              </Text>
            </Space>
          </Card>

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
                      status === '运行中' ? <SyncOutlined /> : undefined
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
              {/* 视频预览 */}
              {result.preview_url && (
                <Card title="视频预览" size="small">
                  <div style={{ textAlign: 'center', marginBottom: 16 }}>
                    <video 
                      controls 
                      style={{ width: '100%', maxWidth: '100%', borderRadius: 8 }}
                      src={result.preview_url}
                    >
                      您的浏览器不支持视频播放
                    </video>
                  </div>
                  <Space>
                    <Text type="secondary">预览链接: </Text>
                    <Text code>{result.preview_url}</Text>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => copyToClipboard(result.preview_url!, '预览链接')}
                    />
                  </Space>
                </Card>
              )}

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
              <Card 
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span><YoutubeOutlined /> 标题</span>
                    {(result.youtube_metadata as any).titles?.chinese && (
                      <Button 
                        size="small" 
                        onClick={() => setShowChineseTitles(!showChineseTitles)}
                      >
                        {showChineseTitles ? '显示英文' : '翻译中文'}
                      </Button>
                    )}
                  </div>
                } 
                size="small"
              >
                {(() => {
                  const metadata = result.youtube_metadata as any;
                  if (!metadata || !metadata.titles) {
                    return <Empty description="暂无标题数据" />;
                  }
                  
                  const titles = showChineseTitles ? metadata.titles.chinese : metadata.titles.english;
                  return (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {titles?.map((title: string, index: number) => (
                        <div key={index} style={{ marginBottom: 8 }}>
                          <Badge count={index + 1} style={{ backgroundColor: '#52c41a' }}>
                            <Paragraph
                              copyable={{ text: title }}
                              style={{ marginBottom: 0, marginLeft: 8 }}
                            >
                              {title}
                            </Paragraph>
                          </Badge>
                        </div>
                      ))}
                    </Space>
                  );
                })()}
              </Card>

              {/* 描述 */}
              <Card 
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>描述</span>
                    {(result.youtube_metadata as any).descriptions?.chinese && (
                      <Button 
                        size="small" 
                        onClick={() => setShowChineseDesc(!showChineseDesc)}
                      >
                        {showChineseDesc ? '显示英文' : '翻译中文'}
                      </Button>
                    )}
                  </div>
                } 
                size="small"
              >
                {(() => {
                  const metadata = result.youtube_metadata as any;
                  if (!metadata || !metadata.descriptions) {
                    return <Empty description="暂无描述数据" />;
                  }
                  
                  const description = showChineseDesc ? metadata.descriptions.chinese : metadata.descriptions.english;
                  return (
                    <Paragraph
                      copyable={{ text: description }}
                      style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
                    >
                      {description}
                    </Paragraph>
                  );
                })()}
              </Card>

              {/* 标签 - 只显示英文标签 */}
              <Card title={<><TagsOutlined /> 标签</>} size="small">
                {(() => {
                  const metadata = result.youtube_metadata as any;
                  if (!metadata || !metadata.tags || !metadata.tags.english) {
                    return <Empty description="暂无标签数据" />;
                  }
                  
                  const englishTags = metadata.tags.english || [];
                  
                  return (
                    <>
                      <Space wrap>
                        {englishTags.map((tag: string, index: number) => (
                          <Tag key={`en-${index}`} color="blue">
                            {tag}
                          </Tag>
                        ))}
                      </Space>
                      {englishTags.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                          <Button
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard(
                              englishTags.join(', '),
                              '标签'
                            )}
                          >
                            复制所有标签
                          </Button>
                        </div>
                      )}
                    </>
                  );
                })()}
              </Card>

              {/* 缩略图信息 */}
              {(() => {
                const metadata = result.youtube_metadata as any;
                const thumbnail = metadata.thumbnail;
                
                if (!thumbnail) return null;
                
                // 新格式的缩略图信息
                if (thumbnail.visual_focus || thumbnail.text_overlay) {
                  return (
                    <Card title={<><PictureOutlined /> 缩略图设计</>} size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {thumbnail.visual_focus && (
                          <div>
                            <Text strong>视觉焦点: </Text>
                            <Text style={{ display: 'block', marginTop: 8 }}>{thumbnail.visual_focus}</Text>
                          </div>
                        )}
                        
                        {thumbnail.text_overlay && (
                          <div style={{ marginTop: 16 }}>
                            <Text strong>文字叠加: </Text>
                            <div style={{ marginTop: 8 }}>
                              <Tag color="blue">英文: {thumbnail.text_overlay.english}</Tag>
                              <Tag color="red">中文: {thumbnail.text_overlay.chinese}</Tag>
                            </div>
                          </div>
                        )}
                        
                        {thumbnail.color_scheme && (
                          <div style={{ marginTop: 16 }}>
                            <Text strong>配色方案: </Text>
                            <Text style={{ display: 'block', marginTop: 8 }}>{thumbnail.color_scheme}</Text>
                          </div>
                        )}
                        
                        {thumbnail.emotion && (
                          <div style={{ marginTop: 16 }}>
                            <Text strong>情感表达: </Text>
                            <Text style={{ display: 'block', marginTop: 8 }}>{thumbnail.emotion}</Text>
                          </div>
                        )}
                      </Space>
                    </Card>
                  );
                }
                
                
                return null;
              })()}
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