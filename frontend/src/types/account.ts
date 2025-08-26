// 账号相关类型定义

export interface Account {
  id: string;
  name: string;                    // 账号名称
  youtube_account: string;         // YouTube账号
  bitbrowser_name: string;        // 比特浏览器名称
  status: 'active' | 'inactive';  // 账号状态
  created_at: string;
  updated_at: string;
}

export interface PublishTask {
  id: string;
  task_id: string;                 // 关联的Pipeline任务ID
  account_id: string;              // 发布账号ID
  account_name: string;            // 账号名称（冗余存储）
  title: string;                   // 视频标题
  description: string;             // 视频描述
  video_path: string;              // 视频文件路径
  thumbnail_path?: string;         // 封面图片路径
  publish_time?: string;           // 发布时间（立即发布则为空）
  publish_interval?: number;       // 发布时间间隔（分钟）
  status: 'pending' | 'publishing' | 'published' | 'failed';  // 发布状态
  error_message?: string;          // 错误信息
  youtube_url?: string;            // 发布后的YouTube链接
  created_at: string;
  published_at?: string;
}

export interface CreatePublishRequest {
  task_id: string;
  account_id: string;
  title: string;
  description: string;
  video_path: string;
  thumbnail?: File | string;       // 封面文件
  publish_mode: 'immediate' | 'scheduled' | 'interval';
  publish_time?: string;           // 定时发布时间
  publish_interval?: number;       // 发布间隔（分钟）
  tags?: string[];
  category?: string;
}