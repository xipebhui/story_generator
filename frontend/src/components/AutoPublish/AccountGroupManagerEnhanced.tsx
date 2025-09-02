import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, message, Space, Tag,
  Tooltip, Popconfirm, Transfer, Badge, Drawer, Descriptions, Row, Col,
  Statistic, List, Divider, Avatar, Progress, Empty
} from 'antd';
import {
  PlusOutlined, TeamOutlined, EditOutlined, DeleteOutlined,
  UserAddOutlined, ExperimentOutlined, EyeOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SettingOutlined
} from '@ant-design/icons';
import { autoPublishService } from '../../services/autoPublish';
import moment from 'moment';

const { TextArea } = Input;
const { Option } = Select;

interface AccountGroup {
  group_id: string;
  group_name: string;
  group_type: 'experiment' | 'production' | 'test';
  description?: string;
  is_active: boolean;
  member_count?: number;
  members?: AccountMember[];
  created_at: string;
  updated_at: string;
  stats?: {
    total_tasks: number;
    active_configs: number;
    success_rate: number;
  };
}

interface AccountMember {
  account_id: string;
  account_name: string;
  platform: string;
  role: 'control' | 'experiment' | 'member';
  join_date: string;
  is_active: boolean;
  stats?: {
    total_tasks: number;
    success_tasks: number;
    total_views: number;
  };
}

interface GroupStats {
  total_tasks: number;
  success_tasks: number;
  failed_tasks: number;
  success_rate: number;
  active_configs: number;
  total_views: number;
  member_stats: Array<{
    account_id: string;
    account_name: string;
    total_tasks: number;
    success_tasks: number;
    total_views: number;
  }>;
}

