import React from 'react';
import { Layout, Menu, theme } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  PlusCircleOutlined,
  UnorderedListOutlined,
  RocketOutlined,
  BarChartOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/create',
      icon: <PlusCircleOutlined />,
      label: '创作中心',
      children: [
        {
          key: '/create',
          label: '新建任务',
        },
      ],
    },
    {
      key: '/tasks-group',
      icon: <UnorderedListOutlined />,
      label: '任务管理',
      children: [
        {
          key: '/tasks',
          label: '任务列表',
        },
        {
          key: '/monitor',
          label: '任务监控',
        },
      ],
    },
    {
      key: '/publish-group',
      icon: <RocketOutlined />,
      label: '发布中心',
      children: [
        {
          key: '/publish',
          label: '待发布',
        },
        {
          key: '/publish/history',
          label: '发布历史',
        },
      ],
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  // 获取当前选中的菜单项
  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/task/')) {
      return ['/tasks'];
    }
    if (path.startsWith('/monitor/')) {
      return ['/monitor'];
    }
    return [path];
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
          <BarChartOutlined style={{ marginRight: '10px' }} />
          视频创作工作台
        </div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: colorBgContainer }}>
          <Menu
            mode="inline"
            selectedKeys={getSelectedKeys()}
            defaultOpenKeys={['/create', '/tasks-group', '/publish-group']}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
            onClick={handleMenuClick}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: '8px',
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;