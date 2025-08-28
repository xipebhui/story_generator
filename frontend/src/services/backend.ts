// 后端API服务层 - 适配实际后端接口
import { message } from 'antd';

// API基础配置
const API_BASE = '/api'; // 通过vite代理到 http://localhost:51082/api

// 通用请求函数
async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    // 获取API Key
    const apiKey = localStorage.getItem('api_key');
    
    // 构建请求头，确保认证头不被覆盖
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options?.headers as any,
    };
    
    // 添加认证头 - 放在最后确保不被覆盖
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }
    
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers,
    });

    // 处理401未授权错误
    if (response.status === 401) {
      // 清除本地存储的认证信息
      localStorage.removeItem('api_key');
      localStorage.removeItem('username');
      // 跳转到登录页
      window.location.href = '/login';
      throw new Error('认证失败，请重新登录');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(error.detail || `请求失败: ${response.status}`);
    }

    return response.json();
  } catch (error: any) {
    console.error('API请求错误:', error);
    message.error(error.message || '网络请求失败');
    throw error;
  }
}

// Pipeline任务相关类型定义
export interface CreatePipelineRequest {
  video_id: string;        // YouTube视频ID
  creator_id: string;      // 创作者ID
  account_name?: string;   // 发布账号名称（可选）
  gender: 1 | 2;          // 1=男声, 2=女声
  duration: number;        // 每张图片显示时长(秒)
  export_video: boolean;   // 是否导出视频
  enable_subtitle: boolean; // 是否生成字幕
}

export interface CreatePipelineResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
}

export interface TaskStatus {
  task_id: string;
  video_id: string;
  creator_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_stage?: string;
  progress: number;
  start_time?: string;
  end_time?: string;
  error_message?: string;
  stages?: {
    [key: string]: {
      status: string;
      start_time?: string;
      end_time?: string;
    };
  };
  // 添加完成后的结果数据
  result?: {
    video_path?: string;
    audio_path?: string;
    draft_path?: string;
    subtitle_path?: string;
    youtube_metadata?: {
      title: string;
      description: string;
      tags: string[];
    };
  };
}

export interface TaskHistoryParams {
  page?: number;
  page_size?: number;
  status?: string;
  creator_id?: string;
}

export interface TaskHistoryResponse {
  tasks: TaskStatus[];
  total: number;
  page: number;
  page_size: number;
}

// 账号相关类型
export interface YouTubeAccount {
  id?: number;
  account_id: string;
  account_name: string;
  profile_id?: string;
  channel_url?: string;
  window_number?: string;
  description?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  // 旧字段兼容（如果后端后续更新）
  channel_name?: string;
  channel_id?: string;
  status?: 'active' | 'inactive';
  subscriber_count?: number;
  video_count?: number;
}

// 图库相关类型
export interface ImageLibrary {
  id: number;
  library_name: string;
  library_path: string;
  created_at: string;
  updated_at?: string | null;
}

export interface ImageLibrariesResponse {
  success: boolean;
  libraries: ImageLibrary[];
  count: number;
}

export interface AccountsResponse {
  accounts: YouTubeAccount[];
  total: number;
}

// 发布相关类型
export interface CreatePublishRequest {
  task_id: string;
  account_ids: string[];
  video_title: string;
  video_description: string;
  video_tags: string[];
  privacy_status: 'private' | 'unlisted' | 'public';
  thumbnail_path?: string;  // 缩略图路径
}

export interface PublishResponse {
  publish_id: string;
  status: string;
  message: string;
  results?: Array<{
    account_id: string;
    status: string;
    youtube_url?: string;
    error?: string;
  }>;
}

export interface BatchPublishRequest {
  task_id: string;
  account_count: number;
  video_metadata: {
    title: string;
    description: string;
    tags: string[];
  };
}

// Pipeline服务类
class BackendPipelineService {
  // 创建Pipeline任务
  async createPipeline(params: {
    videoId: string;
    creatorId: string;
    accountName?: string;
    gender?: 1 | 2;
    duration?: number;
    exportVideo?: boolean;
    enableSubtitle?: boolean;
  }): Promise<CreatePipelineResponse> {
    const request: CreatePipelineRequest = {
      video_id: params.videoId,
      creator_id: params.creatorId,
      account_name: params.accountName,
      gender: params.gender || 1,
      duration: params.duration || 60,
      export_video: params.exportVideo || false,
      enable_subtitle: params.enableSubtitle !== false
    };

    return apiRequest<CreatePipelineResponse>('/pipeline/run', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }
  
  // 重试Pipeline任务
  async retryPipeline(taskId: string, accountName?: string): Promise<CreatePipelineResponse> {
    return apiRequest<CreatePipelineResponse>(`/pipeline/retry/${taskId}`, {
      method: 'POST',
      body: accountName ? JSON.stringify({ account_name: accountName }) : undefined
    });
  }

  // 删除Pipeline任务
  async deletePipeline(taskId: string): Promise<{ message: string; task_id: string; deleted_publish_tasks: number }> {
    return apiRequest<{ message: string; task_id: string; deleted_publish_tasks: number }>(`/pipeline/task/${taskId}`, {
      method: 'DELETE'
    });
  }

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return apiRequest<TaskStatus>(`/pipeline/status/${taskId}`);
  }

