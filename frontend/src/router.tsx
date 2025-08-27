import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';
import Login from '@/pages/Login';
import AuthGuard from '@/components/AuthGuard';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <Dashboard />
      </AuthGuard>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

export default router;