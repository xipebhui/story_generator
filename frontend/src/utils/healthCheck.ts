// 健康检查工具 - 检测后端服务状态
import { message } from 'antd';

export interface ServiceStatus {
  backend: boolean;
  ytengine: boolean;
  message: string;
}

// 检查后端服务状态
export async function checkBackendHealth(): Promise<boolean> {
  try {
    // health 接口没有 /api 前缀，直接访问 /health
    const response = await fetch('/health');
    return response.ok;
  } catch (error) {
    console.error('后端服务不可用:', error);
    return false;
  }
}

// 检查YTEngine服务状态
export async function checkYTEngineHealth(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:51077/health');
    const data = await response.json();
    return data.status === 'healthy';
  } catch (error) {
    // YTEngine可能不可用，这是正常的
    console.log('YTEngine服务不可用（可选）');
    return false;
  }
}

// 综合健康检查
export async function performHealthCheck(): Promise<ServiceStatus> {
  const backendHealthy = await checkBackendHealth();
  const ytengineHealthy = await checkYTEngineHealth();
  
  let message = '';
  
  if (backendHealthy && ytengineHealthy) {
    message = '所有服务运行正常';
  } else if (backendHealthy && !ytengineHealthy) {
    message = '后端服务正常，YTEngine不可用（将使用模拟模式）';
  } else if (!backendHealthy) {
    message = '后端服务不可用，请检查服务是否已启动';
  }
  
  return {
    backend: backendHealthy,
    ytengine: ytengineHealthy,
    message
  };
}

// 显示服务状态提示
export async function showServiceStatus() {
  const status = await performHealthCheck();
  
  if (status.backend && status.ytengine) {
    message.success('所有服务运行正常');
  } else if (status.backend) {
    message.warning('后端服务正常，YTEngine不可用');
  } else {
    message.error('后端服务不可用，请启动后端服务');
  }
  
  return status;
}