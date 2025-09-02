import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Tag, 
  Input, 
  Select, 
  Row, 
  Col,
  message,
  Popconfirm,
  Switch,
  Tooltip,
  Badge,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { autoPublishService } from '../../services/autoPublish';
import ConfigFormModal from './ConfigFormModal';
import ConfigDetailDrawer from './ConfigDetailDrawer';
import moment from 'moment';

const { Search } = Input;
const { Option } = Select;

interface PublishConfig {
  config_id: string;
  config_name: string;
  group_id: string;
  pipeline_id: string;
  trigger_type: string;
  trigger_config: any;
  strategy_id?: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

interface ConfigStats {
  total_tasks: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  avg_duration: number;
  period: string;
}

const PublishConfigManagement: React.FC = () => {
  const [configs, setConfigs] = useState<PublishConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<PublishConfig | null>(null);
  const [selectedConfig, setSelectedConfig] = useState<PublishConfig | null>(null);
  const [searchText, setSearchText] = useState('');
  const [filterPipeline, setFilterPipeline] = useState<string | undefined>(undefined);
  const [filterGroup, setFilterGroup] = useState<string | undefined>(undefined);
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [configStats, setConfigStats] = useState<Record<string, ConfigStats>>({});
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);

  // 加载配置列表
  const loadConfigs = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (filterPipeline) params.pipeline_id = filterPipeline;
      if (filterGroup) params.group_id = filterGroup;
      if (filterActive !== undefined) params.is_active = filterActive;

      const response = await autoPublishService.listPublishConfigs(params);
      setConfigs(response.configs || []);
      
      // 加载每个配置的统计信息
      const statsPromises = response.configs.map((config: PublishConfig) => 
        autoPublishService.getConfigStats(config.config_id, 'week')
          .then(stats => ({ config_id: config.config_id, stats }))
          .catch(() => ({ config_id: config.config_id, stats: null }))
      );
      
