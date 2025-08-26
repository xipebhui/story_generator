# 前端适配后端API指南

## 概述

本文档指导前端开发者如何修改现有前端代码以适配实际的后端API服务。后端服务运行在 `http://localhost:51082`。

## 主要变更点

### 1. API基础URL变更
- **原前端期望**: `/api/v1/`
- **实际后端**: `/api/`
- **修改方式**: 全局替换所有API请求的基础路径

```javascript
// 原来
const API_BASE = 'http://localhost:51082/api/v1';

// 修改为
const API_BASE = 'http://localhost:51082/api';
```

### 2. Pipeline创建接口完全重构

#### 2.1 接口路径
- **原路径**: `POST /api/v1/pipelines`
- **新路径**: `POST /api/pipeline/run`

#### 2.2 请求参数变化

**原前端请求结构**:
```json
{
  "name": "string",
  "type": "story_generation",
  "config": {
    "source_video_url": "string",
    "duration": 120,
    "voice_config": {},
    "subtitle_config": {}
  }
}
```

**实际后端需要的请求结构**:
```json
{
  "video_id": "string",        // YouTube视频ID
  "creator_id": "string",      // 创作者ID
  "account_name": "string",    // 账号名称（可选，用于生成task_id）
  "gender": 1,                 // 1=男声, 2=女声
  "duration": 60,              // 每张图片显示时长(秒)
  "export_video": false,       // 是否导出视频
  "enable_subtitle": true      // 是否生成字幕
}
```

**注意**: `account_name` 是可选参数。如果提供，task_id会包含账号名称，格式为：`{creator_id}_{account_name}_{video_id}_{uuid}`；如果不提供，格式为：`{creator_id}_{video_id}_{uuid}`。

**前端修改示例**:
```javascript
// 原来的创建Pipeline函数
async function createPipeline(name, videoUrl, duration, voiceConfig) {
  const response = await fetch(`${API_BASE}/pipelines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: name,
      type: 'story_generation',
      config: {
        source_video_url: videoUrl,
        duration: duration,
        voice_config: voiceConfig
      }
    })
  });
  return response.json();
}

