import React from 'react';
import { Tooltip } from 'antd';
import { PublishStatusCount, PublishedAccount } from '../../types/task';
import styles from './styles.module.css';

interface PublishStatusBadgeProps {
  publishSummary?: string;
  publishStatus?: PublishStatusCount;
  publishedAccounts?: PublishedAccount[];
  showDetail?: boolean;
}

const PublishStatusBadge: React.FC<PublishStatusBadgeProps> = ({
  publishSummary,
  publishStatus,
  publishedAccounts = [],
  showDetail = true,
}) => {
  // 如果没有发布信息，显示未发布
  if (!publishStatus || publishStatus.total === 0) {
    return <span className={`${styles.badge} ${styles.notPublished}`}>未发布</span>;
  }

  // 判断发布状态类型
  const getStatusType = () => {
    const { total, success, failed } = publishStatus;
    if (success === total) return 'allSuccess';
    if (failed === total) return 'allFailed';
    if (success > 0) return 'partial';
    if (failed > 0) return 'someFailed';
    return 'pending';
  };

  const statusType = getStatusType();

  // 构建提示内容
  const renderTooltipContent = () => {
    if (!showDetail || publishedAccounts.length === 0) return null;

    return (
      <div className={styles.tooltipContent}>
        <div className={styles.tooltipTitle}>发布详情</div>
        {publishedAccounts.map((account) => (
          <div key={account.account_id} className={styles.accountItem}>
            <span className={styles.accountName}>{account.account_name}</span>
            <span className={`${styles.accountStatus} ${styles[account.status]}`}>
              {getStatusLabel(account.status)}
            </span>
            {account.youtube_video_url && (
              <a 
                href={account.youtube_video_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className={styles.videoLink}
                onClick={(e) => e.stopPropagation()}
              >
                查看
              </a>
            )}
          </div>
        ))}
      </div>
    );
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '待发布',
      uploading: '上传中',
      success: '已发布',
      failed: '失败',
    };
    return labels[status] || status;
  };

  const badge = (
    <span className={`${styles.badge} ${styles[statusType]}`}>
      {publishSummary || `${publishStatus.success}/${publishStatus.total}`}
    </span>
  );

  // 如果需要显示详情，用Tooltip包裹
  if (showDetail && publishedAccounts.length > 0) {
    return (
      <Tooltip
        title={renderTooltipContent()}
        placement="top"
        overlayClassName={styles.tooltip}
      >
        {badge}
      </Tooltip>
    );
  }

  return badge;
};

export default PublishStatusBadge;