import React from 'react';
import { Tag } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

interface StatusBadgeProps {
  status: string;
  showIcon?: boolean;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, showIcon = true }) => {
  const getStatusConfig = () => {
    switch (status.toLowerCase()) {
      case 'completed':
      case '成功':
        return {
          color: 'success',
          icon: showIcon ? <CheckCircleOutlined /> : null,
          text: '已完成',
        };
      case 'failed':
      case '失败':
        return {
          color: 'error',
          icon: showIcon ? <CloseCircleOutlined /> : null,
          text: '失败',
        };
      case 'running':
      case '运行中':
        return {
          color: 'processing',
          icon: showIcon ? <SyncOutlined spin /> : null,
          text: '运行中',
        };
      case 'pending':
      case '待处理':
      default:
        return {
          color: 'default',
          icon: showIcon ? <ClockCircleOutlined /> : null,
          text: '待处理',
        };
    }
  };

  const { color, icon, text } = getStatusConfig();

  return (
    <Tag color={color} icon={icon}>
      {text}
    </Tag>
  );
};

export default StatusBadge;