  // 获取任务历史
  async getTaskHistory(params?: TaskHistoryParams): Promise<TaskHistoryResponse> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
    if (params?.status) queryParams.append('status', params.status);
    if (params?.creator_id) queryParams.append('creator_id', params.creator_id);

    const url = `/pipeline/history${queryParams.toString() ? `?${queryParams}` : ''}`;
    return apiRequest<TaskHistoryResponse>(url);
  }

  // 轮询任务状态
  pollTaskStatus(
    taskId: string, 
    onUpdate: (status: TaskStatus) => void,
    interval: number = 10000
  ): () => void {
    let stopped = false;
    
    const poll = async () => {
      if (stopped) return;
      
      try {
        const status = await this.getTaskStatus(taskId);
        onUpdate(status);
        
        // 如果任务还在运行，继续轮询 - 直接检查后端返回的实际状态
        if (status.status === 'pending' || status.status === 'running' || status.status === 'processing') {
          setTimeout(poll, interval);
        }
      } catch (error) {
        console.error('轮询状态失败:', error);
        // 发生错误后延长轮询间隔
        setTimeout(poll, interval * 2);
      }
    };
    
    // 立即开始第一次查询
    poll();
    
    // 返回停止函数
    return () => {
      stopped = true;
    };
  }
}

// 账号服务类
class BackendAccountService {
  // 获取账号列表
  async getAccounts(): Promise<YouTubeAccount[]> {
    const response = await apiRequest<AccountsResponse>('/accounts');
    return response.accounts;
  }

  // 获取图库列表
  async getImageLibraries(): Promise<ImageLibrary[]> {
    try {
      const response = await apiRequest<ImageLibrariesResponse>('/image_libraries');
      if (response.success) {
        return response.libraries;
      }
      return [];
    } catch (error) {
      console.error('获取图库列表失败:', error);
      return [];
    }
  }

  // 创建新账号
  async createAccount(account: {
    account_id: string;
    account_name: string;
    profile_id: string;
    window_number?: string;
    description?: string;
    is_active?: boolean;
    channel_url?: string;
  }): Promise<YouTubeAccount> {
    return apiRequest<YouTubeAccount>('/accounts', {
      method: 'POST',
      body: JSON.stringify(account)
    });
  }

  // 删除账号
  async deleteAccount(accountId: string, force: boolean = false): Promise<{
    message: string;
    account_id: string;
    operation: 'deleted' | 'deactivated';
  }> {
    const url = force ? `/accounts/${accountId}?force=true` : `/accounts/${accountId}`;
    return apiRequest(url, {
      method: 'DELETE'
    });
  }

  // 上传缩略图
  async uploadThumbnail(taskId: string, file: File): Promise<{ message: string; thumbnail_path: string }> {
    const formData = new FormData();
    formData.append('task_id', taskId);
    formData.append('file', file);
    
    // 获取认证信息
    const apiKey = localStorage.getItem('api_key');
    const headers: Record<string, string> = {};
    
    // 添加认证头（注意：使用FormData时不要设置Content-Type）
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }
    
    const response = await fetch('/api/publish/upload-thumbnail', {
      method: 'POST',
      headers,
      body: formData
    });
    
