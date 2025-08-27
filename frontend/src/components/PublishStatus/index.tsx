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
  Avatar
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
  ReloadOutlined
} from '@ant-design/icons';
import { PublishTask } from '../../types/account';
import { accountService } from '../../services/account';
import { backendAccountService } from '../../services/backend';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

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

  // 加载发布任务
  const loadPublishTasks = async () => {
    setLoading(true);
    try {
      // 优先尝试从后端获取真实的发布任务
      try {
        const backendTasks = await backendAccountService.getPublishTasks(taskId);
        
        // 转换后端任务格式为前端格式
        const formattedTasks = backendTasks.map((task: any) => ({
          id: task.publish_id || task.id || `pub_${Date.now()}_${Math.random()}`,
          task_id: task.task_id,
          account_id: task.account_id || task.account_ids?.[0],
          account_name: task.account_name || task.account_id || '未知账号',
          title: task.video_title || task.title || '未命名视频',
          description: task.video_description || task.description,
          video_path: task.video_path,
          thumbnail_path: task.thumbnail_path,
          publish_time: task.publish_time || task.created_at,
          publish_interval: task.publish_interval,
          status: task.status || 'pending',
          created_at: task.created_at,
          published_at: task.published_at,
          youtube_url: task.youtube_url || task.results?.[0]?.youtube_url,
          error_message: task.error_message || task.error || task.results?.[0]?.error
        }));
        
        setPublishTasks(formattedTasks);
      } catch (backendError) {
        console.warn('无法从后端获取发布任务，尝试使用本地数据:', backendError);
        // 如果后端不可用，回退到本地模拟数据
        const tasks = await accountService.getPublishTasks(taskId);
        setPublishTasks(tasks);
      }
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
      // 每5秒刷新一次状态
      const interval = setInterval(loadPublishTasks, 5000);
      return () => clearInterval(interval);
    }
  }, [taskId, visible]);

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待发布' },
      publishing: { color: 'processing', icon: <SyncOutlined spin />, text: '发布中' },
      published: { color: 'success', icon: <CheckCircleOutlined />, text: '已发布' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: '发布失败' }
    };

    const config = statusConfig[status as keyof typeof statusConfig];
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  // 处理取消发布
  const handleCancel = async (id: string) => {
    try {
      await accountService.cancelPublishTask(id);
      message.success('已取消发布任务');
      loadPublishTasks();
    } catch (error) {
      message.error('取消失败');
    }
  };

  // 表格列配置
  const columns: ColumnsType<PublishTask> = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      render: (text) => (
        <Tooltip title={text}>
          <span style={{ 
            fontFamily: 'monospace',
            fontSize: 12,
            color: '#5e72e4'
          }}>
            {text.substring(0, 20)}...
          </span>
        </Tooltip>
      )
    },
    {
      title: '发布账号',
      dataIndex: 'account_name',
      key: 'account_name',
      width: 150,
      render: (text) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {text}
        </Space>
      )
    },
    {
      title: '视频标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      )
    },
    {
      title: '发布时间',
      key: 'publish_time',
      width: 180,
      render: (_, record) => {
        if (record.publish_time) {
          return (
            <Space>
              <CalendarOutlined />
              {dayjs(record.publish_time).format('YYYY-MM-DD HH:mm')}
            </Space>
          );
        }
        if (record.publish_interval) {
          return (
            <Space>
              <ClockCircleOutlined />
              间隔 {record.publish_interval} 分钟
            </Space>
          );
        }
        return '立即发布';
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => getStatusTag(status)
    },
    {
      title: '进度',
      key: 'progress',
      width: 150,
      render: (_, record) => {
        if (record.status === 'publishing') {
          return <Progress percent={50} size="small" status="active" />;
        }
        if (record.status === 'published') {
          return <Progress percent={100} size="small" status="success" />;
        }
        if (record.status === 'failed') {
          return <Progress percent={0} size="small" status="exception" />;
        }
        return <Progress percent={0} size="small" />;
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          {record.status === 'published' && record.youtube_url && (
            <Tooltip title="查看视频">
              <Button
                type="link"
                icon={<YoutubeOutlined />}
                href={record.youtube_url}
                target="_blank"
              >
                查看
              </Button>
            </Tooltip>
          )}
          {record.status === 'pending' && (
            <Button
              size="small"
              danger
              onClick={() => handleCancel(record.id)}
            >
              取消
            </Button>
          )}
          {record.status === 'failed' && (
            <Tooltip title={record.error_message}>
              <Button size="small" danger>
                查看错误
              </Button>
            </Tooltip>
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
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: false
          }}
        />
      )}
    </Card>
  );
};

export default PublishStatus;