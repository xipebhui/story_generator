import React from 'react';
import { Progress, Space, Typography, Spin } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface TaskProgressProps {
  stageName: string;
  status: string;
  showIcon?: boolean;
}

const TaskProgress: React.FC<TaskProgressProps> = ({ stageName, status, showIcon = true }) => {
  const getProgressInfo = () => {
    switch (status) {
      case '成功':
        return {
          percent: 100,
          status: 'success' as const,
          icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
        };
      case '失败':
        return {
          percent: 100,
          status: 'exception' as const,
          icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
        };
      case '运行中':
        return {
          percent: 50,
          status: 'active' as const,
          icon: <Spin indicator={<SyncOutlined spin />} />,
        };
      case '准备中':
        return {
          percent: 20,
          status: 'normal' as const,
          icon: <SyncOutlined spin style={{ color: '#1890ff' }} />,
        };
      case '待处理':
      default:
        return {
          percent: 0,
          status: 'normal' as const,
          icon: <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
        };
    }
  };

  const { percent, status: progressStatus, icon } = getProgressInfo();

  return (
    <Space style={{ width: '100%' }}>
      {showIcon && icon}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text>{stageName}</Text>
          <Text type="secondary">{status}</Text>
        </div>
        <Progress
          percent={percent}
          status={progressStatus}
          showInfo={false}
          strokeWidth={8}
        />
      </div>
    </Space>
  );
};

export default TaskProgress;