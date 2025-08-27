// 认证相关API服务
import { message } from 'antd';

const API_BASE_URL = '/api';

// 认证相关类型定义
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  invite_code: string;
}

export interface AuthResponse {
  username: string;
  api_key: string;
  message: string;
}

export interface UserInfo {
  username: string;
  api_key: string;
  created_at?: string;
  last_login?: string;
  status?: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// API请求工具函数
async function authRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || '请求失败');
  }

  return data;
}

// 带认证的API请求
async function authenticatedRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('api_key');
  
  if (!token) {
    throw new Error('未登录');
  }

  return authRequest<T>(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    },
  });
}

// 认证服务类
class AuthService {
  // 登录
  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await authRequest<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      
      // 保存认证信息
      this.saveAuth(response.username, response.api_key);
      
      return response;
    } catch (error: any) {
      message.error(error.message || '登录失败');
      throw error;
    }
  }

  // 注册
  async register(username: string, password: string, inviteCode: string): Promise<AuthResponse> {
    try {
      const response = await authRequest<AuthResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          username,
          password,
          invite_code: inviteCode,
        }),
      });
      
      // 保存认证信息
      this.saveAuth(response.username, response.api_key);
      
      return response;
    } catch (error: any) {
      message.error(error.message || '注册失败');
      throw error;
    }
  }

  // 修改密码
  async changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
    try {
      const response = await authenticatedRequest<{ message: string }>('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });
      
      message.success(response.message);
      return response;
    } catch (error: any) {
      message.error(error.message || '修改密码失败');
      throw error;
    }
  }

  // 重置API Key
  async resetApiKey(): Promise<AuthResponse> {
    try {
      const response = await authenticatedRequest<AuthResponse>('/auth/reset-api-key', {
        method: 'POST',
      });
      
      // 更新保存的API Key
      this.saveAuth(response.username, response.api_key);
      
      message.success('API Key已重置');
      return response;
    } catch (error: any) {
      message.error(error.message || '重置API Key失败');
      throw error;
    }
  }

  // 登出
  logout(): void {
    localStorage.removeItem('username');
    localStorage.removeItem('api_key');
    window.location.href = '/login';
  }

  // 检查是否已登录
  isAuthenticated(): boolean {
    return !!localStorage.getItem('api_key');
  }

  // 获取当前用户名
  getCurrentUsername(): string | null {
    return localStorage.getItem('username');
  }
  
  // 兼容旧接口名称
  getUsername(): string {
    return localStorage.getItem('username') || '';
  }

  // 获取API Key
  getApiKey(): string | null {
    return localStorage.getItem('api_key');
  }

  // 获取用户信息
  async getUserInfo(): Promise<UserInfo> {
    try {
      const response = await authenticatedRequest<UserInfo>('/auth/me', {
        method: 'GET',
      });
      return response;
    } catch (error: any) {
      message.error(error.message || '获取用户信息失败');
      throw error;
    }
  }

  // 保存认证信息
  private saveAuth(username: string, apiKey: string): void {
    localStorage.setItem('username', username);
    localStorage.setItem('api_key', apiKey);
  }
}

// 导出单例实例
export const authService = new AuthService();

// 导出认证请求函数，供其他服务使用
export { authenticatedRequest };