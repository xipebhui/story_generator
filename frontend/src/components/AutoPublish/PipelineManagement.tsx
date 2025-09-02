import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Input, Select, Tag, Modal, Form, message, Drawer, Descriptions, Badge, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { autoPublishService } from '../../services/autoPublish';
import PipelineFormModal from './PipelineFormModal';
import './PipelineManagement.less';

const { Search } = Input;
const { Option } = Select;

interface Pipeline {
  pipeline_id: string;
  pipeline_name: string;
  pipeline_type: string;
  pipeline_class: string;
  config_schema: any;
  supported_platforms: string[];
  version: string;
  status: 'active' | 'inactive' | 'testing';
  created_at: string;
  updated_at: string;
}

const PipelineManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [filteredPipelines, setFilteredPipelines] = useState<Pipeline[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [editingPipeline, setEditingPipeline] = useState<Pipeline | null>(null);

  // 加载Pipeline列表
  const loadPipelines = async () => {
    try {
      setLoading(true);
      const response = await autoPublishService.listPipelines({
        pipeline_type: filterType || undefined,
        status: filterStatus || undefined
      });
      
      const pipelineList = response.pipelines || [];
      setPipelines(pipelineList);
      setFilteredPipelines(pipelineList);
    } catch (error) {
      console.error('Failed to load pipelines:', error);
      message.error('加载Pipeline列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadPipelines();
  }, [filterType, filterStatus]);

  // 搜索过滤
  useEffect(() => {
    const filtered = pipelines.filter(p => 
      p.pipeline_name.toLowerCase().includes(searchText.toLowerCase()) ||
      p.pipeline_id.toLowerCase().includes(searchText.toLowerCase())
    );
    setFilteredPipelines(filtered);
  }, [searchText, pipelines]);

  // 删除Pipeline
  const handleDelete = async (pipeline_id: string) => {
    try {
      await autoPublishService.deletePipeline(pipeline_id);
      message.success('删除成功');
      loadPipelines();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 更新Pipeline状态
  const handleStatusChange = async (pipeline_id: string, status: string) => {
    try {
      await autoPublishService.updatePipeline(pipeline_id, { status });
      message.success('状态更新成功');
      loadPipelines();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '状态更新失败');
    }
  };

  // 查看详情
  const handleViewDetail = async (pipeline: Pipeline) => {
    setSelectedPipeline(pipeline);
    setDetailDrawerVisible(true);
  };

  // 创建Pipeline
  const handleCreate = () => {
    setEditingPipeline(null);
    setFormModalVisible(true);
  };

  // 编辑Pipeline
  const handleEdit = (pipeline: Pipeline) => {
    setEditingPipeline(pipeline);
    setFormModalVisible(true);
  };

  // 保存Pipeline
  const handleSave = async (values: any) => {
    try {
      if (editingPipeline) {
        await autoPublishService.updatePipeline(editingPipeline.pipeline_id, values);
        message.success('更新成功');
      } else {
        await autoPublishService.registerPipeline(values);
        message.success('创建成功');
      }
      setFormModalVisible(false);
      loadPipelines();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      'active': { color: 'green', text: '启用' },
      'inactive': { color: 'default', text: '停用' },
      'testing': { color: 'blue', text: '测试中' }
    };
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 获取类型标签
  const getTypeTag = (type: string) => {
    const typeConfig: Record<string, { color: string; text: string }> = {
      'content_generation': { color: 'blue', text: '内容生成' },
      'metadata': { color: 'green', text: '元数据' },
      'processing': { color: 'orange', text: '后处理' }
    };
    const config = typeConfig[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 表格列定义
  const columns = [
    {
      title: 'Pipeline ID',
      dataIndex: 'pipeline_id',
      key: 'pipeline_id',
      width: 200,
      render: (text: string) => <span className="pipeline-id">{text}</span>
    },
    {
      title: '名称',
      dataIndex: 'pipeline_name',
      key: 'pipeline_name',
      render: (text: string, record: Pipeline) => (
        <a onClick={() => handleViewDetail(record)}>{text}</a>
      )
    },
    {
      title: '类型',
      dataIndex: 'pipeline_type',
      key: 'pipeline_type',
      width: 120,
      render: (type: string) => getTypeTag(type)
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '平台',
      dataIndex: 'supported_platforms',
      key: 'supported_platforms',
      width: 120,
      render: (platforms: string[]) => (
        <Space size={4}>
          {platforms?.map(p => (
            <Tag key={p} color="purple">{p}</Tag>
          ))}
        </Space>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString('zh-CN')
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_: any, record: Pipeline) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个Pipeline吗？"
            onConfirm={() => handleDelete(record.pipeline_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <div className="pipeline-management">
      <Card>
        {/* 顶部操作栏 */}
        <div className="toolbar">
          <Space>
            <Search
              placeholder="搜索Pipeline"
              style={{ width: 200 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={setSearchText}
            />
            <Select
              placeholder="筛选类型"
              style={{ width: 150 }}
              allowClear
              value={filterType}
              onChange={setFilterType}
            >
              <Option value="content_generation">内容生成</Option>
              <Option value="metadata">元数据</Option>
              <Option value="processing">后处理</Option>
            </Select>
            <Select
              placeholder="筛选状态"
              style={{ width: 120 }}
              allowClear
              value={filterStatus}
              onChange={setFilterStatus}
            >
              <Option value="active">启用</Option>
              <Option value="inactive">停用</Option>
              <Option value="testing">测试中</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadPipelines}>
              刷新
            </Button>
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建Pipeline
          </Button>
        </div>

        {/* 数据表格 */}
        <Table
          columns={columns}
          dataSource={filteredPipelines}
          rowKey="pipeline_id"
          loading={loading}
          pagination={{
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="Pipeline详情"
        placement="right"
        width={900}
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
      >
        {selectedPipeline && (
          <div className="pipeline-detail">
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="Pipeline ID" span={2}>
                {selectedPipeline.pipeline_id}
              </Descriptions.Item>
              <Descriptions.Item label="名称">
                {selectedPipeline.pipeline_name}
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                {getTypeTag(selectedPipeline.pipeline_type)}
              </Descriptions.Item>
              <Descriptions.Item label="Python类">
                <code>{selectedPipeline.pipeline_class}</code>
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                {selectedPipeline.version}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusTag(selectedPipeline.status)}
              </Descriptions.Item>
              <Descriptions.Item label="支持平台">
                {selectedPipeline.supported_platforms?.join(', ')}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedPipeline.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {new Date(selectedPipeline.updated_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>

            <Descriptions title="参数配置Schema" bordered style={{ marginTop: 24 }}>
              <Descriptions.Item label="Schema" span={2}>
                <pre className="schema-display">
                  {JSON.stringify(selectedPipeline.config_schema, null, 2)}
                </pre>
              </Descriptions.Item>
            </Descriptions>

            <div className="detail-actions">
              <Space>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => {
                    handleEdit(selectedPipeline);
                    setDetailDrawerVisible(false);
                  }}
                >
                  编辑
                </Button>
                <Select
                  value={selectedPipeline.status}
                  style={{ width: 120 }}
                  onChange={(value) => handleStatusChange(selectedPipeline.pipeline_id, value)}
                >
                  <Option value="active">启用</Option>
                  <Option value="inactive">停用</Option>
                  <Option value="testing">测试中</Option>
                </Select>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* 创建/编辑弹窗 */}
      <PipelineFormModal
        visible={formModalVisible}
        pipeline={editingPipeline}
        onCancel={() => setFormModalVisible(false)}
        onOk={handleSave}
      />
    </div>
  );
};

export default PipelineManagement;