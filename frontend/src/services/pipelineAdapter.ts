// Pipeline适配器 - 将前端期望的接口适配到实际后端
import { Task, TaskStatus, TaskResult } from '../types/task';
import { backendPipelineService, taskManager, TaskStatus as BackendTaskStatus, backendAccountService } from './backend';
import api from './api';

class PipelineAdapter {
  private tasks: Map<string, Task> = new Map();
  private results: Map<string, TaskResult> = new Map();
  private pollHandlers: Map<string, () => void> = new Map();

  // 创建新的Pipeline任务
  async createTask(workflow: string, params: any): Promise<Task> {
    try {
      // 根据工作流类型生成合适的参数
      const videoId = params.video_id || this.generateVideoId(workflow);
      const creatorId = params.creator_id || this.generateCreatorId();
      
      // 调用后端API创建任务
      const response = await backendPipelineService.createPipeline({
        videoId,
        creatorId,
        accountName: params.account_name,  // 添加账号名称参数
        gender: this.getGenderFromParams(params),
        duration: params.duration || 60,
        exportVideo: params.export_video || false,
        enableSubtitle: params.enable_subtitle !== false
      });
      
      const task: Task = {
        task_id: response.task_id,
        workflow,
        status: 'pending',
        progress: 0,
        created_at: new Date().toISOString(),
        params: {
          ...params,
          video_id: videoId,
          creator_id: creatorId
        }
      };

      // 保存到内存
      this.tasks.set(response.task_id, task);
      
      // 开始轮询状态
      this.startStatusPolling(response.task_id);
      
      return task;
    } catch (error) {
      console.error('创建任务失败:', error);
      throw error;
    }
  }

  // 获取所有任务
  async listTasks(): Promise<{ tasks: Task[] }> {
    try {
      // 尝试从后端获取历史任务
      const history = await backendPipelineService.getTaskHistory({
        page: 1,
        page_size: 100
      });
      
      // 合并后端任务到本地任务列表
      history.tasks.forEach(backendTask => {
        if (!this.tasks.has(backendTask.task_id)) {
          const task: Task = {
            task_id: backendTask.task_id,
            workflow: this.detectWorkflow(backendTask),
            status: backendTask.status as TaskStatus,
            progress: backendTask.progress,
            current_stage: backendTask.current_stage,
            created_at: backendTask.created_at || backendTask.start_time || new Date().toISOString(),
            completed_at: backendTask.completed_at || backendTask.end_time,
            total_duration: backendTask.total_duration,
            duration: backendTask.duration,
            error_message: backendTask.error_message,
            params: {
              video_id: backendTask.video_id,
              creator_id: backendTask.creator_id
            }
          };
          this.tasks.set(backendTask.task_id, task);
          
          // 如果任务还在运行，开始轮询
          if (task.status === 'running' || task.status === 'pending') {
            this.startStatusPolling(task.task_id);
          }
        }
      });
    } catch (error) {
      console.error('获取历史任务失败:', error);
      // 如果获取失败，继续返回本地任务
    }
    
    // 返回所有任务
    return {
      tasks: Array.from(this.tasks.values()).sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    };
  }

