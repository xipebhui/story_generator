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
    search?: string;
  }) {
    return await api.get('/api/auto-publish/publish-configs', { params });
  },

  async getPublishConfig(configId: string) {
    return await api.get(`/api/auto-publish/publish-configs/${configId}`);
  },

  async updatePublishConfig(configId: string, data: any) {
    return await api.put(`/api/auto-publish/publish-configs/${configId}`, data);
  },

  async deletePublishConfig(configId: string) {
    return await api.delete(`/api/auto-publish/publish-configs/${configId}`);
  },

  async togglePublishConfig(configId: string) {
    return await api.patch(`/api/auto-publish/publish-configs/${configId}/toggle`);
  },

  async getConfigTasks(configId: string, params?: {
    status?: string;
    limit?: number;
  }) {
    return await api.get(`/api/auto-publish/publish-configs/${configId}/tasks`, { params });
  },

  async getConfigStats(configId: string, period: string = 'week') {
    return await api.get(`/api/auto-publish/publish-configs/${configId}/stats`, { params: { period } });
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
  },

  async updatePipeline(pipelineId: string, data: any) {
    return await api.put(`/api/auto-publish/pipelines/${pipelineId}`, data);
  },

  async deletePipeline(pipelineId: string) {
    return await api.delete(`/api/auto-publish/pipelines/${pipelineId}`);
  },

  async getPipeline(pipelineId: string) {
    return await api.get(`/api/auto-publish/pipelines/${pipelineId}`);
  },

  // 全局概览
  async getOverviewStats(period: string = 'today') {
    return await api.get('/api/auto-publish/overview/stats', {
      params: { period }
    });
  },

  async getTaskTimeDistribution(period: string = 'today') {
    return await api.get('/api/auto-publish/overview/task-time-distribution', {
      params: { period }
    });
  },

  async getTopAccounts(params: {
    limit?: number;
    period?: string;
    metric?: string;
  } = {}) {
    return await api.get('/api/auto-publish/overview/top-accounts', {
      params: { limit: 5, period: 'today', metric: 'views', ...params }
    });
  },

  async getRecentTasks(limit: number = 10) {
    return await api.get('/api/auto-publish/overview/recent-tasks', {
      params: { limit }
    });
  },

  // Tab 3: 执行记录管理 API
  async getTasks(params: {
    page?: number;
    page_size?: number;
    status?: string;
    config_id?: string;
    account_id?: string;
    start_date?: string;
    end_date?: string;
  } = {}) {
    return await api.get('/api/auto-publish/tasks', { params });
  },

  async getGroupExecutions(configId: string, executionTime: string) {
    return await api.get(`/api/auto-publish/tasks/${configId}/group-executions`, {
      params: { execution_time: executionTime }
    });
  },

  async uploadSubtitle(taskId: string, formData: FormData) {
    return await api.post(`/api/auto-publish/tasks/${taskId}/subtitle`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  async getTaskPerformance(taskId: string) {
    return await api.get(`/api/auto-publish/tasks/${taskId}/performance`);
  },

  async retryTask(taskId: string) {
    return await api.post(`/api/auto-publish/tasks/${taskId}/retry`);
  },

  // Tab 4: 账号组管理增强 API
  async getAccountGroups() {
    return await api.get('/api/auto-publish/account-groups');
  },

  async updateAccountGroup(groupId: string, data: {
    group_name?: string;
    group_type?: string;
    description?: string;
    is_active?: boolean;
  }) {
    return await api.put(`/api/auto-publish/account-groups/${groupId}`, data);
  },

  async deleteAccountGroup(groupId: string) {
    return await api.delete(`/api/auto-publish/account-groups/${groupId}`);
  },

  async addGroupMembers(groupId: string, accountIds: string[], role: string = 'member') {
    return await api.post(`/api/auto-publish/account-groups/${groupId}/members`, {
      account_ids: accountIds,
      role
    });
  },

  async removeGroupMember(groupId: string, accountId: string) {
    return await api.delete(`/api/auto-publish/account-groups/${groupId}/members/${accountId}`);
  },

  async getGroupStats(groupId: string) {
    return await api.get(`/api/auto-publish/account-groups/${groupId}/stats`);
  },

  async getGroupConfigs(groupId: string) {
    return await api.get(`/api/auto-publish/account-groups/${groupId}/configs`);
  },

  async getAccounts() {
    return await api.get('/api/accounts');
  }
};