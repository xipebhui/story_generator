import React from 'react';
import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';
import {
  VideoCameraOutlined,
} from '@ant-design/icons';

const { Header, Content } = Layout;

const AppLayout: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        display: 'flex', 
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
      }}>
        <div style={{ 
          color: 'white', 
          fontSize: '24px', 
          fontWeight: 'bold',
          display: 'flex',
          alignItems: 'center'
        }}>
          <VideoCameraOutlined style={{ marginRight: '12px', fontSize: '32px' }} />
          视频创作工作台
        </div>
      </Header>
      <Content style={{ 
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        minHeight: 'calc(100vh - 64px)'
      }}>
        <Outlet />
      </Content>
    </Layout>
  );
};

export default AppLayout;