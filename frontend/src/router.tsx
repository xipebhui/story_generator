import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import AppLayout from '@/components/Layout';
import TaskCenter from '@/pages/TaskCenter';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <TaskCenter />,
      },
      {
        path: 'tasks',
        element: <TaskCenter />,
      },
    ],
  },
]);

export default router;