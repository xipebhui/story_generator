// 任务相关类型定义

export enum Gender {
  Male = 0,
  Female = 1,
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

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

// YouTube元数据
export interface YouTubeMetadata {
  title: string;
  description: string;
  tags: string[];
  category?: string;
  thumbnail?: {
    text: string;
    style: string;
    color_scheme: string;
    emotion: string;
  };
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

// 任务类型
export interface Task {
  task_id: string;
  status: TaskStatus;
  current_stage?: string | null;
  progress?: Record<string, string>;
  created_at: string;
  completed_at?: string | null;
}

// 任务结果
export interface TaskResult {
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

// 任务列表项
export interface TaskListItem {
  task_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
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