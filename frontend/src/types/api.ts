// API响应通用类型

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 创建任务响应
export interface CreateTaskResponse {
  task_id: string;
  message: string;
  status_url: string;
  result_url: string;
}

// Pipeline请求参数
export interface PipelineRequest {
  video_id: string;
  creator_id: string;
  gender?: number;
  duration?: number;
  image_dir?: string;
  export_video?: boolean;
  enable_subtitle?: boolean;
  workflow_type?: string;
  [key: string]: any; // 允许额外的工作流特定参数
}