  // 重试失败的任务 - 处理后端创建新ID的情况
  async retryTask(taskId: string): Promise<Task> {
    try {
      // 获取原任务信息
      const originalTask = this.tasks.get(taskId);
      if (!originalTask) {
        throw new Error('任务不存在');
      }
      
      // 获取原任务的account_name参数
      const accountName = originalTask?.params?.account_name;
      
      // 调用后端重试接口，后端会返回新的任务ID
      console.log('[PipelineAdapter] 调用后端重试接口，原任务ID:', taskId);
      const response = await backendPipelineService.retryPipeline(taskId, accountName);
      console.log('[PipelineAdapter] 后端返回新任务:', response);
      
      // 后端返回了新的任务ID，我们需要：
      // 1. 从本地删除原任务
      // 2. 创建新任务并使用新ID
      const newTaskId = response.task_id;
      
      if (newTaskId !== taskId) {
        console.log('[PipelineAdapter] 后端创建了新任务ID:', newTaskId, '原ID:', taskId);
        
        // 删除原任务
        this.tasks.delete(taskId);
        this.results.delete(taskId);
        
        // 停止原任务的轮询
        const stopPolling = this.pollHandlers.get(taskId);
        if (stopPolling) {
          stopPolling();
          this.pollHandlers.delete(taskId);
        }
        
        // 创建新任务对象，保持原任务的参数
        const newTask: Task = {
          ...originalTask,
          task_id: newTaskId,
          status: 'pending',
          progress: 0,
          current_stage: null,
          error_message: undefined,
          completed_at: undefined,
          created_at: new Date().toISOString() // 更新创建时间
        };
        
        // 保存新任务
        this.tasks.set(newTaskId, newTask);
        
        // 开始轮询新任务状态
        this.startStatusPolling(newTaskId);
        
        console.log('[PipelineAdapter] 重试任务成功，新任务ID:', newTaskId);
        return newTask;
      } else {
        // 如果任务ID相同（理论上不应该发生），使用原逻辑
        console.log('[PipelineAdapter] 任务ID未变化，更新原任务状态');
        originalTask.status = 'pending';
        originalTask.progress = 0;
        originalTask.current_stage = null;
        originalTask.error_message = undefined;
        originalTask.completed_at = undefined;
        
        // 重新开始轮询原任务状态
        this.startStatusPolling(taskId);
        
        return originalTask;
      }
    } catch (error) {
      console.error('重试任务失败:', error);
      throw error;
    }
  }

  // 删除任务
  async deleteTask(taskId: string): Promise<void> {
    try {
      // 停止轮询
      const stopPolling = this.pollHandlers.get(taskId);
      if (stopPolling) {
        stopPolling();
        this.pollHandlers.delete(taskId);
      }
      
      // 调用后端删除接口
      await backendPipelineService.deletePipeline(taskId);
      
      // 从本地缓存中删除
      this.tasks.delete(taskId);
      this.results.delete(taskId);
    } catch (error) {
      console.error('删除任务失败:', error);
      throw error;
    }
  }
  
  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<Task | undefined> {
    // 先从本地获取
    let task = this.tasks.get(taskId);
    
    // 如果本地没有，尝试从后端获取
    if (!task) {
      try {
        const backendStatus = await backendPipelineService.getTaskStatus(taskId);
        task = {
          task_id: backendStatus.task_id,
          workflow: this.detectWorkflow(backendStatus),
          status: backendStatus.status as TaskStatus,
          progress: backendStatus.progress,
          current_stage: backendStatus.current_stage,
          created_at: backendStatus.created_at || backendStatus.start_time || new Date().toISOString(),
          completed_at: backendStatus.completed_at || backendStatus.end_time,
          total_duration: (backendStatus as any).total_duration,
          duration: (backendStatus as any).duration,
          error_message: backendStatus.error_message,
          params: {
            video_id: backendStatus.video_id,
            creator_id: backendStatus.creator_id
          }
        };
        this.tasks.set(taskId, task);
        
        // 如果任务还在运行，开始轮询
        if (task.status === 'running' || task.status === 'pending') {
          this.startStatusPolling(taskId);
        }
      } catch (error) {
        console.error('获取任务状态失败:', error);
        return undefined;
      }
    }
    
    return task;
  }

  // 获取任务结果
  async getResult(taskId: string): Promise<TaskResult | undefined> {
    // 先从缓存获取
    let result = this.results.get(taskId);
    
    if (!result) {
      // 从后端获取任务结果 - 使用统一的 api 服务
      try {
        const data = await api.get(`/pipeline/result/${taskId}`);
        
        result = {
          task_id: data.task_id,
          status: data.status,
          video_path: data.video_path || '',
          draft_path: data.draft_path || '',
          audio_path: data.audio_path || '',
          story_path: data.story_path || '',
          preview_url: data.preview_url || '',
          youtube_metadata: data.youtube_metadata,
          error: data.error
        };
        this.results.set(taskId, result);
      } catch (error) {
        console.error('获取任务结果失败:', error);
      }
    }
    
    return result;
  }

  // 取消任务
  async cancelTask(taskId: string): Promise<void> {
    // 停止轮询
    const stopPolling = this.pollHandlers.get(taskId);
    if (stopPolling) {
      stopPolling();
      this.pollHandlers.delete(taskId);
    }
    
    // 更新本地状态
    const task = this.tasks.get(taskId);
    if (task) {
      task.status = 'cancelled';
    }
  }