    // 处理401未授权错误
    if (response.status === 401) {
      localStorage.removeItem('api_key');
      localStorage.removeItem('username');
      window.location.href = '/login';
      throw new Error('认证失败，请重新登录');
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || '上传缩略图失败');
    }
    
    return response.json();
  }

  // 上传字幕文件
  async uploadSubtitle(taskId: string, file: File): Promise<{ message: string; path: string; video_id: string; file_size: number }> {
    const formData = new FormData();
    formData.append('task_id', taskId);
    formData.append('file', file);
    
    // 获取认证信息
    const apiKey = localStorage.getItem('api_key');
    const headers: Record<string, string> = {};
    
    // 添加认证头（注意：使用FormData时不要设置Content-Type）
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }
    
    const response = await fetch('/api/pipeline/upload-subtitle', {
      method: 'POST',
      headers,
      body: formData
    });
    
    // 处理401未授权错误
    if (response.status === 401) {
      localStorage.removeItem('api_key');
      localStorage.removeItem('username');
      window.location.href = '/login';
      throw new Error('认证失败，请重新登录');
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传字幕失败');
    }
    
    return response.json();
  }

  // 创建发布任务（使用新的schedule接口，支持定时发布）
  async createPublish(params: CreatePublishRequest): Promise<PublishResponse> {
    return apiRequest<PublishResponse>('/publish/schedule', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  // 批量发布
  async batchPublish(params: BatchPublishRequest): Promise<PublishResponse> {
    return apiRequest<PublishResponse>('/publish/batch', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  // 查询发布状态
  async getPublishStatus(taskId: string): Promise<any> {
    return apiRequest(`/publish/status/${taskId}`);
  }

  // 获取所有发布任务（使用后端的 /publish/history 接口）
  async getPublishTasks(taskId?: string): Promise<any[]> {
    try {
      // 构建查询参数
      const params = new URLSearchParams();
      if (taskId) {
        params.append('task_id', taskId);
      }
      
      const url = `/publish/history${params.toString() ? `?${params}` : ''}`;
      const response = await apiRequest(url);
      
      // 返回发布任务列表 - 后端返回的格式是 { total: number, publish_tasks: [] }
      if (Array.isArray(response)) {
        return response;
      } else if (response && response.publish_tasks) {
        return response.publish_tasks;  // 实际的数据在 publish_tasks 字段中
      } else if (response && response.history) {
        return response.history;
      } else if (response && response.items) {
        return response.items;
      } else if (response && typeof response === 'object') {
        // 如果返回的是单个对象，包装成数组
        return [response];
      }
      return [];
    } catch (error) {
      console.error('获取发布历史失败:', error);
      return [];
    }
  }
}

// 导出服务实例
export const backendPipelineService = new BackendPipelineService();
export const backendAccountService = new BackendAccountService();

// 任务管理器类 - 提供高层API
export class TaskManager {
  private pollStoppers: Map<string, () => void> = new Map();

  // 创建并监控任务
  async createAndMonitorTask(
    videoId: string,
    creatorId: string,
    options?: {
      gender?: 1 | 2;
      duration?: number;
      onProgress?: (status: TaskStatus) => void;
      onComplete?: (status: TaskStatus) => void;
      onError?: (error: any) => void;
    }
  ): Promise<string> {
    try {
      // 创建任务
      const response = await backendPipelineService.createPipeline({
        videoId,
        creatorId,
        gender: options?.gender,
        duration: options?.duration,
        exportVideo: false,
        enableSubtitle: true
      });

      const taskId = response.task_id;
      
      // 开始监控
      const stopPolling = backendPipelineService.pollTaskStatus(
        taskId,
        (status) => {
          // 进度回调
          options?.onProgress?.(status);
          
          // 完成处理
          if (status.status === 'completed') {
            this.pollStoppers.delete(taskId);
            options?.onComplete?.(status);
          }
          
          // 失败处理
          if (status.status === 'failed') {
            this.pollStoppers.delete(taskId);
            options?.onError?.(new Error(status.error_message || '任务执行失败'));
          }
        }
      );
      
      this.pollStoppers.set(taskId, stopPolling);
      
      return taskId;
    } catch (error) {
      options?.onError?.(error);
      throw error;
    }
  }

  // 停止监控任务
  stopMonitoring(taskId: string) {
    const stopper = this.pollStoppers.get(taskId);
    if (stopper) {
      stopper();
      this.pollStoppers.delete(taskId);
    }
  }

  // 停止所有监控
  stopAllMonitoring() {
    this.pollStoppers.forEach(stopper => stopper());
    this.pollStoppers.clear();
  }

  // 发布视频到YouTube
  async publishVideo(
    taskId: string,
    options?: {
      accountIds?: string[];
      title?: string;
      description?: string;
      tags?: string[];
      privacy?: 'private' | 'unlisted' | 'public';
    }
  ): Promise<PublishResponse> {
    // 如果没有指定账号，获取可用账号
    let accountIds = options?.accountIds;
    if (!accountIds || accountIds.length === 0) {
      const accounts = await backendAccountService.getAccounts();
      // 默认选择前3个活跃账号
      accountIds = accounts
        .filter(a => a.status === 'active')
        .slice(0, 3)
        .map(a => a.account_id);
    }

    // 创建发布任务
    return backendAccountService.createPublish({
      task_id: taskId,
      account_ids: accountIds,
      video_title: options?.title || `AI生成视频 - ${new Date().toLocaleDateString()}`,
      video_description: options?.description || '这是通过AI自动生成的视频内容',
      video_tags: options?.tags || ['AI生成', '自动创作'],
      privacy_status: options?.privacy || 'public'
    });
  }

  // 批量发布
  async batchPublishVideo(
    taskId: string,
    accountCount: number = 3,
    metadata?: {
      title?: string;
      description?: string;
      tags?: string[];
    }
  ): Promise<PublishResponse> {
    return backendAccountService.batchPublish({
      task_id: taskId,
      account_count: accountCount,
      video_metadata: {
        title: metadata?.title || '默认标题',
        description: metadata?.description || '默认描述',
        tags: metadata?.tags || ['tag1', 'tag2']
      }
    });
  }
}

// 创建默认任务管理器实例
export const taskManager = new TaskManager();