import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Tag,
  Tooltip,
  Popconfirm,
  Transfer,
  Badge
} from 'antd';
import {
  PlusOutlined,
  TeamOutlined,
  EditOutlined,
  DeleteOutlined,
  UserAddOutlined,
  ExperimentOutlined
} from '@ant-design/icons';
import { autoPublishService } from '../../services/autoPublish';
import { backendAccountService } from '../../services/backend';

interface AccountGroup {
  group_id: string;
  group_name: string;
  group_type: 'experiment' | 'production' | 'test';
  description?: string;
  is_active: boolean;
  member_count: number;
  created_at: string;
  members?: string[];
}

const AccountGroupManager: React.FC = () => {
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);

  useEffect(() => {
    loadGroups();
    loadAccounts();
  }, []);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const response = await autoPublishService.listAccountGroups();
      console.log('API响应:', response);
      const data = response?.groups || response || [];
      console.log('提取的数据:', data);
      setGroups(Array.isArray(data) ? data : []);
      console.log('设置的groups:', Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载账号组失败:', error);
      message.error('加载账号组失败');
      setGroups([]);
    } finally {
      setLoading(false);
    }
  };

  const loadAccounts = async () => {
    try {
      const response = await backendAccountService.getAccounts();
      const data = response?.accounts || response || [];
      setAccounts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载账号失败:', error);
      setAccounts([]);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setSelectedAccounts([]);
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      await autoPublishService.createAccountGroup({
        ...values,
        account_ids: selectedAccounts
      });
      message.success('创建账号组成功');
      setModalVisible(false);
      loadGroups();
    } catch (error) {
      message.error('创建账号组失败');
    }
  };

  const handleDelete = async (groupId: string) => {
    try {
      await autoPublishService.deleteAccountGroup(groupId);
      message.success('删除账号组成功');
      loadGroups();
    } catch (error) {
      message.error('删除账号组失败');
    }
  };

  const columns = [
    {
      title: '组名称',
      dataIndex: 'group_name',
      key: 'group_name',
      render: (text: string, record: AccountGroup) => (
        <Space>
          <TeamOutlined />
          <span>{text}</span>
          {record.group_type === 'experiment' && (
            <Tag color="blue">
              <ExperimentOutlined /> 实验组
            </Tag>
          )}
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'group_type',
      key: 'group_type',
      width: 100,
      render: (type: string) => {
        const typeMap = {
          experiment: { text: '实验', color: 'blue' },
          production: { text: '生产', color: 'green' },
          test: { text: '测试', color: 'orange' }
        };
        const config = typeMap[type as keyof typeof typeMap];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      }
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      key: 'member_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '活跃' : '停用'}
        </Tag>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: AccountGroup) => (
        <Space>
          <Tooltip title="编辑">
            <Button icon={<EditOutlined />} size="small" />
          </Tooltip>
          <Tooltip title="管理成员">
            <Button icon={<UserAddOutlined />} size="small" />
          </Tooltip>
          <Popconfirm
            title="确定删除此账号组？"
            onConfirm={() => handleDelete(record.group_id)}
          >
            <Tooltip title="删除">
              <Button danger icon={<DeleteOutlined />} size="small" />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Card
      title="账号组管理"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建账号组
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={groups}
        rowKey="group_id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 个账号组`
        }}
      />

      <Modal
        title="创建账号组"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="group_name"
            label="组名称"
            rules={[{ required: true, message: '请输入组名称' }]}
          >
            <Input placeholder="例如：小说账号组A" />
          </Form.Item>

          <Form.Item
            name="group_type"
            label="组类型"
            rules={[{ required: true, message: '请选择组类型' }]}
            initialValue="production"
          >
            <Select>
              <Select.Option value="production">生产组</Select.Option>
              <Select.Option value="experiment">实验组</Select.Option>
              <Select.Option value="test">测试组</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={2} placeholder="描述此账号组的用途" />
          </Form.Item>

          <Form.Item label="选择账号">
            <Transfer
              dataSource={accounts.map(acc => ({
                key: acc.account_id,
                title: acc.account_name,
                description: acc.description
              }))}
              targetKeys={selectedAccounts}
              onChange={setSelectedAccounts}
              render={item => item.title}
              titles={['可用账号', '已选账号']}
              listStyle={{ width: 300, height: 300 }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default AccountGroupManager;