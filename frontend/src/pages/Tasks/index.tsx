import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Card,
  Input,
  Select,
  Row,
  Col,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EyeOutlined,
  MonitorOutlined,
  DeleteOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { ColumnsType } from 'antd/es/table';
import pipelineService from '@/services/pipeline';
import { TaskListItem, TaskListResponse } from '@/types/task';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime, formatRelativeTime } from '@/utils/format';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

const TaskList: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // 获取任务列表
  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response: TaskListResponse = await pipelineService.getTaskList();
      setTasks(response.tasks);
      filterTasks(response.tasks, searchText, statusFilter);
    } catch (error) {
      console.error('获取任务列表失败:', error);
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 过滤任务
  const filterTasks = (taskList: TaskListItem[], search: string, status: string) => {
    let filtered = [...taskList];
    
    // 状态过滤
    if (status !== 'all') {
      filtered = filtered.filter(task => task.status === status);
    }
    
    // 搜索过滤
    if (search) {
      filtered = filtered.filter(task => 
        task.task_id.toLowerCase().includes(search.toLowerCase())
      );
    }
    
    // 按创建时间倒序
    filtered.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    
    setFilteredTasks(filtered);
  };

  // 搜索处理
  const handleSearch = (value: string) => {
    setSearchText(value);
    filterTasks(tasks, value, statusFilter);
  };

  // 状态过滤处理
  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    filterTasks(tasks, searchText, value);
  };

  // 清空任务（测试用）
  const handleClearTasks = async () => {
    try {
      await pipelineService.clearTasks();
      message.success('已清空所有任务');
      fetchTasks();
    } catch (error) {
      message.error('清空任务失败');
    }
  };

  // 删除任务（预留）
  const handleDeleteTask = async (taskId: string) => {
    const result = await pipelineService.deleteTask(taskId);
    if (!result.success) {
      message.warning(result.message);
    }
  };

  // 重试任务（预留）
  const handleRetryTask = async (taskId: string) => {
    const result = await pipelineService.retryTask(taskId);
    if (!result.success) {
      message.warning(result.message);
    }
  };

  useEffect(() => {
    fetchTasks();
    
    // 每10秒刷新一次
    const interval = setInterval(fetchTasks, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const columns: ColumnsType<TaskListItem> = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 300,
      ellipsis: true,
      render: (text: string) => (
        <Typography.Text copyable ellipsis style={{ width: 280 }}>
          {text}
        </Typography.Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => <StatusBadge status={status} />,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => (
        <span title={formatDateTime(time)}>
          {formatRelativeTime(time)}
        </span>
      ),
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (time?: string) => 
        time ? (
          <span title={formatDateTime(time)}>
            {formatRelativeTime(time)}
          </span>
        ) : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space>
          {record.status === 'running' ? (
            <Button
              type="link"
              icon={<MonitorOutlined />}
              onClick={() => navigate(`/monitor/${record.task_id}`)}
            >
              监控
            </Button>
          ) : (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/task/${record.task_id}`)}
            >
              详情
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="link"
              danger
              onClick={() => handleRetryTask(record.task_id)}
            >
              重试
            </Button>
          )}
          <Popconfirm
            title="确定删除该任务吗？"
            onConfirm={() => handleDeleteTask(record.task_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>任务列表</Title>
        </Col>
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/create')}
            >
              新建任务
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchTasks}>
              刷新
            </Button>
            <Popconfirm
              title="确定清空所有任务吗？"
              onConfirm={handleClearTasks}
              okText="确定"
              cancelText="取消"
            >
              <Button danger>清空任务</Button>
            </Popconfirm>
          </Space>
        </Col>
      </Row>

      <Card>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Search
              placeholder="搜索任务ID"
              onSearch={handleSearch}
              enterButton={<SearchOutlined />}
              allowClear
            />
          </Col>
          <Col span={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="状态筛选"
              value={statusFilter}
              onChange={handleStatusFilter}
            >
              <Option value="all">全部状态</Option>
              <Option value="pending">待处理</Option>
              <Option value="running">运行中</Option>
              <Option value="completed">已完成</Option>
              <Option value="failed">失败</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredTasks}
          rowKey="task_id"
          loading={loading}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个任务`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  );
};

export default TaskList;