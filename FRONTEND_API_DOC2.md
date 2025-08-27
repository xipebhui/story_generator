# 前端API对接文档

## 基础配置

### API服务地址
- 开发环境：`http://localhost:51082`
- 生产环境：根据实际部署地址

### 请求头配置
```javascript
// 基础请求头
const headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer {api_key}' // 登录后获取的API Key
}
```

## 一、认证相关接口

### 1.1 用户注册
```javascript
POST /api/auth/register

// 请求
{
  "username": "testuser",      // 用户名（必填）
  "password": "password123",    // 密码（必填）
  "invite_code": "15361578057"  // 邀请码（必填，固定值）
}

// 成功响应 200
{
  "username": "testuser",
  "api_key": "550e8400-e29b-41d4-a716-446655440000",
  "message": "注册成功"
}

// 错误响应
// 400 - 邀请码错误或用户名已存在
{
  "detail": "无效的邀请码" // 或 "用户名已存在"
}
```

### 1.2 用户登录
```javascript
POST /api/auth/login

// 请求
{
  "username": "testuser",    // 用户名
  "password": "password123"   // 密码
}

// 成功响应 200
{
  "username": "testuser",
  "api_key": "550e8400-e29b-41d4-a716-446655440000",
  "message": "登录成功"
}

// 错误响应
// 401 - 认证失败
{
  "detail": "用户名或密码错误"
}
```

### 1.3 修改密码
```javascript
POST /api/auth/change-password
Headers: Authorization: Bearer {api_key}

// 请求
{
  "old_password": "password123",    // 旧密码
  "new_password": "newpassword456"  // 新密码
}

// 成功响应 200
{
  "message": "密码修改成功"
}

// 错误响应
// 400 - 旧密码错误
{
  "detail": "旧密码错误"
}
```

### 1.4 重置API Key
```javascript
POST /api/auth/reset-api-key
Headers: Authorization: Bearer {api_key}

// 无需请求体

// 成功响应 200
{
  "username": "testuser",
  "api_key": "新生成的-api-key",
  "message": "API Key重置成功"
}
```

## 二、Pipeline任务接口

### 2.1 创建并运行Pipeline任务
```javascript
POST /api/pipeline/run
Headers: Authorization: Bearer {api_key}

// 请求
{
  "video_id": "dQw4w9WgXcQ",        // YouTube视频ID（必填）
  "creator_id": "user123",           // 创建者ID（必填）
  "account_name": "MyYouTube",       // 发布账号名称（可选）
  "gender": 1,                       // 配音性别：0男1女（可选，默认1）
  "duration": 60,                    // 每张图片时长秒数（可选，默认60）
  "image_dir": "/path/to/images",    // 图片目录路径（可选）
  "export_video": true,              // 是否导出视频（可选，默认false）
  "enable_subtitle": true            // 是否生成字幕（可选，默认true）
}

// 成功响应 200
{
  "task_id": "user123_MyYouTube_dQw4w9WgXcQ_a1b2c3d4",
  "status": "pending",
  "message": "任务已创建，正在后台执行"
}
```

### 2.2 查询任务状态
```javascript
GET /api/pipeline/status/{task_id}
Headers: Authorization: Bearer {api_key}

// 成功响应 200
{
  "task_id": "user123_MyYouTube_dQw4w9WgXcQ_a1b2c3d4",
  "status": "running",              // pending/running/completed/failed
  "current_stage": "generating_audio",  // 当前执行阶段
  "progress": {
    "transcript": "completed",
    "story": "completed", 
    "image": "completed",
    "audio": "running",
    "video": "pending"
  },
  "created_at": "2024-01-15T10:30:00",
  "error": null                     // 错误信息（如果有）
}
```

### 2.3 获取任务结果
```javascript
GET /api/pipeline/result/{task_id}
Headers: Authorization: Bearer {api_key}

// 成功响应 200（任务完成时）
{
  "task_id": "user123_MyYouTube_dQw4w9WgXcQ_a1b2c3d4",
  "status": "completed",
  "result": {
    "video_path": "/path/to/video.mp4",
    "draft_path": "/path/to/draft.json",
    "preview_url": "http://example.com/preview/video.mp4",
    "youtube_metadata": {
      "title": "视频标题",
      "description": "视频描述",
      "tags": ["tag1", "tag2"]
    }
  }
}

// 错误响应 404
{
  "detail": "任务不存在"
}
```

### 2.4 查询历史任务
```javascript
GET /api/pipeline/history
Headers: Authorization: Bearer {api_key}

// 查询参数
?creator_id=user123      // 创建者ID（可选）
&status=completed        // 状态筛选（可选）
&start_date=2024-01-01  // 开始日期（可选）
&end_date=2024-01-31    // 结束日期（可选）
&limit=20               // 返回数量（默认100）
&offset=0               // 分页偏移（默认0）

// 成功响应 200
{
  "tasks": [
    {
      "task_id": "...",
      "video_id": "...",
      "creator_id": "...",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00",
      "completed_at": "2024-01-15T10:45:00",
      "youtube_metadata": {...}
    }
  ],
  "total": 50,
  "offset": 0,
  "limit": 20
}
```

