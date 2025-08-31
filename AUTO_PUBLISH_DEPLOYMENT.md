# 账号驱动自动发布系统 - 部署指南

## 系统概述

账号驱动自动发布系统是一个完整的视频内容自动化生产和发布解决方案，支持：
- 多账号组管理
- Pipeline动态注册
- 环形调度策略
- A/B测试
- 多平台监控
- 策略分析

## 快速启动

### 一键启动所有服务

```bash
# 赋予执行权限
chmod +x start_all_services.sh

# 启动所有服务（包括数据库迁移）
./start_all_services.sh
```

启动后可访问：
- 后端API: http://localhost:51082
- 前端界面: http://localhost:3000
- API文档: http://localhost:51082/docs

### 停止服务

```bash
./stop_services.sh
```

## 详细部署步骤

### 1. 环境准备

#### 系统要求
- Python 3.8+
- Node.js 14+
- SQLite3

#### Python依赖
```bash
pip install -r requirements.txt
```

主要依赖：
- fastapi
- uvicorn
- sqlalchemy
- aiohttp
- scipy
- numpy
- pydantic

#### 前端依赖
```bash
cd frontend
npm install
```

### 2. 数据库迁移

#### 首次部署
```bash
# 执行数据库迁移
python migrate_database.py
```

这将创建以下表：
- `pipeline_registry` - Pipeline注册表
- `account_groups` - 账号组
- `publish_configs` - 发布配置
- `ring_schedule_slots` - 环形调度槽
- `publish_strategies` - 策略
- `auto_publish_tasks` - 执行任务
- 相关关联表

#### 验证迁移
```bash
sqlite3 data/pipeline_tasks.db
.tables
.exit
```

### 3. 启动后端服务

#### 启动API服务
```bash
# 设置环境变量
export LOG_LEVEL=INFO
export DB_PATH=./data/pipeline_tasks.db

# 启动API
python api_with_db.py
```

API将在 `http://localhost:51082` 运行

#### 启动自动发布服务
```bash
# 在新终端中启动
python start_auto_publish.py
```

### 4. 启动前端

```bash
cd frontend
npm start
```

前端将在 `http://localhost:3000` 运行

## 使用指南

### 1. 访问系统

打开浏览器访问 http://localhost:3000

### 2. 导航到自动发布

在顶部标签中点击 "自动发布" 图标

### 3. 配置账号组

1. 进入 "账号组管理" 标签
2. 点击 "创建账号组"
3. 输入组名称，选择类型（生产/实验/测试）
4. 选择要加入该组的账号
5. 点击确定

### 4. 创建发布配置

1. 进入 "发布配置" 标签
2. 点击 "创建配置"
3. 配置以下信息：
   - 配置名称：如"每日故事发布"
   - 账号组：选择已创建的账号组
   - Pipeline：选择要使用的Pipeline
   - 触发方式：定时触发或监控触发
   - 策略：可选，用于A/B测试

### 5. 生成调度槽位

1. 进入 "调度日历" 标签
2. 选择发布配置
3. 点击 "生成槽位"
4. 设置：
   - 目标日期
   - 开始时间（默认6:00）
   - 结束时间（默认23:00）
   - 分配策略（均匀/随机）

### 6. 启动执行器

1. 在 "执行器仪表盘" 查看系统状态
2. 点击右上角 "启动" 按钮
3. 系统将自动：
   - 按照调度槽位执行Pipeline
   - 在指定时间发布内容
   - 记录执行结果

### 7. 创建策略（可选）

1. 进入 "策略管理" 标签
2. 创建A/B测试策略
3. 分配账号组到不同变体
4. 查看策略报告分析效果

## 系统架构

### 核心模块

#### 后端模块
- `pipeline_registry.py` - Pipeline注册和管理
- `ring_scheduler.py` - 环形调度算法
- `account_driven_executor.py` - 任务执行引擎
- `platform_monitor.py` - 多平台监控
- `strategy_engine.py` - 策略引擎
- `api_auto_publish.py` - REST API接口

#### 前端组件
- `AutoPublish/index.tsx` - 主界面
- `AccountGroupManager.tsx` - 账号组管理
- `PublishConfigManager.tsx` - 发布配置
- `ScheduleCalendar.tsx` - 调度日历
- `StrategyManager.tsx` - 策略管理
- `ExecutorDashboard.tsx` - 执行器仪表盘

### 数据流

```
账号组 → 发布配置 → 调度槽位 → 执行器 → Pipeline → 发布
                ↓
              策略引擎
                ↓
             效果分析
```

## 监控和维护

### 查看日志

```bash
# API日志
tail -f api_with_db.log

# 自动发布日志
tail -f auto_publish.log
```

### 数据库管理

```bash
# 查看任务状态
sqlite3 data/pipeline_tasks.db "SELECT * FROM auto_publish_tasks ORDER BY created_at DESC LIMIT 10;"

# 查看调度槽位
sqlite3 data/pipeline_tasks.db "SELECT * FROM ring_schedule_slots WHERE slot_date = date('now');"
```

### 性能优化

1. **调整并发数**
   - 修改 `account_driven_executor.py` 中的：
     - `max_concurrent_pipelines` (默认3)
     - `max_concurrent_publishes` (默认5)

2. **调整检查间隔**
   - 修改执行器主循环的休眠时间（默认60秒）

3. **清理历史数据**
   ```bash
   # 清理30天前的数据
   sqlite3 data/pipeline_tasks.db "DELETE FROM auto_publish_tasks WHERE created_at < date('now', '-30 days');"
   ```

## 故障排除

### 常见问题

#### 1. 数据库迁移失败
- 检查数据库文件权限
- 确保目录 `data/` 存在且可写
- 查看迁移日志中的具体错误

#### 2. API无法启动
- 检查端口51082是否被占用
- 验证Python依赖是否完整安装
- 查看 `api_with_db.log` 日志

#### 3. 前端无法访问自动发布功能
- 确保后端API正常运行
- 检查浏览器控制台错误
- 清除浏览器缓存后重试

#### 4. 执行器不工作
- 检查执行器状态是否为"运行中"
- 查看 `auto_publish.log` 日志
- 验证账号组和发布配置是否正确

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 运行服务
python api_with_db.py
```

## 安全建议

1. **生产环境部署**
   - 使用HTTPS
   - 配置防火墙规则
   - 定期备份数据库

2. **账号安全**
   - 定期更新账号凭证
   - 使用环境变量存储敏感信息
   - 限制API访问权限

3. **监控告警**
   - 配置失败任务告警
   - 监控系统资源使用
   - 定期检查日志异常

## 更新升级

### 备份数据
```bash
cp data/pipeline_tasks.db data/pipeline_tasks.db.backup
```

### 更新代码
```bash
git pull origin main
```

### 重新迁移（如有新表）
```bash
python migrate_database.py
```

### 重启服务
```bash
./stop_services.sh
./start_all_services.sh
```

## 联系支持

如遇到问题，请提供：
1. 错误日志
2. 系统环境信息
3. 操作步骤复现

---

最后更新：2024-01-10