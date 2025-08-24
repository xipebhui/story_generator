import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import AppLayout from '@/components/Layout';
import CreateTask from '@/pages/Create';
import TaskList from '@/pages/Tasks';
import TaskDetail from '@/pages/TaskDetail';
import TaskMonitor from '@/pages/Monitor';
import PublishPage from '@/pages/Publish';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/create" replace />,
      },
      {
        path: 'create',
        element: <CreateTask />,
      },
      {
        path: 'tasks',
        element: <TaskList />,
      },
      {
        path: 'task/:taskId',
        element: <TaskDetail />,
      },
      {
        path: 'monitor/:taskId',
        element: <TaskMonitor />,
      },
      {
        path: 'monitor',
        element: <TaskList />, // 默认显示任务列表
      },
      {
        path: 'publish/:taskId',
        element: <PublishPage />,
      },
      {
        path: 'publish',
        element: (
          <div style={{ textAlign: 'center', padding: '100px 0' }}>
            <h2>发布中心</h2>
            <p>功能开发中...</p>
          </div>
        ),
      },
      {
        path: 'publish/history',
        element: (
          <div style={{ textAlign: 'center', padding: '100px 0' }}>
            <h2>发布历史</h2>
            <p>功能开发中...</p>
          </div>
        ),
      },
    ],
  },
]);

export default router;