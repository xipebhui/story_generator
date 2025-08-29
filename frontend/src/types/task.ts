// 任务相关类型定义

export enum Gender {
  Male = 0,
  Female = 1,
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export enum StageStatus {
  Pending = '待处理',
  Running = '运行中',
  Success = '成功',
  Failed = '失败',
}

// 创建任务请求
export interface PipelineRequest {
  video_id: string;
  creator_id: string;
  gender: Gender;
  duration: number;
  image_dir?: string;
  export_video: boolean;
}

// 任务状态响应
export interface TaskStatusResponse {
  task_id: string;
  status: string;
  current_stage: string | null;
  progress: Record<string, string>;
  created_at: string;
  completed_at: string | null;
}

// YouTube元数据 - 支持新旧两种格式
export interface YouTubeMetadata {
  // 新格式
  titles?: {
    chinese: string[];
    english: string[];
  };
  descriptions?: {
    chinese: string;
    english: string;
  };
  tags?: {
    chinese: string[];
    english: string[];
    mixed: string[];
  } | string[]; // 兼容旧格式
  thumbnail?: {
    visual_focus?: string;
    text_overlay?: {
      chinese: string;
      english: string;
    };
    color_scheme?: string;
    emotion?: string;
    // 兼容旧格式
    text?: string;
    style?: string;
  };
  // 旧格式兼容
  title?: string;
  description?: string;
  category?: string;
}

// 任务结果响应
export interface TaskResultResponse {
  task_id: string;
  status: string;
  youtube_metadata?: YouTubeMetadata;
  video_path?: string;
  video_url?: string;
  preview_url?: string;
  draft_path?: string;
  audio_path?: string;
  story_path?: string;
  error?: string;
}

// 发布状态统计
export interface PublishStatusCount {
  total: number;
  success: number;
  pending: number;
  uploading: number;
  failed: number;
}

// 发布账号信息
export interface PublishedAccount {
  account_id: string;
  account_name: string;
  status: 'pending' | 'uploading' | 'success' | 'failed' | 'cancelled';
  youtube_video_url?: string | null;
  published_at?: string | null;
  error_message?: string | null;
  publish_id?: string; // 发布任务ID，用于重试和删除操作
}

// 任务类型
export interface Task {
  task_id: string;
  workflow?: string;  // 工作流类型
  status: TaskStatus;
  current_stage?: string | null;
  progress?: number | Record<string, string>;  // 进度百分比或详细进度
  created_at: string;
  completed_at?: string | null;
  duration?: number;  // 执行时长（秒） - 兼容旧字段
  total_duration?: number;  // 执行时长（秒） - 新字段
  error_message?: string;  // 错误信息
  params?: any;  // 任务参数
  stages?: Array<{  // 阶段信息
    name: string;
    status: string;
    start_time?: string;
    end_time?: string;
  }>;
  // 发布状态相关
  publish_summary?: string;  // 发布状态总结，如 "已发布 (2)" 或 "部分发布 (1/3)"
  publish_status?: PublishStatusCount;  // 发布状态统计
  published_accounts?: PublishedAccount[];  // 已发布账号列表
}

// 任务结果
export interface TaskResult {
  task_id?: string;
  status?: string;
  youtube_metadata?: YouTubeMetadata;
  video_path?: string;
  video_url?: string;
  preview_url?: string;
  draft_path?: string;
  audio_path?: string;
  story_path?: string;
  error?: string;
}

// 任务列表项
export interface TaskListItem {
  task_id: string;
  workflow?: string;
  status: string;
  current_stage?: string;
  progress?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// 任务列表响应
export interface TaskListResponse {
  total: number;
  tasks: TaskListItem[];
}

// 发布请求（预留）
export interface PublishRequest {
  task_id: string;
  video_path: string;
  title: string;
  description: string;
  tags: string[];
  thumbnail_path?: string;
  publish_time?: number; // 延迟发布时间（分钟）
}

// 发布历史项（预留）
export interface PublishHistoryItem {
  id: string;
  task_id: string;
  title: string;
  published_at: string;
  status: 'published' | 'scheduled' | 'failed';
  platform: string;
}