import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../../services/auth';

interface AuthGuardProps {
  children: React.ReactNode;
}

// 认证守卫组件
const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();

  if (!isAuthenticated) {
    // 保存当前路径，登录后可以重定向回来
    const from = location.pathname + location.search;
    return <Navigate to={`/login?from=${encodeURIComponent(from)}`} replace />;
  }

  return <>{children}</>;
};

export default AuthGuard;