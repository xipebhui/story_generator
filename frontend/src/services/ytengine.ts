// YTEngine API 服务
import axios from 'axios';

// YTEngine 服务配置
const YTENGINE_BASE_URL = import.meta.env.VITE_YTENGINE_URL || 'http://localhost:51077';
const YTENGINE_API_TIMEOUT = 300000; // 5分钟超时

// 创建专用的 axios 实例
const ytengineClient = axios.create({
  baseURL: YTENGINE_BASE_URL,
  timeout: YTENGINE_API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 视频上传任务接口
export interface YTEngineTask {
  uid: string;
  profileId: string;
  video: {
    path: string;
    title: string;
    description?: string;
    tags?: string[];
    thumbnail?: string;
    language?: string;
    playlist?: string;
    channelName?: string;
    visibility?: 'public' | 'private' | 'unlisted';
    category?: string;
    isNotForKid?: boolean;
    ageRestricted?: boolean;
  };
}

// 上传请求接口
export interface YTEngineUploadRequest {
  tasks: YTEngineTask[];
}

// 上传结果接口
export interface YTEngineUploadResult {
  taskId: string;
  status: 'completed' | 'failed';
  videoUrl?: string;
  error?: string;
  executionTime: number;
}

// 上传响应接口
export interface YTEngineUploadResponse {
  success: boolean;
  message?: string;
  data?: {
    results: YTEngineUploadResult[];
    summary: {
      total: number;
      success: number;
      failed: number;
      totalTime: number;
    };
  };
  error?: string;
  details?: string;
}

// Mock上传响应接口
export interface YTEngineMockResponse {
  success: boolean;
  message: string;
  totalTasks: number;
  successCount: number;
  failedCount: number;
  executionTime: number;
  results: Array<{
    success: boolean;
    message: string;
    videoId: string;
    videoUrl: string;
    title: string;
    timestamp: string;
  }>;
}

class YTEngineService {
  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await ytengineClient.get('/health');
      return response.data.status === 'healthy';
    } catch (error) {
      console.error('YTEngine health check failed:', error);
      return false;
    }
  }

  /**
   * 真实视频上传
   */
  async uploadVideos(request: YTEngineUploadRequest): Promise<YTEngineUploadResponse> {
    try {
      const response = await ytengineClient.post<YTEngineUploadResponse>('/api/upload', request);
      return response.data;
    } catch (error: any) {
      console.error('YTEngine upload failed:', error);
      throw new Error(error.response?.data?.error || error.message || '上传失败');
    }
  }

  /**
   * Mock视频上传（测试用）
   */
  async mockUpload(request: YTEngineUploadRequest): Promise<YTEngineMockResponse> {
    try {
      const response = await ytengineClient.post<YTEngineMockResponse>('/api/mock-upload', request);
      return response.data;
    } catch (error: any) {
      console.error('YTEngine mock upload failed:', error);
      throw new Error(error.response?.data?.error || error.message || 'Mock上传失败');
    }
  }

  /**
   * 创建上传任务
   */
  createUploadTask(
    taskId: string,
    profileId: string,
    videoPath: string,
    metadata: {
      title: string;
      description?: string;
      tags?: string[];
      thumbnail?: string;
      visibility?: 'public' | 'private' | 'unlisted';
      category?: string;
    }
  ): YTEngineTask {
    return {
      uid: taskId,
      profileId: profileId,
      video: {
        path: videoPath,
        title: metadata.title,
        description: metadata.description,
        tags: metadata.tags,
        thumbnail: metadata.thumbnail,
        visibility: metadata.visibility || 'private',
        category: metadata.category,
        isNotForKid: true,
        ageRestricted: false,
        language: 'chinese'
      }
    };
  }

  /**
   * 批量创建上传任务
   */
  createBatchUploadTasks(
    tasks: Array<{
      taskId: string;
      profileId: string;
      videoPath: string;
      metadata: {
        title: string;
        description?: string;
        tags?: string[];
        thumbnail?: string;
        visibility?: 'public' | 'private' | 'unlisted';
        category?: string;
      };
    }>
  ): YTEngineUploadRequest {
    return {
      tasks: tasks.map(task => 
        this.createUploadTask(
          task.taskId,
          task.profileId,
          task.videoPath,
          task.metadata
        )
      )
    };
  }

  /**
   * 解析视频分类
   */
  parseCategory(category?: string): string | undefined {
    const categoryMap: Record<string, string> = {
      'Gaming': 'Gaming',
      'Education': 'Education',
      'Entertainment': 'Entertainment',
      'Music': 'Music',
      'News': 'News & Politics',
      'Sports': 'Sports',
      'Technology': 'Science & Technology',
      '游戏': 'Gaming',
      '教育': 'Education',
      '娱乐': 'Entertainment',
      '音乐': 'Music',
      '新闻': 'News & Politics',
      '体育': 'Sports',
      '科技': 'Science & Technology'
    };

    return category ? categoryMap[category] : undefined;
  }

  /**
   * 格式化上传结果
   */
  formatUploadResults(response: YTEngineUploadResponse): string {
    if (!response.success) {
      return `上传失败: ${response.error || '未知错误'}`;
    }

    const summary = response.data?.summary;
    if (!summary) {
      return '上传完成，但无详细结果';
    }

    const results = [`上传完成: 总计${summary.total}个, 成功${summary.success}个, 失败${summary.failed}个`];
    
    if (response.data?.results) {
      response.data.results.forEach(result => {
        if (result.status === 'completed') {
          results.push(`✅ ${result.taskId}: ${result.videoUrl}`);
        } else {
          results.push(`❌ ${result.taskId}: ${result.error}`);
        }
      });
    }

    return results.join('\n');
  }

  /**
   * 检查服务状态
   */
  async checkServiceStatus(): Promise<{
    available: boolean;
    message: string;
  }> {
    const isHealthy = await this.healthCheck();
    
    return {
      available: isHealthy,
      message: isHealthy 
        ? 'YTEngine服务正常运行' 
        : 'YTEngine服务不可用，请确认服务已启动（端口: 51077）'
    };
  }
}

export const ytEngineService = new YTEngineService();