### 2.5 手动上传字幕文件

```javascript
POST /api/pipeline/upload-subtitle
Headers: Authorization: Bearer {api_key}
Content-Type: multipart/form-data

// FormData请求
FormData:
  task_id: "task_123"          // 任务ID（必填）
  file: [File Object]          // 字幕文本文件（.txt格式）

// 成功响应 200
{
  "message": "字幕文件上传成功",
  "task_id": "task_123",
  "video_id": "dQw4w9WgXcQ",
  "subtitle_path": "/absolute/path/to/subtitle.txt",
  "subtitle_length": 1234       // 字幕文本长度
}

// 错误响应
// 404 - 任务不存在
{
  "detail": "任务不存在"
}

// 使用说明：
// 1. 当YouTube字幕获取不稳定时，可手动上传字幕文件
// 2. 上传的字幕会保存到 cache/{video_id}/raw/subtitle.txt
// 3. Pipeline执行时会优先使用手动上传的字幕
// 4. 字幕文件应为纯文本格式（.txt）
```

### 2.6 删除任务
```javascript
DELETE /api/pipeline/task/{task_id}
Headers: Authorization: Bearer {api_key}

// 成功响应 200
{
  "message": "任务已删除"
}

// 错误响应 404
{
  "detail": "任务不存在"
}
```

## 三、发布相关接口

### 3.1 上传缩略图
```javascript
POST /api/publish/upload-thumbnail
Headers: Authorization: Bearer {api_key}
Content-Type: multipart/form-data

// FormData请求
FormData:
  task_id: "task_123"          // 任务ID
  file: [File Object]          // 图片文件

// 成功响应 200
{
  "thumbnail_path": "/absolute/path/to/thumbnail.jpg",
  "relative_path": "thumbnails/task_123.jpg",
  "message": "缩略图上传成功"
}
```

### 3.2 创建发布任务
```javascript
POST /api/publish/create
Headers: Authorization: Bearer {api_key}

// 请求
{
  "task_id": "task_123",              // Pipeline任务ID（必填）
  "account_id": "youtube_account_1",   // YouTube账号ID（必填）
  "video_title": "视频标题",           // 视频标题（必填）
  "video_description": "视频描述",     // 视频描述（可选）
  "video_tags": ["tag1", "tag2"],     // 标签列表（可选）
  "thumbnail_path": "/path/to/thumb",  // 缩略图路径（可选）
  "privacy_status": "public"          // public/private/unlisted（默认public）
}

// 成功响应 200
{
  "publish_id": "pub_123456",
  "message": "发布任务创建成功"
}
```

### 3.3 执行发布
```javascript
POST /api/publish/execute/{publish_id}
Headers: Authorization: Bearer {api_key}

// 无需请求体

// 成功响应 200
{
  "message": "发布任务已启动",
  "publish_id": "pub_123456"
}
```

### 3.4 查询发布历史
```javascript
GET /api/publish/history
Headers: Authorization: Bearer {api_key}

// 查询参数
?task_id=task_123        // Pipeline任务ID（可选）
&account_id=account_1    // 账号ID（可选）
&status=success         // 状态：pending/uploading/success/failed（可选）
&limit=20               // 返回数量（默认100）

// 成功响应 200
[
  {
    "publish_id": "pub_123456",
    "task_id": "task_123",
    "account_id": "account_1",
    "video_title": "视频标题",
    "status": "success",
    "youtube_video_id": "abc123",
    "youtube_video_url": "https://youtube.com/watch?v=abc123",
    "created_at": "2024-01-15T10:30:00",
    "upload_completed_at": "2024-01-15T10:45:00"
  }
]
```

## 四、统计接口

### 4.1 获取统计信息
```javascript
GET /api/pipeline/statistics
Headers: Authorization: Bearer {api_key}

// 查询参数
?creator_id=user123      // 创建者ID（可选）

// 成功响应 200
{
  "pipeline": {
    "total": 100,           // 总任务数
    "completed": 80,        // 完成数
    "failed": 10,          // 失败数
    "running": 5,          // 运行中
    "success_rate": 80.0   // 成功率
  },
  "publish": {
    "total": 50,           // 总发布数
    "success": 45,         // 成功数
    "failed": 5,           // 失败数
    "success_rate": 90.0   // 成功率
  },
  "avg_duration_seconds": 300.5  // 平均耗时
}
```

## 五、前端集成示例

