import React, { useState, useEffect } from 'react';
import { Tabs } from 'antd';
import { useSearchParams } from 'react-router-dom';
import GlobalOverview from '../../components/AutoPublish/GlobalOverview';
import PipelineManagement from '../../components/AutoPublish/PipelineManagement';
import ApiKeyModal from '../../components/AutoPublish/ApiKeyModal';
import './index.less';

const { TabPane } = Tabs;

const AutoPublishPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('overview');
  const [apiKeyModalVisible, setApiKeyModalVisible] = useState(false);

  // 检查API Key
  useEffect(() => {
    const apiKey = localStorage.getItem('api_key');
    if (!apiKey) {
      setApiKeyModalVisible(true);
    }
  }, []);

  // 从URL参数读取当前Tab
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Tab切换时更新URL
  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setSearchParams({ tab: key });
  };

  return (
    <div className="auto-publish-page">
      <ApiKeyModal 
        visible={apiKeyModalVisible} 
        onOk={() => setApiKeyModalVisible(false)} 
      />
      <Tabs activeKey={activeTab} onChange={handleTabChange} size="large">
        <TabPane tab="全局概览" key="overview">
          <GlobalOverview />
        </TabPane>
        <TabPane tab="Pipeline管理" key="pipeline">
          <PipelineManagement />
        </TabPane>
        <TabPane tab="发布配置" key="config">
          <div style={{ padding: 24, background: '#fff', minHeight: 360 }}>
            发布配置 - 待实现
          </div>
        </TabPane>
        <TabPane tab="执行记录" key="task">
          <div style={{ padding: 24, background: '#fff', minHeight: 360 }}>
            执行记录 - 待实现
          </div>
        </TabPane>
        <TabPane tab="账号组" key="account">
          <div style={{ padding: 24, background: '#fff', minHeight: 360 }}>
            账号组管理 - 待实现
          </div>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default AutoPublishPage;