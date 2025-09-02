// 账号相关类型定义

export interface Account {
  id: string;
  name: string;                    // 账号名称
  youtube_account: string;         // YouTube账号
  bitbrowser_name: string;        // 比特浏览器名称（profile_id）
  status: 'active' | 'inactive';  // 账号状态
  created_at: string;
  updated_at: string;
  
  // 新增字段
  display_name?: string;           // YouTube显示名称
  remark?: string;                 // 账号说明
  tags?: string[];                 // 账号标签
  today_uploaded?: number;         // 今日已上传
  success_count?: number;          // 成功次数
  failed_count?: number;           // 失败次数
  total_uploaded?: number;         // 总上传数
  daily_quota?: number;            // 每日限额
  email?: string;                  // 邮箱
  channel_url?: string;            // 频道URL
  profile_id?: string;             // 比特浏览器profile ID
  description?: string;            // 描述
  window_number?: string;          // 窗口序号
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