import React, { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import router from './router';
import { performHealthCheck } from './utils/healthCheck';
import './App.css';
import './styles/modern.css';

function App() {
  // 在应用启动时进行健康检查
  useEffect(() => {
    performHealthCheck().then(status => {
      console.log('服务状态:', status);
      if (!status.backend) {
        console.error('⚠️ 后端服务不可用，请启动后端服务 (localhost:51082)');
      }
    });
  }, []);

  return (
    <ConfigProvider locale={zhCN}>
      <AntdApp>
        <RouterProvider router={router} />
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;