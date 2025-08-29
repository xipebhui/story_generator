# TaskDetailDrawer 重试和删除功能测试文档

## 新增功能

### 1. API 服务方法
在 `frontend/src/services/backend.ts` 中新增：

#### retryPublishTask(publishId: string)
- 功能：重试发布任务
- 参数：publishId - 发布任务ID
- 返回：Promise<{ message: string; publish_id: string }>

#### deletePublishTask(publishId: string)  
- 功能：删除发布任务记录
- 参数：publishId - 发布任务ID
- 返回：Promise<{ message: string; publish_id: string }>

### 2. TaskDetailDrawer 组件更新

#### 新增状态
- `retryLoading` - 控制重试按钮加载状态
- `deleteLoading` - 控制删除按钮加载状态

#### 新增属性
- `onTaskRefresh?: () => void` - 刷新任务数据回调

#### 新增功能
- **重试按钮**：仅对 failed/cancelled 状态的发布任务显示
- **删除按钮**：对所有发布记录都显示，带确认对话框
- **加载状态**：按钮操作期间显示加载动画
- **错误处理**：显示操作失败的错误信息
- **数据刷新**：成功操作后自动刷新任务数据

#### UI 改进
- 在发布账号详情的 Timeline 项中添加操作按钮
- 使用 Tooltip 显示按钮功能提示
- 使用 Popconfirm 确认删除操作
- 按钮颜色区分（绿色重试，红色删除）

### 3. 父组件更新

#### Dashboard 页面
- 添加 `onTaskRefresh` 回调，调用 `loadTasks()` 刷新数据

#### TaskCenter 页面  
- 添加 `onTaskRefresh` 回调，调用 `loadTasks()` 刷新数据

### 4. 类型定义更新

#### PublishedAccount 接口
- 新增 `publish_id?: string` 字段
- 添加 'cancelled' 状态支持

## 测试要点

### 功能测试
1. ✅ 重试按钮只在 failed/cancelled 状态显示
2. ✅ 删除按钮对所有发布记录显示 
3. ✅ 删除操作有确认对话框
4. ✅ 操作按钮有加载状态
5. ✅ 成功操作后显示成功消息
6. ✅ 失败操作显示错误信息
7. ✅ 操作完成后刷新任务数据

### UI测试
1. ✅ 按钮图标和颜色正确
2. ✅ Tooltip 提示文案正确
3. ✅ 确认对话框文案正确
4. ✅ 加载动画正常显示

### 集成测试  
1. ✅ API 调用正确
2. ✅ 错误处理正常
3. ✅ 数据刷新正常
4. ✅ 父组件回调正常

## 注意事项

1. **publish_id 字段**：需要后端确保返回这个字段
2. **权限控制**：后端需要验证用户是否有删除/重试权限  
3. **错误处理**：前端已处理各种错误情况
4. **用户体验**：操作有明确的状态反馈

## API 接口要求

后端需要实现以下接口：

```
POST /api/publish/retry/{publish_id}
DELETE /api/publish/task/{publish_id}
```

响应格式：
```json
{
  "message": "操作成功",
  "publish_id": "xxx"
}
```