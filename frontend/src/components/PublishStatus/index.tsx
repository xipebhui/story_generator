import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Progress,
  Tooltip,
  message,
  Empty,
  Avatar,
  Typography,
  Popconfirm
} from 'antd';
import {
  CloudUploadOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  YoutubeOutlined,
  LinkOutlined,
  UserOutlined,
  CalendarOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  RedoOutlined
} from '@ant-design/icons';
import { PublishTask } from '../../types/account';
import { accountService } from '../../services/account';
import { backendAccountService } from '../../services/backend';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Text } = Typography;

interface PublishStatusProps {
  taskId?: string;
  visible?: boolean;
}

const PublishStatus: React.FC<PublishStatusProps> = ({ 
  taskId,
  visible = true 
}) => {
  const [publishTasks, setPublishTasks] = useState<PublishTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [retryLoading, setRetryLoading] = useState<{ [key: string]: boolean }>({});
  const [deleteLoading, setDeleteLoading] = useState<{ [key: string]: boolean }>({});

  // 加载发布任务
  const loadPublishTasks = async () => {
    setLoading(true);
    try {
      // 从后端获取真实的发布任务
      const backendTasks = await backendAccountService.getPublishTasks(taskId);
      console.log('后端发布任务数据:', backendTasks);
      
      // 直接使用后端返回的数据格式
      const formattedTasks = backendTasks.map((task: any) => ({
        // 主要标识
        id: task.publish_id,
        publish_id: task.publish_id,
        task_id: task.task_id,
        
        // 账号信息
        account_id: task.account_id,
        account_name: task.account_name,
        youtube_channel_name: task.youtube_channel_name,
        
        // 视频信息
        title: task.video_title,
        video_title: task.video_title,
        privacy_status: task.privacy_status,
        
        // 状态和结果
        status: task.status,
        youtube_url: task.youtube_video_url,
        youtube_video_url: task.youtube_video_url,
        error_message: task.error_message,
        
        // 时间信息
        created_at: task.created_at,
        upload_completed_at: task.upload_completed_at,
        publish_time: task.created_at, // 用创建时间作为发布时间显示
        
        // 兼容旧字段
        published_at: task.upload_completed_at
      }));
      
      setPublishTasks(formattedTasks);
    } catch (error) {
      console.error('加载发布任务失败:', error);
      message.error('加载发布任务失败');
      setPublishTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      loadPublishTasks();
      // 移除自动刷新，改为手动刷新
    }
  }, [taskId, visible]);

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待发布' },
      uploading: { color: 'processing', icon: <SyncOutlined spin />, text: '上传中' },
      publishing: { color: 'processing', icon: <SyncOutlined spin />, text: '发布中' },
      published: { color: 'success', icon: <CheckCircleOutlined />, text: '已发布' },
      success: { color: 'success', icon: <CheckCircleOutlined />, text: '发布成功' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: '发布失败' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || 
                   { color: 'default', icon: <ClockCircleOutlined />, text: status || '未知' };
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  // 处理取消发布（用于pending和运行中的任务）
  const handleCancel = async (publishId: string) => {
    try {
      // 对于运行中的任务，使用backendAccountService的取消方法
      await backendAccountService.cancelPublishTask(publishId);
      message.success('已取消发布任务');
      loadPublishTasks();
    } catch (error) {
      message.error('取消失败');
    }
  };

  // 处理重试发布
  const handleRetry = async (publishId: string) => {
    setRetryLoading({ ...retryLoading, [publishId]: true });
    try {
      await backendAccountService.retryPublishTask(publishId);
      message.success('重试任务已启动');
      loadPublishTasks();
    } catch (error: any) {
      message.error(error.message || '重试失败');
    } finally {
      setRetryLoading({ ...retryLoading, [publishId]: false });
    }
  };

  // 处理删除发布记录
  const handleDelete = async (publishId: string) => {
    setDeleteLoading({ ...deleteLoading, [publishId]: true });
    try {
      await backendAccountService.deletePublishTask(publishId);
      message.success('删除成功');
      loadPublishTasks();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    } finally {
      setDeleteLoading({ ...deleteLoading, [publishId]: false });
    }
  };

  // 表格列配置
  const columns: ColumnsType<any> = [
    {
      title: '发布ID',
      dataIndex: 'publish_id',
      key: 'publish_id',
      width: 150,
      render: (text) => {
        if (!text) return '-';
        const shortId = text.split('_').slice(-1)[0]; // 只显示最后一部分
        return (
          <Tooltip title={text}>
            <span style={{ 
              fontFamily: 'monospace',
              fontSize: 12,
              color: '#5e72e4'
            }}>
              ...{shortId}
            </span>
          </Tooltip>
        );
      }
    },
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 180,
      render: (text) => {
        if (!text) return '-';
        const displayText = text.length > 25 ? text.substring(0, 25) + '...' : text;
        return (
          <Tooltip title={text}>
            <span style={{ 
              fontFamily: 'monospace',
              fontSize: 11
            }}>
              {displayText}
            </span>
          </Tooltip>
        );
      }
    },
    {
      title: 'YouTube账号',
      key: 'youtube_account',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
            <Text strong style={{ fontSize: 13 }}>
              {record.account_name || '未知账号'}
            </Text>
          </Space>
          {record.youtube_channel_name && (
            <Text type="secondary" style={{ fontSize: 11, marginLeft: 28 }}>
              @{record.youtube_channel_name}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: '视频标题',
      dataIndex: 'video_title',
      key: 'video_title',
      ellipsis: true,
      render: (text) => {
        if (!text) return '-';
        return (
          <Tooltip title={text}>
            <span>{text}</span>
          </Tooltip>
        );
      }
    },
    {
      title: '隐私设置',
      dataIndex: 'privacy_status',
      key: 'privacy_status',
      width: 100,
      render: (privacy) => {
        const privacyConfig = {
          public: { color: 'green', text: '公开' },
          private: { color: 'red', text: '私密' },
          unlisted: { color: 'orange', text: '不公开' }
        };
        const config = privacyConfig[privacy as keyof typeof privacyConfig] || 
                       { color: 'default', text: privacy || '-' };
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => status ? getStatusTag(status) : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time) => {
        if (!time) return '-';
        return dayjs(time).format('MM-DD HH:mm');
      }
    },
    {
      title: '完成时间',
      dataIndex: 'upload_completed_at',
      key: 'upload_completed_at',
      width: 150,
      render: (time) => {
        if (!time) return '-';
        return (
          <Tooltip title={dayjs(time).format('YYYY-MM-DD HH:mm:ss')}>
            <span>{dayjs(time).format('MM-DD HH:mm')}</span>
          </Tooltip>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          {(record.status === 'success' || record.status === 'published') && record.youtube_video_url && (
            <Tooltip title={`访问视频: ${record.youtube_video_url}`}>
              <Button
                type="primary"
                size="small"
                icon={<YoutubeOutlined />}
                href={record.youtube_video_url}
                target="_blank"
                style={{ fontSize: 12 }}
              >
                查看
              </Button>
            </Tooltip>
          )}
          {record.status === 'pending' && (
            <Button
              size="small"
              danger
              onClick={() => handleCancel(record.publish_id)}
              style={{ fontSize: 12 }}
            >
              取消
            </Button>
          )}
          {record.status === 'failed' && (
            <>
              <Button
                size="small"
                icon={<RedoOutlined />}
                onClick={() => handleRetry(record.publish_id)}
                loading={retryLoading[record.publish_id]}
                style={{ fontSize: 12 }}
              >
                重试
              </Button>
              {record.error_message && (
                <Tooltip title={`错误信息: ${record.error_message}`}>
                  <Button 
                    size="small" 
                    danger
                    icon={<ExclamationCircleOutlined />}
                    style={{ fontSize: 12 }}
                  >
                    错误
                  </Button>
                </Tooltip>
              )}
            </>
          )}
          {(record.status === 'uploading' || record.status === 'publishing') && (
            <>
              <Button
                size="small"
                danger
                onClick={() => handleCancel(record.publish_id)}
                style={{ fontSize: 12 }}
              >
                取消
              </Button>
              <Tag color="processing" icon={<SyncOutlined spin />}>
                处理中
              </Tag>
            </>
          )}
          {record.status !== 'uploading' && record.status !== 'publishing' && (
            <Popconfirm
              title="确认删除"
              description="确定要删除这条发布记录吗？"
              onConfirm={() => handleDelete(record.publish_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleteLoading[record.publish_id]}
                style={{ fontSize: 12 }}
              >
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  if (!visible) return null;

  return (
    <Card
      title={
        <Space>
          <CloudUploadOutlined />
          发布状态
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={loadPublishTasks}
          loading={loading}
        >
          刷新
        </Button>
      }
    >
      {publishTasks.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无发布任务"
        />
      ) : (
        <Table
          columns={columns}
          dataSource={publishTasks}
          rowKey="publish_id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条发布记录`
          }}
        />
      )}
    </Card>
  );
};

export default PublishStatus;