import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  message,
  Popconfirm,
  Avatar,
  Tooltip
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  YoutubeOutlined,
  ChromeOutlined,
  CheckCircleOutlined,
  StopOutlined
} from '@ant-design/icons';
import { Account } from '../../types/account';
import { accountService } from '../../services/account';
import { backendAccountService } from '../../services/backend';
import type { ColumnsType } from 'antd/es/table';

interface AccountManagerProps {
  visible?: boolean;
  onClose?: () => void;
}

const AccountManager: React.FC<AccountManagerProps> = ({
  visible = true,
  onClose
}) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [form] = Form.useForm();

  // 加载账号列表
  const loadAccounts = async () => {
    setLoading(true);
    try {
      // 优先从后端加载真实账号
      const backendAccounts = await backendAccountService.getAccounts();
      
      // 转换为前端账号格式
      const formattedAccounts = backendAccounts.map(acc => ({
        id: acc.account_id,
        name: acc.account_name,
        youtube_account: acc.channel_name,
        youtube_channel_id: acc.channel_id,
        bitbrowser_name: acc.account_id,
        status: acc.status,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }));
      
      setAccounts(formattedAccounts);
    } catch (error) {
      console.warn('无法加载后端账号，使用本地模拟账号');
      // 回退到本地模拟数据
      try {
        const data = await accountService.getAccounts();
        setAccounts(data);
      } catch (localError) {
        message.error('加载账号列表失败');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  // 处理创建/编辑账号
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingAccount) {
        // 编辑账号
        await accountService.updateAccount(editingAccount.id, values);
        message.success('账号更新成功');
      } else {
        // 创建账号
        await accountService.createAccount({
          ...values,
          status: 'active'
        });
        message.success('账号创建成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      setEditingAccount(null);
      loadAccounts();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 处理删除账号
  const handleDelete = async (id: string) => {
    try {
      await accountService.deleteAccount(id);
      message.success('账号删除成功');
      loadAccounts();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 处理编辑账号
  const handleEdit = (account: Account) => {
    setEditingAccount(account);
    form.setFieldsValue(account);
    setModalVisible(true);
  };

  // 处理状态切换
  const handleToggleStatus = async (account: Account) => {
    try {
      await accountService.updateAccount(account.id, {
        status: account.status === 'active' ? 'inactive' : 'active'
      });
      message.success('状态更新成功');
      loadAccounts();
    } catch (error) {
      message.error('状态更新失败');
    }
  };

  // 表格列配置
  const columns: ColumnsType<Account> = [
    {
      title: '账号',
      key: 'account',
      width: 120,
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
          </div>
        </Space>
      )
    },
    {
      title: 'YouTube账号',
      dataIndex: 'youtube_account',
      key: 'youtube_account',
      render: (text) => (
        <Space>
          <YoutubeOutlined style={{ color: '#FF0000' }} />
          {text}
        </Space>
      )
    },
    {
      title: '比特浏览器',
      dataIndex: 'bitbrowser_name',
      key: 'bitbrowser_name',
      render: (text) => (
        <Space>
          <ChromeOutlined style={{ color: '#4285F4' }} />
          {text}
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag 
          icon={status === 'active' ? <CheckCircleOutlined /> : <StopOutlined />}
          color={status === 'active' ? 'success' : 'default'}
        >
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title={record.status === 'active' ? '禁用' : '启用'}>
            <Button
              type="text"
              icon={record.status === 'active' ? <StopOutlined /> : <CheckCircleOutlined />}
              onClick={() => handleToggleStatus(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个账号吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  if (!visible) return null;

  return (
    <>
      <Card
        title="账号管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingAccount(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            添加账号
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={accounts}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: false
          }}
        />
      </Card>

      <Modal
        title={editingAccount ? '编辑账号' : '添加账号'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingAccount(null);
        }}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="账号名称"
            rules={[{ required: true, message: '请输入账号名称' }]}
          >
            <Input placeholder="例如：主账号" />
          </Form.Item>

          <Form.Item
            name="youtube_account"
            label="YouTube账号"
            rules={[{ required: true, message: '请输入YouTube账号' }]}
          >
            <Input 
              prefix={<YoutubeOutlined />}
              placeholder="例如：MyYouTubeChannel" 
            />
          </Form.Item>

          <Form.Item
            name="bitbrowser_name"
            label="比特浏览器名称"
            rules={[{ required: true, message: '请输入比特浏览器名称' }]}
          >
            <Input 
              prefix={<ChromeOutlined />}
              placeholder="例如：BitBrowser_Main" 
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AccountManager;