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