const AccountGroupManagerEnhanced: React.FC = () => {
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<AccountGroup | null>(null);
  const [groupStats, setGroupStats] = useState<GroupStats | null>(null);
  const [groupConfigs, setGroupConfigs] = useState<any[]>([]);
  const [isEdit, setIsEdit] = useState(false);
  const [form] = Form.useForm();
  const [availableAccounts, setAvailableAccounts] = useState<any[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);

  useEffect(() => {
    loadGroups();
    loadAvailableAccounts();
  }, []);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const response = await autoPublishService.getAccountGroups();
      setGroups(response.groups || []);
    } catch (error) {
      message.error('加载账号组失败');
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableAccounts = async () => {
    try {
      const response = await autoPublishService.getAccounts();
      const accountData = response.accounts?.map((acc: any) => ({
        key: acc.account_id,
        account_id: acc.account_id,
        account_name: acc.account_name,
        platform: acc.platform || 'youtube'
      })) || [];
      setAvailableAccounts(accountData);
    } catch (error) {
      console.error('加载账号失败:', error);
    }
  };

  const loadGroupDetail = async (group: AccountGroup) => {
    try {
      // Load group members
      const membersResponse = await autoPublishService.getAccountGroupMembers(group.group_id);
      
      // Load group stats
      const statsResponse = await autoPublishService.getGroupStats(group.group_id);
      setGroupStats(statsResponse);
      
      // Load group configs
      const configsResponse = await autoPublishService.getGroupConfigs(group.group_id);
      setGroupConfigs(configsResponse.configs || []);
      
      // Update group with members
      setSelectedGroup({
        ...group,
        members: membersResponse.members || []
      });
    } catch (error) {
      message.error('加载详情失败');
    }
  };

  const showGroupDetail = async (group: AccountGroup) => {
    setSelectedGroup(group);
    setDetailVisible(true);
    await loadGroupDetail(group);
  };

  const showCreateModal = () => {
    setIsEdit(false);
    form.resetFields();
    setSelectedAccounts([]);
    setModalVisible(true);
  };

  const showEditModal = (group: AccountGroup) => {
    setIsEdit(true);
    form.setFieldsValue({
      group_name: group.group_name,
      group_type: group.group_type,
      description: group.description
    });
    setSelectedGroup(group);
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (isEdit && selectedGroup) {
        await autoPublishService.updateAccountGroup(selectedGroup.group_id, values);
        message.success('更新成功');
      } else {
        await autoPublishService.createAccountGroup({
          ...values,
          account_ids: selectedAccounts
        });
        message.success('创建成功');
      }
      
      setModalVisible(false);
      loadGroups();
    } catch (error) {
      message.error(isEdit ? '更新失败' : '创建失败');
    }
  };

  const handleDelete = async (groupId: string) => {
    try {
      await autoPublishService.deleteAccountGroup(groupId);
      message.success('删除成功');
      loadGroups();
    } catch (error: any) {
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('删除失败');
      }
    }
  };

  const removeMember = async (accountId: string) => {
    if (!selectedGroup) return;
    
    try {
      await autoPublishService.removeGroupMember(selectedGroup.group_id, accountId);
      message.success('移除成功');
      await loadGroupDetail(selectedGroup);
    } catch (error) {
      message.error('移除失败');
    }
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'production': 'green',
      'test': 'blue',
      'experiment': 'orange'
    };
    return colors[type] || 'default';
  };

  const getTypeText = (type: string) => {
    const texts: Record<string, string> = {
      'production': '生产组',
      'test': '测试组',
      'experiment': '实验组'
    };
    return texts[type] || type;
  };

  const getPlatformColor = (platform: string) => {
    const colors: Record<string, string> = {
      'youtube': '#FF0000',
      'tiktok': '#000000',
      'instagram': '#E4405F'
    };
    return colors[platform] || '#888888';
  };

  const columns = [
    {
      title: '组ID',
      dataIndex: 'group_id',
      width: 120,
      render: (id: string) => (
        <Tooltip title={id}>
          <span>{id.substring(0, 10)}...</span>
        </Tooltip>
      )
    },
    {
      title: '组名称',
      dataIndex: 'group_name',
      width: 150
    },
    {
      title: '类型',
      dataIndex: 'group_type',
      width: 100,
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{getTypeText(type)}</Tag>
      )
    },
    {
      title: '账号数',
      dataIndex: 'member_count',
      width: 80,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      )
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Badge 
          status={active ? 'success' : 'default'} 
          text={active ? '启用' : '停用'} 
        />
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 150,
      render: (time: string) => moment(time).format('YYYY-MM-DD HH:mm')
    },
    {
      title: '操作',
      width: 200,
      render: (_: any, record: AccountGroup) => (
        <Space>
          <Button 
            type="link" 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => showGroupDetail(record)}>
            查看
          </Button>
          <Button 
            type="link" 
            size="small" 
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个账号组吗？"
            onConfirm={() => handleDelete(record.group_id)}>
            <Button 
              type="link" 
              size="small" 
              danger
              icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Card 
      title="账号组管理"
      extra={
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={showCreateModal}>
          创建账号组
        </Button>
      }>
      
      <Table
        columns={columns}
        dataSource={groups}
        loading={loading}
        rowKey="group_id"
        pagination={false}
      />

      {/* 创建/编辑模态框 */}
      <Modal
        title={isEdit ? "编辑账号组" : "创建账号组"}
        visible={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={800}>
        
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item 
                name="group_name" 
                label="组名称" 
                rules={[
                  { required: true, message: '请输入组名称' },
                  { max: 50, message: '名称不能超过50个字符' }
                ]}>
                <Input placeholder="例如: 故事频道组" />
              </Form.Item>
            </Col>
            
            <Col span={12}>
              <Form.Item 
                name="group_type" 
                label="组类型" 
                rules={[{ required: true }]}>
                <Select placeholder="选择组类型">
                  <Option value="production">
                    <Tag color="green">生产组</Tag> - 正式发布
                  </Option>
                  <Option value="test">
                    <Tag color="blue">测试组</Tag> - 测试使用
                  </Option>
                  <Option value="experiment">
                    <Tag color="orange">实验组</Tag> - A/B测试
                  </Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="账号组的用途说明" />
          </Form.Item>
          
          {!isEdit && (
            <Form.Item label="选择账号成员">
              <Transfer
                dataSource={availableAccounts}
                targetKeys={selectedAccounts}
                onChange={setSelectedAccounts}
                render={item => (
                  <Space>
                    <Avatar size="small" style={{ backgroundColor: getPlatformColor(item.platform) }}>
                      {item.platform.substring(0, 1).toUpperCase()}
                    </Avatar>
                    {item.account_name}
                  </Space>
                )}
                titles={['可选账号', '已选账号']}
                listStyle={{ width: 350, height: 300 }}
                showSearch
                filterOption={(inputValue, option) =>
                  option.account_name.toLowerCase().includes(inputValue.toLowerCase())
                }
              />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 账号组详情抽屉 */}
      <Drawer
        title="账号组详情"
        width={900}
        visible={detailVisible}
        onClose={() => {
          setDetailVisible(false);
          setSelectedGroup(null);
          setGroupStats(null);
          setGroupConfigs([]);
        }}>
        
        {selectedGroup && (
          <>
            {/* 基本信息 */}
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="组ID">{selectedGroup.group_id}</Descriptions.Item>
              <Descriptions.Item label="组名称">{selectedGroup.group_name}</Descriptions.Item>
              <Descriptions.Item label="组类型">
                <Tag color={getTypeColor(selectedGroup.group_type)}>
                  {getTypeText(selectedGroup.group_type)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge status={selectedGroup.is_active ? 'success' : 'default'} 
                  text={selectedGroup.is_active ? '启用' : '停用'} />
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{selectedGroup.created_at}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{selectedGroup.updated_at}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedGroup.description || '-'}
              </Descriptions.Item>
            </Descriptions>
            
            <Divider />
            
            {/* 统计信息 */}
            {groupStats && (
              <>
                <Card title="统计信息" size="small">
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title="账号数量" value={selectedGroup.members?.length || 0} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="关联配置" value={groupStats.active_configs} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="总任务数" value={groupStats.total_tasks} />
                    </Col>
                    <Col span={6}>
                      <Statistic 
                        title="成功率" 
                        value={groupStats.success_rate} 
                        suffix="%" />
                    </Col>
                  </Row>
                </Card>
                
                <Divider />
              </>
            )}
            
            {/* 成员列表 */}
            <Card title={`成员账号 (${selectedGroup.members?.length || 0})`} size="small">
              {selectedGroup.members && selectedGroup.members.length > 0 ? (
                <Table
                  dataSource={selectedGroup.members}
                  rowKey="account_id"
                  size="small"
                  pagination={false}
                  columns={[
                    {
                      title: '账号ID',
                      dataIndex: 'account_id',
                      width: 120
                    },
                    {
                      title: '账号名称',
                      dataIndex: 'account_name',
                      width: 150
                    },
                    {
                      title: '平台',
                      dataIndex: 'platform',
                      width: 100,
                      render: (platform: string) => (
                        <Tag color={getPlatformColor(platform)}>
                          {platform.toUpperCase()}
                        </Tag>
                      )
                    },
                    {
                      title: '角色',
                      dataIndex: 'role',
                      width: 100,
                      render: (role: string) => {
                        const config: Record<string, any> = {
                          'control': { color: 'blue', text: '对照组' },
                          'experiment': { color: 'orange', text: '实验组' },
                          'member': { color: 'default', text: '成员' }
                        };
                        const roleConfig = config[role] || config['member'];
                        return <Tag color={roleConfig.color}>{roleConfig.text}</Tag>;
                      }
                    },
                    {
                      title: '加入时间',
                      dataIndex: 'join_date',
                      width: 150,
                      render: (date: string) => moment(date).format('YYYY-MM-DD')
                    },
                    {
                      title: '操作',
                      width: 100,
                      render: (_: any, record: AccountMember) => (
                        <Popconfirm
                          title="确定要移除该账号吗？"
                          onConfirm={() => removeMember(record.account_id)}>
                          <Button type="link" size="small" danger>
                            移除
                          </Button>
                        </Popconfirm>
                      )
                    }
                  ]}
                />
              ) : (
                <Empty description="暂无成员" />
              )}
            </Card>
            
            <Divider />
            
            {/* 关联配置 */}
            <Card title={`关联的发布配置 (${groupConfigs.length})`} size="small">
              {groupConfigs.length > 0 ? (
                <List
                  dataSource={groupConfigs}
                  renderItem={config => (
                    <List.Item>
                      <List.Item.Meta
                        title={config.config_name}
                        description={`Pipeline: ${config.pipeline_name} | 任务数: ${config.task_count}`}
                      />
                      <Badge 
                        status={config.is_active ? 'success' : 'default'} 
                        text={config.is_active ? '启用' : '停用'} />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无关联配置" />
              )}
            </Card>
          </>
        )}
      </Drawer>
    </Card>
  );
};

export default AccountGroupManagerEnhanced;