      const statsResults = await Promise.all(statsPromises);
      const statsMap: Record<string, ConfigStats> = {};
      statsResults.forEach(result => {
        if (result.stats) {
          statsMap[result.config_id] = result.stats;
        }
      });
      setConfigStats(statsMap);
    } catch (error: any) {
      message.error('加载配置列表失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 加载Pipeline和账号组列表
  const loadMetadata = async () => {
    try {
      const [pipelinesRes, groupsRes] = await Promise.all([
        autoPublishService.listPipelines(),
        autoPublishService.listAccountGroups()
      ]);
      setPipelines(pipelinesRes.pipelines || []);
      setGroups(groupsRes.groups || []);
    } catch (error) {
      console.error('加载元数据失败:', error);
    }
  };

  useEffect(() => {
    loadConfigs();
    loadMetadata();
  }, [searchText, filterPipeline, filterGroup, filterActive]);

  // 创建/编辑配置
  const handleCreateOrEdit = (config?: PublishConfig) => {
    setEditingConfig(config || null);
    setModalVisible(true);
  };

  // 保存配置
  const handleSaveConfig = async (values: any) => {
    try {
      if (editingConfig) {
        await autoPublishService.updatePublishConfig(editingConfig.config_id, values);
        message.success('配置更新成功');
      } else {
        await autoPublishService.createPublishConfig(values);
        message.success('配置创建成功');
      }
      setModalVisible(false);
      loadConfigs();
    } catch (error: any) {
      message.error('保存配置失败: ' + error.message);
    }
  };

  // 删除配置
  const handleDelete = async (config: PublishConfig) => {
    try {
      await autoPublishService.deletePublishConfig(config.config_id);
      message.success('配置删除成功');
      loadConfigs();
    } catch (error: any) {
      message.error('删除配置失败: ' + error.message);
    }
  };

  // 切换配置状态
  const handleToggleStatus = async (config: PublishConfig) => {
    try {
      await autoPublishService.togglePublishConfig(config.config_id);
      message.success(`配置已${config.is_active ? '禁用' : '启用'}`);
      loadConfigs();
    } catch (error: any) {
      message.error('切换状态失败: ' + error.message);
    }
  };

  // 查看详情
  const handleViewDetail = (config: PublishConfig) => {
    setSelectedConfig(config);
    setDrawerVisible(true);
  };

  // 获取触发类型标签
  const getTriggerTypeTag = (type: string) => {
    const typeMap: Record<string, { color: string; text: string; icon: any }> = {
      scheduled: { color: 'blue', text: '定时触发', icon: <ClockCircleOutlined /> },
      manual: { color: 'orange', text: '手动触发', icon: <PlayCircleOutlined /> },
      event: { color: 'purple', text: '事件触发', icon: <ExclamationCircleOutlined /> }
    };
    const config = typeMap[type] || { color: 'default', text: type, icon: null };
    return (
      <Tag color={config.color}>
        {config.icon} {config.text}
      </Tag>
    );
  };

  // 获取状态标签
  const getStatusTag = (isActive: boolean) => {
    return isActive ? (
      <Tag color="success">
        <CheckCircleOutlined /> 启用
      </Tag>
    ) : (
      <Tag color="default">
        <PauseCircleOutlined /> 禁用
      </Tag>
    );
  };

  // 表格列定义
  const columns: ColumnsType<PublishConfig> = [
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
      render: (text, record) => (
        <Button type="link" onClick={() => handleViewDetail(record)}>
          {text}
        </Button>
      )
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_id',
      key: 'pipeline_id',
      render: (text) => {
        const pipeline = pipelines.find(p => p.pipeline_id === text);
        return pipeline ? pipeline.pipeline_name : text;
      }
    },
    {
      title: '账号组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (text) => {
        const group = groups.find(g => g.group_id === text);
        return group ? group.group_name : text;
      }
    },
    {
      title: '触发方式',
      dataIndex: 'trigger_type',
      key: 'trigger_type',
      render: (type) => getTriggerTypeTag(type)
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => (
        <Badge count={priority} style={{ backgroundColor: priority >= 80 ? '#f5222d' : priority >= 50 ? '#fa8c16' : '#52c41a' }} />
      )
    },
    {
      title: '执行统计',
      key: 'stats',
      render: (_, record) => {
        const stats = configStats[record.config_id];
        if (!stats) return <span>-</span>;
        
        return (
          <Space size="small">
            <Tooltip title="成功率">
              <Tag color={stats.success_rate >= 90 ? 'success' : stats.success_rate >= 70 ? 'warning' : 'error'}>
                {stats.success_rate}%
              </Tag>
            </Tooltip>
            <Tooltip title={`总任务数: ${stats.total_tasks}`}>
              <span>{stats.total_tasks} 次</span>
            </Tooltip>
          </Space>
        );
      }
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive, record) => (
        <Switch
          checked={isActive}
          onChange={() => handleToggleStatus(record)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => moment(text).format('YYYY-MM-DD HH:mm'),
      sorter: (a, b) => moment(a.created_at).unix() - moment(b.created_at).unix()
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleCreateOrEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="确定删除此配置？"
            description="删除后无法恢复，请谨慎操作"
            onConfirm={() => handleDelete(record)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  // 统计卡片
  const renderStatistics = () => {
    const activeCount = configs.filter(c => c.is_active).length;
    const totalCount = configs.length;
    const scheduledCount = configs.filter(c => c.trigger_type === 'scheduled').length;
    
    return (
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总配置数"
              value={totalCount}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃配置"
              value={activeCount}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="定时任务"
              value={scheduledCount}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均成功率"
              value={
                Object.values(configStats).length > 0
                  ? Object.values(configStats).reduce((sum, s) => sum + (s?.success_rate || 0), 0) / Object.values(configStats).length
                  : 0
              }
              precision={1}
              suffix="%"
              valueStyle={{ 
                color: Object.values(configStats).length > 0 && 
                  Object.values(configStats).reduce((sum, s) => sum + (s?.success_rate || 0), 0) / Object.values(configStats).length >= 90 
                  ? '#3f8600' 
                  : '#cf1322' 
              }}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  return (
    <div>
      {renderStatistics()}
      
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Search
                placeholder="搜索配置名称"
                onSearch={setSearchText}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="筛选Pipeline"
                style={{ width: '100%' }}
                allowClear
                onChange={setFilterPipeline}
              >
                {pipelines.map(p => (
                  <Option key={p.pipeline_id} value={p.pipeline_id}>
                    {p.pipeline_name}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="筛选账号组"
                style={{ width: '100%' }}
                allowClear
                onChange={setFilterGroup}
              >
                {groups.map(g => (
                  <Option key={g.group_id} value={g.group_id}>
                    {g.group_name}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="筛选状态"
                style={{ width: '100%' }}
                allowClear
                onChange={(value) => setFilterActive(value === undefined ? undefined : value === 'active')}
              >
                <Option value="active">启用</Option>
                <Option value="inactive">禁用</Option>
              </Select>
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadConfigs}>
                  刷新
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => handleCreateOrEdit()}>
                  创建配置
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={configs}
          rowKey="config_id"
          loading={loading}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      {/* 配置表单弹窗 */}
      <ConfigFormModal
        visible={modalVisible}
        config={editingConfig}
        pipelines={pipelines}
        groups={groups}
        onSave={handleSaveConfig}
        onCancel={() => setModalVisible(false)}
      />

      {/* 配置详情抽屉 */}
      <ConfigDetailDrawer
        visible={drawerVisible}
        config={selectedConfig}
        pipelines={pipelines}
        groups={groups}
        onClose={() => setDrawerVisible(false)}
        onEdit={(config) => {
          setDrawerVisible(false);
          handleCreateOrEdit(config);
        }}
      />
    </div>
  );
};

export default PublishConfigManagement;