// 修改为
async function createPipeline(videoId, creatorId, accountName, gender, imageDuration, exportVideo = false, enableSubtitle = true) {
  const requestBody = {
    video_id: videoId,
    creator_id: creatorId,
    gender: gender,
    duration: imageDuration,  // 注意：这是图片显示时长，不是视频总时长
    export_video: exportVideo,
    enable_subtitle: enableSubtitle
  };
  
  // account_name 是可选的
  if (accountName) {
    requestBody.account_name = accountName;
  }
  
  const response = await fetch(`${API_BASE}/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  });
  return response.json();
}
```

#### 2.3 响应结构变化

**原前端期望响应**:
```json
{
  "pipeline_id": "uuid",
  "name": "string",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00"
}
```

**实际后端响应**:
```json
{
  "task_id": "creatorId_accountName_videoId_timestamp",  // 或 "creatorId_videoId_timestamp"
  "status": "pending",
  "message": "Pipeline任务已创建并开始执行"
}
```

**前端处理响应的修改**:
```javascript
// 原来
function handlePipelineCreated(response) {
  const pipelineId = response.pipeline_id;
  const status = response.status;
  // ...
}

// 修改为
function handlePipelineCreated(response) {
  const taskId = response.task_id;  // 使用task_id而不是pipeline_id
  const status = response.status;
  // 注意：没有name和created_at字段
  // task_id可能包含account_name信息
  // ...
}
```

### 3. 查询任务状态

#### 3.1 单个任务状态查询
- **原路径**: `GET /api/v1/pipelines/{pipeline_id}/status`
- **新路径**: `GET /api/pipeline/status/{task_id}`

**响应结构完全不同**:

**实际后端响应**:
```json
{
  "task_id": "string",
  "video_id": "string",
  "creator_id": "string",
  "status": "pending|processing|completed|failed",
  "current_stage": "string",
  "progress": 0-100,
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T00:00:00",
  "error_message": null,
  "stages": {
    "story_generation": {
      "status": "completed",
      "start_time": "...",
      "end_time": "..."
    },
    "voice_generation": {
      "status": "processing",
      "start_time": "..."
    }
  }
}
```

#### 3.2 任务历史查询
- **新接口**: `GET /api/pipeline/history`
- **查询参数**:
  - `page`: 页码（默认1）
  - `page_size`: 每页数量（默认10，最大100）
  - `status`: 筛选状态（可选）
  - `creator_id`: 筛选创作者（可选）

**前端实现示例**:
```javascript
async function getTaskHistory(page = 1, pageSize = 10, status = null) {
  const params = new URLSearchParams({
    page: page,
    page_size: pageSize
  });
  if (status) params.append('status', status);
  
  const response = await fetch(`${API_BASE}/pipeline/history?${params}`);
  return response.json();
}
```

### 4. 缺失的功能处理

以下是前端期望但后端**不支持**的功能，需要移除或禁用：

#### 4.1 WebSocket实时更新
- **移除**: 所有WebSocket连接代码
- **替代方案**: 使用轮询方式查询任务状态

```javascript
// 使用轮询替代WebSocket
function pollTaskStatus(taskId, interval = 5000) {
  const intervalId = setInterval(async () => {
    const status = await getTaskStatus(taskId);
    updateUI(status);
    
    if (status.status === 'completed' || status.status === 'failed') {
      clearInterval(intervalId);
    }
  }, interval);
  
  return intervalId;
}
```

#### 4.2 Pipeline更新和删除
- **不支持**: `PUT /api/v1/pipelines/{id}` 和 `DELETE /api/v1/pipelines/{id}`
- **处理**: 隐藏或禁用编辑和删除按钮

```javascript
// 在UI中禁用这些功能
document.querySelector('.edit-pipeline-btn').disabled = true;
document.querySelector('.delete-pipeline-btn').style.display = 'none';
```

#### 4.3 文件管理接口
- **不支持**: 所有 `/api/v1/files/*` 接口
- **处理**: 文件通过其他方式处理，不通过API上传

### 5. 新增功能集成

#### 5.1 YouTube账号管理

**获取账号列表**:
```javascript
async function getYouTubeAccounts() {
  const response = await fetch(`${API_BASE}/accounts`);
  const data = await response.json();
  return data.accounts;  // 包含15个预设账号
}
```

#### 5.2 视频发布功能

**创建发布任务**:
```javascript
async function publishVideo(taskId, accountIds, title, description, tags) {
  const response = await fetch(`${API_BASE}/publish/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      account_ids: accountIds,  // 数组，可选择多个账号
      video_title: title,
      video_description: description,
      video_tags: tags,  // 数组
      privacy_status: "private"  // "private", "unlisted", "public"
    })
  });
  return response.json();
}
```

**批量发布**:
```javascript
async function batchPublish(taskId, accountCount = 3) {
  const response = await fetch(`${API_BASE}/publish/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      account_count: accountCount,
      video_metadata: {
        title: "默认标题",
        description: "默认描述",
        tags: ["tag1", "tag2"]
      }
    })
  });
  return response.json();
}
```

### 6. 数据结构映射

#### 6.1 任务ID映射
```javascript
// 前端使用pipeline_id的地方全部改为task_id
const taskIdMap = {
  'pipeline_id': 'task_id',
  'pipeline': 'task',
  'pipelines': 'tasks'
};
```

#### 6.2 状态值映射
```javascript
const statusMap = {
  // 前端状态 -> 后端状态
  'running': 'processing',
  'success': 'completed',
  'error': 'failed',
  'waiting': 'pending'
};
```

### 7. 错误处理

后端错误响应格式:
```json
{
  "detail": "错误信息"
}
```

前端错误处理:
```javascript
async function apiRequest(url, options) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '请求失败');
    }
    return response.json();
  } catch (error) {
    console.error('API请求错误:', error);
    // 显示错误提示
    showErrorMessage(error.message);
    throw error;
  }
}
```

### 8. 完整的API调用示例

#### 8.1 创建并监控Pipeline任务

```javascript
class PipelineManager {
  constructor() {
    this.apiBase = 'http://localhost:51082/api';
    this.pollInterval = 5000;  // 5秒轮询一次
  }

  // 创建Pipeline任务
  async createPipeline(videoId, creatorId, accountName = null) {
    const requestBody = {
      video_id: videoId,
      creator_id: creatorId,
      gender: 1,  // 默认男声
      duration: 60,  // 默认60秒
      export_video: false,
      enable_subtitle: true
    };
    
    // 如果提供了账号名称，添加到请求中
    if (accountName) {
      requestBody.account_name = accountName;
    }
    
    const response = await fetch(`${this.apiBase}/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error('创建任务失败');
    }
    
    const data = await response.json();
    
    // 开始轮询状态
    this.pollStatus(data.task_id);
    
    return data;
  }

  // 轮询任务状态
  pollStatus(taskId) {
    const intervalId = setInterval(async () => {
      try {
        const status = await this.getTaskStatus(taskId);
        this.updateUI(status);
        
        if (status.status === 'completed') {
          clearInterval(intervalId);
          this.onTaskCompleted(status);
        } else if (status.status === 'failed') {
          clearInterval(intervalId);
          this.onTaskFailed(status);
        }
      } catch (error) {
        console.error('状态查询失败:', error);
      }
    }, this.pollInterval);
    
    return intervalId;
  }

  // 获取任务状态
  async getTaskStatus(taskId) {
    const response = await fetch(`${this.apiBase}/pipeline/status/${taskId}`);
    if (!response.ok) {
      throw new Error('获取状态失败');
    }
    return response.json();
  }

  // 更新UI
  updateUI(status) {
    // 更新进度条
    const progressBar = document.querySelector('#progress-bar');
    if (progressBar) {
      progressBar.style.width = `${status.progress}%`;
    }
    
    // 更新状态文本
    const statusText = document.querySelector('#status-text');
    if (statusText) {
      statusText.textContent = `当前阶段: ${status.current_stage || '准备中'}`;
    }
    
    // 更新阶段信息
    if (status.stages) {
      this.updateStageInfo(status.stages);
    }
  }

  // 更新阶段信息
  updateStageInfo(stages) {
    const stageNames = {
      'story_generation': '故事生成',
      'voice_generation': '语音生成',
      'draft_generation': '草稿生成',
      'video_export': '视频导出'
    };
    
    Object.entries(stages).forEach(([stage, info]) => {
      const stageElement = document.querySelector(`#stage-${stage}`);
      if (stageElement) {
        stageElement.className = `stage-${info.status}`;
        stageElement.textContent = `${stageNames[stage] || stage}: ${info.status}`;
      }
    });
  }

  // 任务完成处理
  async onTaskCompleted(status) {
    console.log('任务完成:', status);
    
    // 询问是否发布
    if (confirm('任务已完成，是否发布到YouTube？')) {
      await this.publishToYouTube(status.task_id);
    }
  }

  // 任务失败处理
  onTaskFailed(status) {
    console.error('任务失败:', status);
    alert(`任务失败: ${status.error_message || '未知错误'}`);
  }

  // 发布到YouTube
  async publishToYouTube(taskId) {
    // 获取可用账号
    const accountsResponse = await fetch(`${this.apiBase}/accounts`);
    const accountsData = await accountsResponse.json();
    
    // 选择前3个账号
    const selectedAccounts = accountsData.accounts.slice(0, 3).map(a => a.account_id);
    
    // 创建发布任务
    const publishResponse = await fetch(`${this.apiBase}/publish/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        account_ids: selectedAccounts,
        video_title: `生成的视频 - ${new Date().toLocaleDateString()}`,
        video_description: '这是通过AI生成的视频内容',
        video_tags: ['AI生成', '自动创作'],
        privacy_status: 'private'
      })
    });
    
    if (publishResponse.ok) {
      const publishData = await publishResponse.json();
      alert('发布任务已创建');
      console.log('发布结果:', publishData);
    } else {
      alert('发布失败');
    }
  }
}

// 使用示例
const pipelineManager = new PipelineManager();

// 创建任务（带账号名称）
document.querySelector('#create-btn').addEventListener('click', async () => {
  const videoId = document.querySelector('#video-id').value;
  const creatorId = document.querySelector('#creator-id').value;
  const accountName = document.querySelector('#account-name').value;  // 可选
  
  try {
    const result = await pipelineManager.createPipeline(videoId, creatorId, accountName);
    console.log('任务创建成功:', result);
  } catch (error) {
    console.error('创建失败:', error);
  }
});
```

### 9. 迁移清单

前端开发者需要完成以下修改：

- [ ] 修改API基础URL从 `/api/v1/` 到 `/api/`
- [ ] 重写Pipeline创建函数，使用新的参数结构
- [ ] 添加可选的account_name参数支持
- [ ] 修改所有使用 `pipeline_id` 的地方为 `task_id`
- [ ] 实现轮询机制替代WebSocket
- [ ] 移除或禁用Pipeline编辑和删除功能
- [ ] 移除文件上传相关功能
- [ ] 集成YouTube账号选择功能
- [ ] 实现视频发布功能
- [ ] 更新错误处理逻辑
- [ ] 修改UI以匹配新的数据结构

### 10. 测试建议

1. **基础连通性测试**
   ```bash
   curl http://localhost:51082/api/health
   ```

2. **创建任务测试（不带账号名称）**
   ```bash
   curl -X POST http://localhost:51082/api/pipeline/run \
     -H "Content-Type: application/json" \
     -d '{"video_id":"test123","creator_id":"user1","gender":1,"duration":60}'
   ```

3. **创建任务测试（带账号名称）**
   ```bash
   curl -X POST http://localhost:51082/api/pipeline/run \
     -H "Content-Type: application/json" \
     -d '{"video_id":"test123","creator_id":"user1","account_name":"account01","gender":1,"duration":60}'
   ```

4. **使用Mock模式测试发布**
   - 后端已配置Mock模式，发布操作不会真正上传到YouTube
   - 可以安全地测试发布流程

## 总结

前端需要进行较大的调整以适配后端API。主要变化包括：
1. API路径和参数结构的变化
2. 新增可选的account_name参数
3. 从WebSocket改为轮询
4. 移除不支持的功能
5. 集成新的发布功能

建议分阶段进行迁移，先确保基本的Pipeline创建和状态查询功能正常，再逐步添加发布等高级功能。