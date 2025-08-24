# 视频创作工作台前端

基于 React + TypeScript + Ant Design 的视频创作任务管理前端应用。

## 功能特性

### 已实现功能
- ✅ **创作中心** - 创建新的视频生成任务
- ✅ **任务监控** - 实时查看任务执行进度
- ✅ **任务列表** - 查看所有任务状态和历史
- ✅ **任务详情** - 查看任务结果和YouTube元数据
- ✅ **发布页面** - 编辑发布信息（界面预留）

### 待实现功能
- ⏳ 视频发布功能
- ⏳ 发布历史查看
- ⏳ 任务删除和重试
- ⏳ 批量操作

## 技术栈

- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Ant Design 5** - UI组件库
- **React Router v6** - 路由管理
- **Axios** - HTTP客户端
- **Vite** - 构建工具
- **dayjs** - 日期处理

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

## 项目结构

```
frontend/
├── src/
│   ├── pages/          # 页面组件
│   │   ├── Create/     # 创作页面
│   │   ├── Tasks/      # 任务列表
│   │   ├── TaskDetail/ # 任务详情
│   │   ├── Monitor/    # 任务监控
│   │   └── Publish/    # 发布页面
│   ├── components/     # 通用组件
│   │   ├── Layout/     # 布局组件
│   │   ├── TaskProgress/ # 进度组件
│   │   └── StatusBadge/  # 状态标签
│   ├── services/       # API服务
│   │   ├── api.ts      # API基础配置
│   │   └── pipeline.ts # Pipeline服务
│   ├── types/          # TypeScript类型
│   │   ├── task.ts     # 任务类型
│   │   └── api.ts      # API类型
│   ├── utils/          # 工具函数
│   │   └── format.ts   # 格式化工具
│   ├── router.tsx      # 路由配置
│   ├── App.tsx         # 主应用组件
│   └── main.tsx        # 应用入口
├── package.json        # 项目配置
├── tsconfig.json       # TypeScript配置
└── vite.config.ts      # Vite配置
```

## API集成

前端通过代理配置连接后端API服务器：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8888',
      changeOrigin: true,
    },
  },
}
```

### 已实现的API调用

- `POST /api/pipeline/run` - 创建任务
- `GET /api/pipeline/status/{id}` - 获取任务状态
- `GET /api/pipeline/result/{id}` - 获取任务结果
- `GET /api/pipeline/tasks` - 获取任务列表

### 预留的API接口

```typescript
// 这些接口已在代码中预留，但后端尚未实现
POST /api/publish/video         // 发布视频
GET  /api/publish/history       // 发布历史
DELETE /api/pipeline/task/{id}  // 删除任务
POST /api/pipeline/retry/{id}   // 重试任务
```

## 使用说明

### 1. 创建任务

1. 进入"创作中心"页面
2. 输入YouTube视频ID（11位字符）
3. 输入创作者ID
4. 选择语音性别（男声/女声）
5. 设置视频时长（30-300秒）
6. 可选：指定图片库目录
7. 可选：勾选"自动导出视频"
8. 点击"开始创作"

### 2. 监控任务

创建任务后会自动跳转到监控页面，可以看到：
- 任务基本信息
- 各阶段执行进度
- 实时运行时长
- 完成后的文件路径和YouTube元数据

### 3. 查看任务列表

在"任务管理"中可以：
- 查看所有任务状态
- 搜索特定任务ID
- 按状态筛选任务
- 点击查看详情或监控

### 4. 任务详情

任务完成后可以查看：
- 生成的文件路径（故事、音频、草稿、视频）
- YouTube元数据（标题、描述、标签等）
- 缩略图建议
- 一键复制路径功能

## 注意事项

1. 确保后端API服务器运行在 `http://localhost:8888`
2. 任务执行时间较长（5-15分钟），请耐心等待
3. 任务监控页面会每3秒自动刷新状态
4. 任务列表页面会每10秒自动刷新

## 开发计划

- [ ] 添加WebSocket支持，实现实时推送
- [ ] 优化移动端响应式设计
- [ ] 添加视频预览功能
- [ ] 实现批量任务管理
- [ ] 添加任务统计图表
- [ ] 国际化支持