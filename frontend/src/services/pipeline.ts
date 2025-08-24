// Pipeline API服务
import api from './api';
import {
  PipelineRequest,
  TaskStatusResponse,
  TaskResultResponse,
  TaskListResponse,
  PublishRequest,
  PublishHistoryItem,
} from '@/types/task';
import { CreateTaskResponse } from '@/types/api';

class PipelineService {
  // ============ 已实现的API ============
  
  // 创建任务
  async createTask(request: PipelineRequest): Promise<CreateTaskResponse> {
    return api.post('/pipeline/run', request);
  }

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return api.get(`/pipeline/status/${taskId}`);
  }

  // 获取任务结果
  async getTaskResult(taskId: string): Promise<TaskResultResponse> {
    return api.get(`/pipeline/result/${taskId}`);
  }

  // 获取任务列表
  async getTaskList(): Promise<TaskListResponse> {
    return api.get('/pipeline/tasks');
  }

  // 清空所有任务（测试用）
  async clearTasks(): Promise<{ message: string }> {
    return api.delete('/pipeline/clear');
  }

  // ============ 预留的API（未实现） ============
  
  // 发布视频
  async publishVideo(request: PublishRequest): Promise<any> {
    // TODO: 实现发布视频API
    console.warn('publishVideo API not implemented yet');
    return Promise.resolve({
      success: false,
      message: '发布功能尚未实现',
    });
  }

  // 获取发布历史
  async getPublishHistory(): Promise<PublishHistoryItem[]> {
    // TODO: 实现获取发布历史API
    console.warn('getPublishHistory API not implemented yet');
    return Promise.resolve([]);
  }

  // 更新发布计划
  async updatePublishSchedule(id: string, schedule: any): Promise<any> {
    // TODO: 实现更新发布计划API
    console.warn('updatePublishSchedule API not implemented yet');
    return Promise.resolve({
      success: false,
      message: '更新发布计划功能尚未实现',
    });
  }

  // 删除任务
  async deleteTask(taskId: string): Promise<any> {
    // TODO: 实现删除任务API
    console.warn('deleteTask API not implemented yet');
    return Promise.resolve({
      success: false,
      message: '删除任务功能尚未实现',
    });
  }

  // 重试任务
  async retryTask(taskId: string): Promise<any> {
    // TODO: 实现重试任务API
    console.warn('retryTask API not implemented yet');
    return Promise.resolve({
      success: false,
      message: '重试任务功能尚未实现',
    });
  }
}

export default new PipelineService();