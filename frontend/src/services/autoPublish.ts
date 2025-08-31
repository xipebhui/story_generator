import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:51082',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('api_key');
    if (apiKey) {
      config.headers['Authorization'] = `Bearer ${apiKey}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 账号组管理
export const autoPublishService = {
  // 账号组管理
  async createAccountGroup(data: {
    group_name: string;
    group_type: string;
    description?: string;
    account_ids: string[];
  }) {
    return await api.post('/api/auto-publish/account-groups', data);
  },

  async listAccountGroups(params?: {
    group_type?: string;
    is_active?: boolean;
  }) {
    return await api.get('/api/auto-publish/account-groups', { params });
  },

  async deleteAccountGroup(groupId: string) {
    return await api.delete(`/api/auto-publish/account-groups/${groupId}`);
  },

  // 发布配置管理
  async createPublishConfig(data: {
    config_name: string;
    group_id: string;
    pipeline_id: string;
    trigger_type: string;
    trigger_config: any;
    strategy_id?: string;
    priority?: number;
  }) {
    return await api.post('/api/auto-publish/publish-configs', data);
  },

  async listPublishConfigs(params?: {
    group_id?: string;
    pipeline_id?: string;
    is_active?: boolean;
  }) {
    return await api.get('/api/auto-publish/publish-configs', { params });
  },

  async updatePublishConfig(configId: string, data: any) {
    return await api.put(`/api/auto-publish/publish-configs/${configId}`, data);
  },

  async deletePublishConfig(configId: string) {
    return await api.delete(`/api/auto-publish/publish-configs/${configId}`);
  },

  // 调度管理
  async generateScheduleSlots(data: {
    config_id: string;
    target_date: string;
    start_hour: number;
    end_hour: number;
    strategy?: string;
  }) {
    return await api.post('/api/auto-publish/schedule/generate-slots', data);
  },

  async getScheduleSlots(configId: string, targetDate: string, status?: string) {
    return await api.get(`/api/auto-publish/schedule/slots/${configId}`, {
      params: { target_date: targetDate, status }
    });
  },

  // 执行器控制
  async startExecutor() {
    return await api.post('/api/auto-publish/executor/start');
  },

  async stopExecutor() {
    return await api.post('/api/auto-publish/executor/stop');
  },

  async getTaskStatus(taskId: string) {
    return await api.get(`/api/auto-publish/executor/task/${taskId}`);
  },

  // 策略管理
  async createStrategy(data: {
    strategy_name: string;
    strategy_type: string;
    parameters: any;
    description?: string;
    start_date?: string;
    end_date?: string;
  }) {
    return await api.post('/api/auto-publish/strategies', data);
  },

  async listStrategies() {
    return await api.get('/api/auto-publish/strategies');
  },

  async assignStrategy(data: {
    strategy_id: string;
    group_id: string;
    variant_name: string;
    variant_config?: any;
    weight?: number;
    is_control?: boolean;
  }) {
    return await api.post('/api/auto-publish/strategies/assign', data);
  },

  async getStrategyReport(strategyId: string) {
    return await api.get(`/api/auto-publish/strategies/${strategyId}/report`);
  },

  // 平台监控
  async createMonitor(data: {
    platform: string;
    monitor_type: string;
    target_identifier: string;
    check_interval?: number;
    config?: any;
  }) {
    return await api.post('/api/auto-publish/monitors', data);
  },

  async fetchMonitoredContent(params: {
    platform: string;
    monitor_type: string;
    target: string;
    max_results?: number;
  }) {
    return await api.get('/api/auto-publish/monitors/fetch', { params });
  },

  async startMonitoring() {
    return await api.post('/api/auto-publish/monitors/start');
  },

  // Pipeline注册表
  async listPipelines(params?: {
    pipeline_type?: string;
    platform?: string;
    status?: string;
  }) {
    return await api.get('/api/auto-publish/pipelines', { params });
  },

  async registerPipeline(data: {
    pipeline_id: string;
    pipeline_name: string;
    pipeline_type: string;
    pipeline_class: string;
    config_schema: any;
    supported_platforms?: string[];
    version?: string;
  }) {
    return await api.post('/api/auto-publish/pipelines/register', data);
  }
};