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
  Empty,
  Badge,
  Upload,
  Popconfirm
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
  UploadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { Task, TaskResult, PublishedAccount } from '../../types/task';
import { pipelineService } from '../../services/pipeline';
import { backendAccountService } from '../../services/backend';
import PublishStatusBadge from '../PublishStatusBadge';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';

dayjs.extend(duration);

const { Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface TaskDetailDrawerProps {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onPublish?: (task: Task) => void;
  onTaskRefresh?: () => void;  // 添加刷新回调
}

const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  visible,
  task,
  onClose,
  onPublish,
  onTaskRefresh
}) => {
  const [result, setResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showChineseTitles, setShowChineseTitles] = useState(false);
  const [showChineseDesc, setShowChineseDesc] = useState(false);
  const [errorExpanded, setErrorExpanded] = useState(false);  // 控制错误信息展开/折叠
  const [retryLoading, setRetryLoading] = useState<{ [key: string]: boolean }>({});
  const [deleteLoading, setDeleteLoading] = useState<{ [key: string]: boolean }>({});
  const [cancelLoading, setCancelLoading] = useState<{ [key: string]: boolean }>({});

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

  // 重试发布任务
  const handleRetry = async (publishId: string) => {
    if (!publishId) {
      message.error('发布任务ID不存在');
      return;
    }
    
    setRetryLoading({ ...retryLoading, [publishId]: true });
    try {
      await backendAccountService.retryPublishTask(publishId);
      message.success('重试任务已启动');
      // 刷新任务数据
      if (onTaskRefresh) {
        onTaskRefresh();
      }
    } catch (error: any) {
      message.error(error.message || '重试失败');
    } finally {
      setRetryLoading({ ...retryLoading, [publishId]: false });
    }
  };

  // 取消运行中的发布任务
  const handleCancel = async (publishId: string) => {
    if (!publishId) {
      message.error('发布任务ID不存在');
      return;
    }
    
    setCancelLoading({ ...cancelLoading, [publishId]: true });
    try {
      await backendAccountService.cancelPublishTask(publishId);
      message.success('发布任务已取消');
      
      // 更新本地任务数据
      if (task && task.published_accounts) {
        const canceledAccount = task.published_accounts.find(
          account => account.publish_id === publishId
        );
        if (canceledAccount) {
          canceledAccount.status = 'cancelled';
          canceledAccount.error_message = '任务已取消';
        }
      }
      
      // 刷新任务数据
      if (onTaskRefresh) {
        onTaskRefresh();
      }
    } catch (error: any) {
      message.error(error.message || '取消失败');
    } finally {
      setCancelLoading({ ...cancelLoading, [publishId]: false });
    }
  };

  // 删除发布任务
  const handleDelete = async (publishId: string) => {
    if (!publishId) {
      message.error('发布任务ID不存在');
      return;
    }
    
    setDeleteLoading({ ...deleteLoading, [publishId]: true });
    try {
      await backendAccountService.deletePublishTask(publishId);
      message.success('发布任务已删除');
      
      // 更新本地任务数据，移除已删除的发布记录
      if (task && task.published_accounts) {
        task.published_accounts = task.published_accounts.filter(
          account => account.publish_id !== publishId
        );
        
        // 更新发布状态统计
        if (task.publish_status) {
          task.publish_status.total = Math.max(0, task.publish_status.total - 1);
          // 根据被删除账号的状态更新相应计数
          const deletedAccount = task.published_accounts.find(a => a.publish_id === publishId);
          if (deletedAccount) {
            if (deletedAccount.status === 'success') {
              task.publish_status.success = Math.max(0, task.publish_status.success - 1);
            } else if (deletedAccount.status === 'failed') {
              task.publish_status.failed = Math.max(0, task.publish_status.failed - 1);
            } else if (deletedAccount.status === 'pending') {
              task.publish_status.pending = Math.max(0, task.publish_status.pending - 1);
            }
          }
        }
      }
      
      // 刷新任务数据
      if (onTaskRefresh) {
        onTaskRefresh();
      }
    } catch (error: any) {
      message.error(error.message || '删除失败');
    } finally {
      setDeleteLoading({ ...deleteLoading, [publishId]: false });
    }
  };

  // 重试发布任务
  const handleRetryPublish = async (publishId: string, accountName: string) => {
    if (!publishId) {
      message.error('缺少发布ID，无法重试');
      return;
    }

    setRetryLoading(prev => ({ ...prev, [publishId]: true }));
    try {
      await backendAccountService.retryPublishTask(publishId);
      message.success(`重试发布任务成功: ${accountName}`);
      
      // 刷新任务数据
      if (onTaskRefresh) {
        onTaskRefresh();
      }
    } catch (error: any) {
      message.error(`重试发布失败: ${error.message || '未知错误'}`);
    } finally {
      setRetryLoading(prev => ({ ...prev, [publishId]: false }));
    }
  };

  // 删除发布任务
  const handleDeletePublish = async (publishId: string, accountName: string) => {
    if (!publishId) {
      message.error('缺少发布ID，无法删除');
      return;
    }

    setDeleteLoading(prev => ({ ...prev, [publishId]: true }));
    try {
      await backendAccountService.deletePublishTask(publishId);
      message.success(`删除发布记录成功: ${accountName}`);
      
      // 刷新任务数据
      if (onTaskRefresh) {
        onTaskRefresh();
      }
    } catch (error: any) {
      message.error(`删除发布记录失败: ${error.message || '未知错误'}`);
    } finally {
      setDeleteLoading(prev => ({ ...prev, [publishId]: false }));
    }
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

          {/* 错误信息展示 */}
          {task.error_message && (
            <>
              <Divider>错误信息</Divider>
              <Alert
                message="任务执行失败"
                description={
                  <div>
                    {(() => {
                      const errorMessage = task.error_message || '';
                      const isLongError = errorMessage.length > 200;
                      
                      if (!isLongError) {
                        return (
                          <Text style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                            {errorMessage}
                          </Text>
                        );
                      }
                      
                      // 长错误信息，支持折叠
                      return (
                        <div>
                          <Text style={{ 
                            whiteSpace: 'pre-wrap', 
                            fontFamily: 'monospace',
                            display: 'block'
                          }}>
                            {errorExpanded 
                              ? errorMessage 
                              : errorMessage.substring(0, 200) + '...'}
                          </Text>
                          <Button
                            type="link"
                            size="small"
                            onClick={() => setErrorExpanded(!errorExpanded)}
                            style={{ padding: '4px 0', marginTop: 8 }}
                          >
                            {errorExpanded ? '收起' : '查看更多'}
                          </Button>
                          {errorExpanded && (
                            <Button
                              type="link"
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => copyToClipboard(errorMessage, '错误信息')}
                              style={{ marginLeft: 16 }}
                            >
                              复制错误信息
                            </Button>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                }
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
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

        <TabPane tab="发布状态" key="publish">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {/* 发布状态统计 */}
            <Card title="发布概览" size="small">
              <div style={{ marginBottom: 16 }}>
                <PublishStatusBadge
                  publishSummary={task.publish_summary}
                  publishStatus={task.publish_status}
                  publishedAccounts={task.published_accounts}
                  showDetail={false}
                />
              </div>
              
              {task.publish_status && (
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="总计划发布">
                    <Badge count={task.publish_status.total} showZero style={{ backgroundColor: '#1890ff' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="发布成功">
                    <Badge count={task.publish_status.success} showZero style={{ backgroundColor: '#52c41a' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="待发布">
                    <Badge count={task.publish_status.pending} showZero style={{ backgroundColor: '#faad14' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="上传中">
                    <Badge count={task.publish_status.uploading} showZero style={{ backgroundColor: '#1890ff' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="发布失败">
                    <Badge count={task.publish_status.failed} showZero style={{ backgroundColor: '#ff4d4f' }} />
                  </Descriptions.Item>
                </Descriptions>
              )}
            </Card>

            {/* 发布账号详情 */}
            <Card title="发布账号详情" size="small">
              {task.published_accounts && task.published_accounts.length > 0 ? (
                <Timeline>
                  {task.published_accounts.map((account: PublishedAccount, index) => {
                    const statusConfig = {
                      success: {
                        color: 'green',
                        icon: <CheckCircleOutlined />,
                        text: '发布成功'
                      },
                      pending: {
                        color: 'orange',
                        icon: <ClockCircleOutlined />,
                        text: '待发布'
                      },
                      uploading: {
                        color: 'blue',
                        icon: <SyncOutlined spin />,
                        text: '上传中'
                      },
                      failed: {
                        color: 'red',
                        icon: <CloseCircleOutlined />,
                        text: '发布失败'
                      }
                    };

                    const config = statusConfig[account.status as keyof typeof statusConfig] || statusConfig.pending;

                    return (
                      <Timeline.Item
                        key={index}
                        color={config.color}
                        dot={config.icon}
                      >
                        <Space direction="vertical" size={4}>
                          <Space>
                            <Text strong>{account.account_name}</Text>
                            <Tag color={config.color === 'orange' ? 'warning' : config.color}>
                              {config.text}
                            </Tag>
                            
                            {/* 取消、重试和删除按钮 */}
                            <Space size={4}>
                              {/* 取消按钮 - 运行中和待发布的任务可以取消 */}
                              {(account.status === 'uploading' || account.status === 'publishing' || account.status === 'pending') && account.publish_id && (
                                <Tooltip title="取消发布">
                                  <Button
                                    type="text"
                                    size="small"
                                    icon={<CloseOutlined />}
                                    loading={cancelLoading[account.publish_id]}
                                    onClick={() => handleCancel(account.publish_id!)}
                                    style={{ color: '#ff4d4f' }}
                                  />
                                </Tooltip>
                              )}
                              
                              {/* 重试按钮 - 仅对失败/取消的任务显示 */}
                              {(account.status === 'failed' || account.status === 'cancelled') && account.publish_id && (
                                <Tooltip title="重试发布">
                                  <Button
                                    type="text"
                                    size="small"
                                    icon={<ReloadOutlined />}
                                    loading={retryLoading[account.publish_id]}
                                    onClick={() => handleRetry(account.publish_id!)}
                                    style={{ color: '#52c41a' }}
                                  />
                                </Tooltip>
                              )}
                              
                              {/* 删除按钮 - 所有发布记录都可以删除 */}
                              {account.publish_id && (
                                <Popconfirm
                                  title="删除发布记录"
                                  description={`确定要删除账号 "${account.account_name}" 的发布记录吗？`}
                                  onConfirm={() => handleDelete(account.publish_id!)}
                                  okText="删除"
                                  cancelText="取消"
                                  okType="danger"
                                >
                                  <Tooltip title="删除发布记录">
                                    <Button
                                      type="text"
                                      size="small"
                                      icon={<DeleteOutlined />}
                                      loading={deleteLoading[account.publish_id]}
                                      style={{ color: '#ff4d4f' }}
                                    />
                                  </Tooltip>
                                </Popconfirm>
                              )}
                            </Space>
                          </Space>
                          
                          {account.youtube_video_url && (
                            <Space>
                              <YoutubeOutlined style={{ color: '#ff0000' }} />
                              <a href={account.youtube_video_url} target="_blank" rel="noopener noreferrer">
                                {account.youtube_video_url}
                              </a>
                              <Button
                                type="text"
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => copyToClipboard(account.youtube_video_url!, 'YouTube链接')}
                              />
                            </Space>
                          )}
                          
                          {account.published_at && (
                            <Text type="secondary">
                              发布时间: {dayjs(account.published_at).format('YYYY-MM-DD HH:mm:ss')}
                            </Text>
                          )}
                          
                          {account.error_message && (
                            <Alert
                              message="错误信息"
                              description={account.error_message}
                              type="error"
                              showIcon
                              style={{ marginTop: 8 }}
                            />
                          )}
                        </Space>
                      </Timeline.Item>
                    );
                  })}
                </Timeline>
              ) : (
                <Empty 
                  description={
                    <Space direction="vertical">
                      <Text>暂未发布到任何账号</Text>
                      {task.status === 'completed' && onPublish && (
                        <Button
                          type="primary"
                          icon={<CloudUploadOutlined />}
                          onClick={() => onPublish(task)}
                        >
                          立即发布
                        </Button>
                      )}
                    </Space>
                  }
                />
              )}
            </Card>

            {/* 发布提示 */}
            {task.status === 'completed' && (!task.publish_status || task.publish_status.total === 0) && (
              <Alert
                message="提示"
                description="任务已完成，您可以点击上方的'发布到YouTube'按钮将视频发布到指定账号。"
                type="info"
                showIcon
              />
            )}

            {task.publish_status && task.publish_status.failed > 0 && (
              <Alert
                message="发布失败提示"
                description={`有 ${task.publish_status.failed} 个账号发布失败，请检查失败原因并重试。失败的发布任务也会被统计在发布状态中。`}
                type="warning"
                showIcon
              />
            )}
          </Space>
        </TabPane>
      </Tabs>
    </Drawer>
  );
};

export default TaskDetailDrawer;