  // 发布视频
  async publishVideo(taskId: string, options?: {
    accountIds?: string[];
    title?: string;
    description?: string;
    tags?: string[];
  }): Promise<any> {
    return taskManager.publishVideo(taskId, {
      accountIds: options?.accountIds,
      title: options?.title,
      description: options?.description,
      tags: options?.tags,
      privacy: 'private'
    });
  }

  // 获取YouTube账号列表
  async getAccounts(): Promise<any[]> {
    return backendAccountService.getAccounts();
  }

  // 批量发布
  async batchPublish(taskId: string, accountCount: number = 3): Promise<any> {
    return taskManager.batchPublishVideo(taskId, accountCount);
  }

  // 私有方法：开始轮询任务状态
  private startStatusPolling(taskId: string) {
    // 如果已经在轮询，先停止
    const existingHandler = this.pollHandlers.get(taskId);
    if (existingHandler) {
      existingHandler();
    }
    
    const task = this.tasks.get(taskId);
    if (!task) return;

    // 使用backend service的轮询功能
    const stopPolling = backendPipelineService.pollTaskStatus(
      taskId,
      (status: BackendTaskStatus) => {
        // 更新任务状态 - 直接使用后端状态
        task.status = status.status as TaskStatus;
        task.progress = status.progress;
        task.current_stage = status.current_stage || '处理中';
        
        // 如果有阶段信息，更新
        if (status.stages) {
          task.stages = Object.entries(status.stages).map(([key, stage]) => ({
            name: this.translateStageName(key),
            status: stage.status,
            start_time: stage.start_time,
            end_time: stage.end_time
          }));
        }
        
        // 任务完成时的处理
        if (status.status === 'completed') {
          task.status = status.status;
          task.progress = 100;
          task.completed_at = status.completed_at || status.end_time || new Date().toISOString();
          task.total_duration = (status as any).total_duration;
          task.duration = (status as any).duration;
          
          // 保存结果
          if (status.result) {
            const result: TaskResult = {
              video_path: status.result.video_path || '',
              draft_path: status.result.draft_path || '',
              audio_path: status.result.audio_path || '',
              preview_url: `/api/preview/${taskId}`,
              youtube_metadata: status.result.youtube_metadata || {
                title: `自动生成的视频 - ${new Date().toLocaleDateString()}`,
                description: '这是通过AI自动生成的视频内容',
                tags: ['AI生成', '自动创作']
              }
            };
            this.results.set(taskId, result);
          }
          
          // 停止轮询
          this.pollHandlers.delete(taskId);
        }
        
        // 任务失败时的处理
        if (status.status === 'failed') {
          task.status = status.status;
          task.error_message = status.error_message;
          
          // 停止轮询
          this.pollHandlers.delete(taskId);
        }
      },
      10000 // 10秒轮询一次
    );
    
    this.pollHandlers.set(taskId, stopPolling);
  }


  // 翻译阶段名称
  private translateStageName(stageName: string): string {
    const stageNames: { [key: string]: string } = {
      'story_generation': '故事生成',
      'voice_generation': '语音生成',
      'draft_generation': '草稿生成',
      'video_export': '视频导出',
      'subtitle_generation': '字幕生成',
      'image_generation': '图像生成'
    };
    return stageNames[stageName] || stageName;
  }

  // 生成视频ID
  private generateVideoId(workflow: string): string {
    const prefix = workflow.includes('故事') ? 'story' : 
                   workflow.includes('漫画') ? 'comic' : 
                   workflow.includes('解压') ? 'asmr' : 'vid';
    return `${prefix}_${Date.now()}`;
  }

  // 生成创作者ID
  private generateCreatorId(): string {
    return `creator_${Date.now().toString(36)}`;
  }

  // 从参数获取性别设置
  private getGenderFromParams(params: any): 1 | 2 {
    if (params.voice_gender === 'female' || params.gender === 2) return 2;
    return 1;
  }

  // 检测工作流类型
  private detectWorkflow(task: any): string {
    if (task.video_id?.includes('story')) return 'YouTube故事';
    if (task.video_id?.includes('comic')) return 'YouTube漫画';
    if (task.video_id?.includes('asmr')) return 'YouTube解压';
    return '视频生成';
  }

  // 停止所有轮询
  stopAllPolling() {
    this.pollHandlers.forEach(stop => stop());
    this.pollHandlers.clear();
  }
}

// 导出单例实例
export const pipelineAdapter = new PipelineAdapter();