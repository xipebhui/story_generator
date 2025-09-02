import React, { useState, useEffect } from 'react';
import { Modal, Input, Alert } from 'antd';

interface ApiKeyModalProps {
  visible: boolean;
  onOk: () => void;
}

const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ visible, onOk }) => {
  const [apiKey, setApiKey] = useState('');
  
  useEffect(() => {
    // 检查localStorage中是否有API Key
    const savedKey = localStorage.getItem('api_key');
    if (savedKey) {
      setApiKey(savedKey);
    } else {
      // 设置默认测试API Key
      setApiKey('2552be3f-8a68-4505-abb9-e4ddbb69869a');
    }
  }, [visible]);
  
  const handleOk = () => {
    if (apiKey) {
      localStorage.setItem('api_key', apiKey);
      onOk();
    }
  };
  
  return (
    <Modal
      title="设置API Key"
      open={visible}
      onOk={handleOk}
      closable={false}
      maskClosable={false}
      okText="确定"
      cancelButtonProps={{ style: { display: 'none' } }}
    >
      <Alert
        message="请输入API Key以访问自动发布系统"
        description="测试API Key: 2552be3f-8a68-4505-abb9-e4ddbb69869a"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Input
        placeholder="请输入API Key"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        size="large"
      />
    </Modal>
  );
};

export default ApiKeyModal;