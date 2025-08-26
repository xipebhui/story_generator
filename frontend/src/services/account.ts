// 账号管理服务
import { Account, PublishTask, CreatePublishRequest } from '../types/account';
import { ytEngineService } from './ytengine';
import { message } from 'antd';

// 模拟账号数据
const mockAccounts: Account[] = [
  {
    id: 'acc_1',
    name: '主账号',
    youtube_account: 'MyYouTubeChannel',
    bitbrowser_name: 'BitBrowser_Main',
    status: 'active',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z'
  },
  {
    id: 'acc_2',
    name: '副账号1',
    youtube_account: 'SecondChannel',
    bitbrowser_name: 'BitBrowser_Second',
    status: 'active',
    created_at: '2024-01-20T10:00:00Z',
    updated_at: '2024-01-20T10:00:00Z'
  },
  {
    id: 'acc_3',
    name: '测试账号',
    youtube_account: 'TestChannel',
    bitbrowser_name: 'BitBrowser_Test',
    status: 'inactive',
    created_at: '2024-02-01T10:00:00Z',
    updated_at: '2024-02-01T10:00:00Z'
  }
];

// 模拟发布任务数据
const mockPublishTasks: PublishTask[] = [];

class AccountService {
  // 获取账号列表
  async getAccounts(): Promise<Account[]> {
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 500));
    return mockAccounts;
  }

  // 获取单个账号
  async getAccount(id: string): Promise<Account | undefined> {
    await new Promise(resolve => setTimeout(resolve, 300));
    return mockAccounts.find(acc => acc.id === id);
  }

  // 创建账号
  async createAccount(account: Omit<Account, 'id' | 'created_at' | 'updated_at'>): Promise<Account> {
    await new Promise(resolve => setTimeout(resolve, 500));
    const newAccount: Account = {
      ...account,
      id: `acc_${Date.now()}`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    mockAccounts.push(newAccount);
    return newAccount;
  }

  // 更新账号
  async updateAccount(id: string, updates: Partial<Account>): Promise<Account> {
    await new Promise(resolve => setTimeout(resolve, 500));
    const index = mockAccounts.findIndex(acc => acc.id === id);
    if (index === -1) {
      throw new Error('账号不存在');
    }
    mockAccounts[index] = {
      ...mockAccounts[index],
      ...updates,
      updated_at: new Date().toISOString()
    };
    return mockAccounts[index];
  }

  // 删除账号
  async deleteAccount(id: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 500));
    const index = mockAccounts.findIndex(acc => acc.id === id);
    if (index !== -1) {
      mockAccounts.splice(index, 1);
    }
  }

  // 创建发布任务
  async createPublishTask(request: CreatePublishRequest): Promise<PublishTask> {
    const account = mockAccounts.find(acc => acc.id === request.account_id);
    if (!account) {
      throw new Error('账号不存在');
    }

    const publishTask: PublishTask = {
      id: `pub_${Date.now()}`,
      task_id: request.task_id,
      account_id: request.account_id,
      account_name: account.name,
      title: request.title,
      description: request.description,
      video_path: request.video_path,
      thumbnail_path: typeof request.thumbnail === 'string' ? request.thumbnail : undefined,
      publish_time: request.publish_time,
      publish_interval: request.publish_interval,
      status: 'pending',
      created_at: new Date().toISOString()
    };

    mockPublishTasks.push(publishTask);

    // 检查YTEngine服务状态
    const serviceStatus = await ytEngineService.checkServiceStatus();
    
    if (!serviceStatus.available) {
      // YTEngine不可用，使用模拟模式
      console.warn('YTEngine service not available, using mock mode');
      
      // 模拟发布过程
      setTimeout(() => {
        publishTask.status = 'publishing';
        setTimeout(() => {
          publishTask.status = 'published';
          publishTask.published_at = new Date().toISOString();
          publishTask.youtube_url = `https://youtube.com/watch?v=${Math.random().toString(36).substring(7)}`;
        }, 3000);
      }, 2000);
      
      return publishTask;
    }

    // YTEngine可用，执行真实上传
    this.executeYTEngineUpload(publishTask, account, request);
    
    return publishTask;
  }

  // 执行YTEngine上传
  private async executeYTEngineUpload(
    publishTask: PublishTask, 
    account: Account, 
    request: CreatePublishRequest
  ): Promise<void> {
    // 立即执行或延迟执行
    const delay = request.publish_time 
      ? new Date(request.publish_time).getTime() - Date.now()
      : request.publish_interval 
      ? request.publish_interval * 60 * 1000
      : 0;

    setTimeout(async () => {
      try {
        publishTask.status = 'publishing';
        
        // 准备上传任务
        const uploadRequest = ytEngineService.createBatchUploadTasks([{
          taskId: publishTask.id,
          profileId: account.bitbrowser_name, // 使用BitBrowser名称作为profileId
          videoPath: request.video_path,
          metadata: {
            title: request.title,
            description: request.description,
            tags: request.tags,
            thumbnail: request.thumbnail_path,
            visibility: 'public',
            category: request.category
          }
        }]);

        // 根据环境决定使用真实上传还是mock上传
        const useMockMode = import.meta.env.VITE_YTENGINE_MOCK === 'true';
        
        if (useMockMode) {
          // 使用Mock API进行测试
          const response = await ytEngineService.mockUpload(uploadRequest);
          
          if (response.success && response.results[0]) {
            publishTask.status = 'published';
            publishTask.published_at = new Date().toISOString();
            publishTask.youtube_url = response.results[0].videoUrl;
            message.success(`视频已成功发布到YouTube: ${response.results[0].videoUrl}`);
          } else {
            throw new Error('Mock上传失败');
          }
        } else {
          // 使用真实API上传
          const response = await ytEngineService.uploadVideos(uploadRequest);
          
          if (response.success && response.data?.results[0]) {
            const result = response.data.results[0];
            
            if (result.status === 'completed') {
              publishTask.status = 'published';
              publishTask.published_at = new Date().toISOString();
              publishTask.youtube_url = result.videoUrl;
              message.success(`视频已成功发布到YouTube: ${result.videoUrl}`);
            } else {
              throw new Error(result.error || '上传失败');
            }
          } else {
            throw new Error(response.error || '上传失败');
          }
        }
      } catch (error: any) {
        publishTask.status = 'failed';
        publishTask.error_message = error.message || '上传失败';
        message.error(`视频发布失败: ${publishTask.error_message}`);
        console.error('YTEngine upload error:', error);
      }
    }, Math.max(delay, 0));
  }

  // 获取发布任务列表
  async getPublishTasks(taskId?: string): Promise<PublishTask[]> {
    await new Promise(resolve => setTimeout(resolve, 500));
    if (taskId) {
      return mockPublishTasks.filter(task => task.task_id === taskId);
    }
    return mockPublishTasks;
  }

  // 获取单个发布任务
  async getPublishTask(id: string): Promise<PublishTask | undefined> {
    await new Promise(resolve => setTimeout(resolve, 300));
    return mockPublishTasks.find(task => task.id === id);
  }

  // 取消发布任务
  async cancelPublishTask(id: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 500));
    const task = mockPublishTasks.find(t => t.id === id);
    if (task && task.status === 'pending') {
      task.status = 'failed';
      task.error_message = '用户取消';
    }
  }
}

export const accountService = new AccountService();