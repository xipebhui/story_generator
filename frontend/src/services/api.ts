// API基础配置
import axios, { AxiosInstance } from 'axios';
import { message } from 'antd';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          message.error(data.detail || '请求参数错误');
          break;
        case 404:
          message.error(data.detail || '资源不存在');
          break;
        case 500:
          message.error(data.detail || '服务器错误');
          break;
        default:
          message.error(data.detail || '网络错误');
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络');
    } else {
      message.error('请求失败');
    }
    
    return Promise.reject(error);
  }
);

export default api;