### 5.1 Axios封装示例
```javascript
import axios from 'axios';

// API基础配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:51082';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器 - 添加认证token
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('api_key');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// 响应拦截器 - 处理认证错误
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      // Token无效，跳转到登录页
      localStorage.removeItem('api_key');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API方法封装
export const authAPI = {
  // 登录
  login: (username, password) => 
    apiClient.post('/api/auth/login', { username, password }),
  
  // 注册
  register: (username, password, inviteCode) =>
    apiClient.post('/api/auth/register', {
      username,
      password,
      invite_code: inviteCode
    }),
  
  // 修改密码
  changePassword: (oldPassword, newPassword) =>
    apiClient.post('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    })
};

export const pipelineAPI = {
  // 运行任务
  runPipeline: (params) =>
    apiClient.post('/api/pipeline/run', params),
  
  // 获取状态
  getStatus: (taskId) =>
    apiClient.get(`/api/pipeline/status/${taskId}`),
  
  // 获取结果
  getResult: (taskId) =>
    apiClient.get(`/api/pipeline/result/${taskId}`),
  
  // 获取历史
  getHistory: (params) =>
    apiClient.get('/api/pipeline/history', { params }),
  
  // 删除任务
  deleteTask: (taskId) =>
    apiClient.delete(`/api/pipeline/task/${taskId}`),
  
  // 上传字幕文件
  uploadSubtitle: (taskId, file) => {
    const formData = new FormData();
    formData.append('task_id', taskId);
    formData.append('file', file);
    return apiClient.post('/api/pipeline/upload-subtitle', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
};

export default apiClient;
```

### 5.2 React组件示例
```jsx
import React, { useState, useEffect } from 'react';
import { authAPI, pipelineAPI } from './api';

// 登录组件
function LoginForm() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.login(
        formData.username, 
        formData.password
      );
      // 保存API Key
      localStorage.setItem('api_key', response.api_key);
      localStorage.setItem('username', response.username);
      // 跳转到主页
      window.location.href = '/dashboard';
    } catch (error) {
      alert('登录失败：' + error.response?.data?.detail);
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        placeholder="用户名"
        value={formData.username}
        onChange={e => setFormData({...formData, username: e.target.value})}
        required
      />
      <input
        type="password"
        placeholder="密码"
        value={formData.password}
        onChange={e => setFormData({...formData, password: e.target.value})}
        required
      />
      <button type="submit">登录</button>
    </form>
  );
}

// 字幕上传组件
function SubtitleUploader({ taskId }) {
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      const response = await pipelineAPI.uploadSubtitle(taskId, file);
      alert(`字幕上传成功！长度: ${response.subtitle_length} 字符`);
    } catch (error) {
      alert('字幕上传失败：' + error.response?.data?.detail);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept=".txt"
        onChange={handleFileUpload}
        disabled={uploading}
      />
      {uploading && <p>上传中...</p>}
    </div>
  );
}

// 任务列表组件
function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await pipelineAPI.getHistory({
        limit: 20,
        offset: 0
      });
      setTasks(response.tasks);
    } catch (error) {
      console.error('获取任务列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    try {
      const response = await pipelineAPI.runPipeline({
        video_id: 'test_video_id',
        creator_id: localStorage.getItem('username'),
        gender: 1,
        duration: 60,
        export_video: true,
        enable_subtitle: true
      });
      alert(`任务创建成功：${response.task_id}`);
      fetchTasks(); // 刷新列表
    } catch (error) {
      alert('创建任务失败');
    }
  };

  return (
    <div>
      <button onClick={handleRunPipeline}>创建新任务</button>
      {loading ? (
        <p>加载中...</p>
      ) : (
        <ul>
          {tasks.map(task => (
            <li key={task.task_id}>
              {task.task_id} - {task.status} - {task.created_at}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## 六、错误处理

### HTTP状态码说明
- **200** - 成功
- **400** - 请求参数错误
- **401** - 未授权（需要登录或Token无效）
- **403** - 禁止访问（用户被禁用）
- **404** - 资源不存在
- **422** - 请求格式错误
- **500** - 服务器内部错误

### 通用错误响应格式
```json
{
  "detail": "错误信息描述"
}
```

### 认证相关注意事项
1. **API Key存储**：建议存储在 `localStorage` 或 `sessionStorage`
2. **Token格式**：必须使用 `Bearer {api_key}` 格式
3. **认证失败处理**：收到401错误时应引导用户重新登录
4. **CORS配置**：确保前端域名在后端CORS配置中

## 七、开发调试建议

### 1. 使用Postman测试
- 导入API文档到Postman
- 设置环境变量管理API Key
- 使用Collection Runner批量测试

### 2. 浏览器调试
```javascript
// 在浏览器控制台测试API
fetch('http://localhost:51082/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'test',
    password: '123456'
  })
}).then(r => r.json()).then(console.log)
```

### 3. 网络请求监控
- 使用Chrome DevTools的Network面板
- 检查请求头是否包含Authorization
- 查看响应状态码和错误信息

## 八、生产环境注意事项

1. **使用HTTPS**：生产环境必须使用HTTPS保护API Key
2. **错误日志**：记录所有API错误用于问题排查
3. **请求限流**：考虑添加请求频率限制
4. **Token刷新**：定期使用重置API Key接口更新Token
5. **超时处理**：设置合理的请求超时时间（建议30秒）