// Pipeline API服务
import api from './api';
import { CreateTaskResponse, PipelineRequest } from '../types/api';
import { Task, TaskResult, TaskStatus } from '../types/task';

interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  current_stage: string | null;
  progress: Record<string, string>;
  created_at: string;
  completed_at: string | null;
}

interface TaskListResponse {
  total: number;
  tasks: Task[];
}

// 视频合并请求接口
interface VideoMergeRequest {
  portrait_folder: string;
  landscape_folder: string;
  custom_id?: string;
}

class PipelineService {
  // 创建任务
  async runPipeline(request: PipelineRequest): Promise<CreateTaskResponse> {
    const response = await api.post('/pipeline/run', request);
    return response.data || response;
  }

  // 获取任务状态
  async getStatus(taskId: string): Promise<TaskStatusResponse> {
    const response = await api.get(`/pipeline/status/${taskId}`);
    return response.data || response;
  }

  // 获取任务结果
  async getResult(taskId: string): Promise<TaskResult> {
    const response = await api.get(`/pipeline/result/${taskId}`);
    return response.data || response;
  }

  // 获取任务列表
  async listTasks(): Promise<TaskListResponse> {
    const response = await api.get('/pipeline/tasks');
    return response.data || response;
  }

  // 清空所有任务（测试用）
  async clearTasks(): Promise<{ message: string }> {
    const response = await api.delete('/pipeline/clear');
    return response.data || response;
  }

  // 健康检查
  async healthCheck(): Promise<any> {
    const response = await api.get('/health');
    return response.data || response;
  }

  // 视频合并
  async mergeVideos(request: VideoMergeRequest): Promise<CreateTaskResponse> {
    const response = await api.post('/video/merge', request);
    return response.data || response;
  }
  
  // 注意：视频合并任务的状态查询复用 getStatus 和 getResult 方法
}

export const pipelineService = new PipelineService();
export type { VideoMergeRequest };