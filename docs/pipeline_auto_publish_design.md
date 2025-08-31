# Pipeline驱动的账号组自动发布系统 - 技术设计文档

## 1. 系统架构概述

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端界面层                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │配置管理  │ │账号组管理│ │AB测试配置│ │监控面板  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         API接口层                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ RESTful API: /api/publish-configs, /api/account-groups│  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         业务逻辑层                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │监控调度器│ │定时生产器│ │发布调度器│ │AB测试引擎│      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         数据存储层                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ MySQL: configs, groups, ab_tests, pipeline_tasks      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件说明

- **Pipeline层**: 定义视频生产方式（小说/漫画/搬运等）
- **调度层**: 监控/定时双模式，控制生产和发布节奏
- **AB测试层**: 多维度测试引擎，支持标题、封面、标签测试
- **发布层**: 定时发布队列，确保按计划发布而非立即发布

### 1.3 数据流设计

```
监控模式流程：
监控YouTube → 发现新视频 → 检查配额 → 触发Pipeline生产 → 
加入发布队列 → 计算发布时间 → 定时发布 → AB测试分发

定时模式流程：
定时触发 → 计算需求量 → 获取内容游标 → 批量生产 → 
加入发布队列 → 按计划发布 → 更新游标
```

## 2. 数据模型设计

### 2.1 核心数据表

#### 2.1.1 publish_task_configs - 发布任务配置表

```sql
CREATE TABLE publish_task_configs (
    config_id VARCHAR(50) PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL,
    
    -- Pipeline配置
    pipeline_type VARCHAR(20) NOT NULL COMMENT '小说novel/漫画comic/搬运repost',
    pipeline_params JSON COMMENT '{"image_library": "xxx", "image_duration": 60, ...}',
    
    -- 触发策略
    trigger_type VARCHAR(20) NOT NULL COMMENT 'monitor/scheduled',
    monitor_accounts JSON COMMENT '["youtube_channel_1", "youtube_channel_2"]',
    
    -- 发布配置
    group_id VARCHAR(50) NOT NULL,
    daily_publish_count INT DEFAULT 3,
    publish_interval_hours INT DEFAULT 4,
    publish_start_hour INT DEFAULT 8 COMMENT '开始发布的小时（0-23）',
    
    -- 进度追踪
    today_published INT DEFAULT 0,
    last_reset_date DATE,
    last_publish_time TIMESTAMP,
    
    -- 定时任务专用
    content_cursor JSON COMMENT '{"comic_id": "xxx", "chapter": 10}',
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_group_id (group_id),
    INDEX idx_active_type (is_active, trigger_type),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.2 account_groups - 账号组表

```sql
CREATE TABLE account_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    -- AB测试配置
    ab_test_dimension VARCHAR(20) COMMENT 'title/thumbnail/tags/all',
    ab_test_enabled BOOLEAN DEFAULT false,
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.3 account_group_members - 账号组成员表

```sql
CREATE TABLE account_group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    
    -- AB测试变体配置
    variant_type VARCHAR(20) COMMENT 'control/treatment_a/treatment_b',
    variant_config JSON COMMENT '{
        "title_prompt": "生成吸引眼球的标题",
        "thumbnail_prompt": "高对比度缩略图",
        "tag_strategy": "trending"
    }',
    
    -- 成员角色
    is_control BOOLEAN DEFAULT false COMMENT '是否为对照组',
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_group_account (group_id, account_id),
    INDEX idx_group_id (group_id),
    INDEX idx_account_id (account_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.4 ab_test_experiments - AB测试实验表

```sql
CREATE TABLE ab_test_experiments (
    experiment_id VARCHAR(50) PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    config_id VARCHAR(50) NOT NULL,
    
    -- 实验配置
    experiment_name VARCHAR(200) NOT NULL,
    test_dimension VARCHAR(20) NOT NULL COMMENT 'title/thumbnail/tags',
    hypothesis TEXT COMMENT '实验假设',
    
    -- 变体定义
    variants JSON COMMENT '[
        {
            "variant_id": "control",
            "prompt": "原始prompt",
            "allocation": 0.5
        },
        {
            "variant_id": "treatment",
            "prompt": "测试prompt",
            "allocation": 0.5
        }
    ]',
    
    -- 实验状态
    status VARCHAR(20) DEFAULT 'draft' COMMENT 'draft/running/paused/completed',
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    
    -- 统计信息
    total_impressions INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_group_config (group_id, config_id),
    INDEX idx_status (status),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    FOREIGN KEY (config_id) REFERENCES publish_task_configs(config_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.5 ab_test_results - AB测试结果表

```sql
CREATE TABLE ab_test_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id VARCHAR(50) NOT NULL,
    variant_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    publish_task_id VARCHAR(50) NOT NULL,
    
    -- 性能指标
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    watch_time_seconds INT DEFAULT 0,
    click_through_rate DECIMAL(5,4) DEFAULT 0,
    
    -- 时间记录
    published_at TIMESTAMP NOT NULL,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_experiment (experiment_id),
    INDEX idx_variant (variant_id),
    INDEX idx_publish_task (publish_task_id),
    FOREIGN KEY (experiment_id) REFERENCES ab_test_experiments(experiment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.6 monitor_cache - 监控缓存表

```sql
CREATE TABLE monitor_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    monitor_account VARCHAR(200) NOT NULL,
    video_id VARCHAR(100) NOT NULL,
    video_title TEXT,
    video_url TEXT,
    
    -- 处理状态
    is_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP NULL,
    
    -- 检测时间
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_config_video (config_id, video_id),
    INDEX idx_config_processed (config_id, is_processed),
    INDEX idx_detected (detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.7 publish_queue - 发布队列表

```sql
CREATE TABLE publish_queue (
    queue_id VARCHAR(50) PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    pipeline_task_id VARCHAR(50) NOT NULL,
    
    -- 发布计划
    scheduled_publish_time TIMESTAMP NOT NULL,
    actual_publish_time TIMESTAMP NULL,
    
    -- AB测试
    experiment_id VARCHAR(50),
    variant_assignments JSON COMMENT '{
        "account_1": "control",
        "account_2": "treatment_a"
    }',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/publishing/published/failed',
    retry_count INT DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_status (config_id, status),
    INDEX idx_scheduled_time (scheduled_publish_time),
    FOREIGN KEY (config_id) REFERENCES publish_task_configs(config_id),
    FOREIGN KEY (pipeline_task_id) REFERENCES pipeline_tasks(task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 现有表扩展

```sql
-- 扩展pipeline_tasks表
ALTER TABLE pipeline_tasks 
ADD COLUMN config_id VARCHAR(50) COMMENT '关联的发布配置',
ADD COLUMN source_type VARCHAR(20) COMMENT 'monitor/scheduled/manual',
ADD COLUMN source_ref VARCHAR(200) COMMENT 'YouTube URL或漫画章节',
ADD INDEX idx_config_id (config_id);

-- 扩展publish_tasks表
ALTER TABLE publish_tasks
ADD COLUMN experiment_id VARCHAR(50) COMMENT 'AB测试实验ID',
ADD COLUMN variant_id VARCHAR(50) COMMENT '使用的变体ID',
ADD COLUMN variant_metadata JSON COMMENT '变体生成的元数据',
ADD INDEX idx_experiment (experiment_id);
```

## 3. 后端服务设计

### 3.1 PublishTaskConfigService - 配置管理服务

```python
class PublishTaskConfigService:
    """发布任务配置管理服务"""
    
    def __init__(self):
        self.db = get_db_manager()
        
    async def create_config(self, config_data: dict) -> str:
        """创建发布配置"""
        config_id = str(uuid.uuid4())
        
        # 验证Pipeline类型
        if config_data['pipeline_type'] not in ['novel', 'comic', 'repost']:
            raise ValueError("Invalid pipeline type")
        
        # 验证触发类型
        if config_data['trigger_type'] not in ['monitor', 'scheduled']:
            raise ValueError("Invalid trigger type")
        
        # 创建配置
        config = PublishTaskConfig(
            config_id=config_id,
            **config_data
        )
        
        self.db.save(config)
        
        # 如果是监控模式，启动监控
        if config.trigger_type == 'monitor':
            await self.start_monitoring(config_id)
        
        return config_id
    
    async def update_config(self, config_id: str, updates: dict):
        """更新配置"""
        config = self.db.get_config(config_id)
        if not config:
            raise ValueError(f"Config not found: {config_id}")
        
        # 更新字段
        for key, value in updates.items():
            setattr(config, key, value)
        
        self.db.save(config)
        
    def reset_daily_quota(self):
        """重置每日配额（定时任务调用）"""
        today = get_beijing_now().date()
        configs = self.db.get_active_configs()
        
        for config in configs:
            if config.last_reset_date != today:
                config.today_published = 0
                config.last_reset_date = today
                self.db.save(config)
```

### 3.2 MonitorScheduler - 监控调度器

```python
class MonitorScheduler:
    """YouTube监控调度器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.youtube_api = YouTubeAPI()
        self.pipeline_service = PipelineService()
        self.publish_scheduler = PublishScheduler()
        self.check_interval = 300  # 5分钟检查一次
        
    async def start_monitoring(self, config_id: str):
        """启动监控任务"""
        while True:
            try:
                config = self.db.get_config(config_id)
                if not config or not config.is_active:
                    break
                
                await self.check_and_produce(config)
                
            except Exception as e:
                logger.error(f"Monitor error for {config_id}: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def check_and_produce(self, config: PublishTaskConfig):
        """检查新视频并生产内容"""
        
        # 1. 检查今日配额
        if config.today_published >= config.daily_publish_count:
            logger.info(f"Config {config.config_id} reached daily quota")
            return
        
        # 2. 监控每个账号
        for account_url in config.monitor_accounts:
            new_videos = await self.check_new_videos(account_url, config.config_id)
            
            for video in new_videos:
                # 检查是否还需要生产
                needed = config.daily_publish_count - config.today_published
                if needed <= 0:
                    break
                
                # 3. 触发Pipeline生产
                pipeline_task_id = await self.trigger_pipeline(
                    config=config,
                    source_video=video
                )
                
                # 4. 创建发布任务（重要：不是立即发布）
                publish_time = self.calculate_next_publish_time(config)
                await self.publish_scheduler.schedule_publish(
                    config_id=config.config_id,
                    pipeline_task_id=pipeline_task_id,
                    scheduled_time=publish_time
                )
                
                # 5. 更新配额
                config.today_published += 1
                self.db.save(config)
    
    async def check_new_videos(self, channel_url: str, config_id: str) -> List[dict]:
        """检查频道新视频"""
        # 获取最新视频
        videos = await self.youtube_api.get_channel_videos(channel_url, limit=10)
        
        # 过滤已处理的
        new_videos = []
        for video in videos:
            cache_entry = self.db.get_monitor_cache(config_id, video['id'])
            if not cache_entry or not cache_entry.is_processed:
                new_videos.append(video)
                
                # 添加到缓存
                self.db.save_monitor_cache(
                    config_id=config_id,
                    video_id=video['id'],
                    video_title=video['title'],
                    video_url=video['url']
                )
        
        return new_videos
    
    def calculate_next_publish_time(self, config: PublishTaskConfig) -> datetime:
        """计算下一个发布时间"""
        now = get_beijing_now()
        
        # 获取今天的发布起始时间
        start_hour = config.publish_start_hour or 8
        base_time = now.replace(hour=start_hour, minute=0, second=0)
        
        # 如果已经过了起始时间，从明天开始
        if now.hour >= start_hour + (config.publish_interval_hours * config.daily_publish_count):
            base_time = base_time + timedelta(days=1)
            config.today_published = 0  # 重置为明天的第一个
        
        # 计算具体发布时间
        publish_time = base_time + timedelta(
            hours=config.publish_interval_hours * config.today_published
        )
        
        return publish_time
```

### 3.3 ScheduledProducer - 定时生产器

```python
class ScheduledProducer:
    """定时内容生产器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.pipeline_service = PipelineService()
        self.publish_scheduler = PublishScheduler()
        
    async def produce_batch(self, config: PublishTaskConfig):
        """批量生产内容"""
        
        # 1. 计算需要生产的数量
        needed = config.daily_publish_count - config.today_published
        if needed <= 0:
            logger.info(f"Config {config.config_id} no production needed")
            return
        
        # 2. 获取内容游标
        cursor = config.content_cursor or {}
        
        # 3. 批量生产
        produced_tasks = []
        for i in range(needed):
            # 获取下一批内容
            next_content = self.get_next_content(config, cursor)
            
            # 创建Pipeline任务
            pipeline_task_id = await self.trigger_pipeline(
                config=config,
                content_source=next_content
            )
            
            produced_tasks.append(pipeline_task_id)
            
            # 更新游标
            cursor = self.update_cursor(config, cursor, next_content)
        
        # 4. 创建发布计划
        publish_times = self.calculate_publish_times(config, needed)
        for i, task_id in enumerate(produced_tasks):
            await self.publish_scheduler.schedule_publish(
                config_id=config.config_id,
                pipeline_task_id=task_id,
                scheduled_time=publish_times[i]
            )
        
        # 5. 更新配置
        config.content_cursor = cursor
        config.today_published = config.daily_publish_count
        self.db.save(config)
    
    def get_next_content(self, config: PublishTaskConfig, cursor: dict) -> dict:
        """获取下一批内容"""
        if config.pipeline_type == 'comic':
            # 漫画类型：获取下N章
            comic_id = cursor.get('comic_id', 'default_comic')
            start_chapter = cursor.get('chapter', 1)
            chapters_per_video = config.pipeline_params.get('chapters_per_video', 2)
            
            return {
                'comic_id': comic_id,
                'start_chapter': start_chapter,
                'end_chapter': start_chapter + chapters_per_video - 1,
                'chapters': self.get_comic_chapters(comic_id, start_chapter, chapters_per_video)
            }
        
        elif config.pipeline_type == 'novel':
            # 小说类型：获取下一段
            novel_id = cursor.get('novel_id', 'default_novel')
            segment = cursor.get('segment', 1)
            
            return {
                'novel_id': novel_id,
                'segment': segment,
                'content': self.get_novel_segment(novel_id, segment)
            }
        
        return {}
    
    def update_cursor(self, config: PublishTaskConfig, cursor: dict, content: dict) -> dict:
        """更新内容游标"""
        new_cursor = cursor.copy()
        
        if config.pipeline_type == 'comic':
            new_cursor['chapter'] = content['end_chapter'] + 1
        elif config.pipeline_type == 'novel':
            new_cursor['segment'] = content['segment'] + 1
        
        return new_cursor
```

### 3.4 PublishScheduler - 发布调度器

```python
class PublishScheduler:
    """发布时间调度器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.publish_service = get_publish_service()
        self.ab_test_engine = ABTestEngine()
        
    async def schedule_publish(self, config_id: str, pipeline_task_id: str, 
                              scheduled_time: datetime):
        """创建发布计划"""
        
        # 1. 创建发布队列记录
        queue_id = str(uuid.uuid4())
        queue_entry = PublishQueue(
            queue_id=queue_id,
            config_id=config_id,
            pipeline_task_id=pipeline_task_id,
            scheduled_publish_time=scheduled_time,
            status='pending'
        )
        
        # 2. 如果有AB测试，分配变体
        config = self.db.get_config(config_id)
        group = self.db.get_account_group(config.group_id)
        
        if group.ab_test_enabled:
            experiment = self.ab_test_engine.get_active_experiment(group.group_id)
            if experiment:
                queue_entry.experiment_id = experiment.experiment_id
                queue_entry.variant_assignments = self.assign_variants(
                    experiment, 
                    group.members
                )
        
        self.db.save(queue_entry)
        
        # 3. 设置定时任务
        await self.schedule_task(queue_id, scheduled_time)
        
        return queue_id
    
    async def execute_publish(self, queue_id: str):
        """执行发布任务"""
        queue_entry = self.db.get_queue_entry(queue_id)
        if not queue_entry:
            logger.error(f"Queue entry not found: {queue_id}")
            return
        
        try:
            # 1. 获取Pipeline任务结果
            pipeline_task = self.db.get_pipeline_task(queue_entry.pipeline_task_id)
            if not pipeline_task or pipeline_task.status != 'completed':
                raise ValueError("Pipeline task not completed")
            
            # 2. 获取账号组成员
            config = self.db.get_config(queue_entry.config_id)
            group = self.db.get_account_group(config.group_id)
            members = self.db.get_group_members(group.group_id)
            
            # 3. 为每个账号生成发布任务
            publish_tasks = []
            for member in members:
                # 生成AB测试变体元数据
                metadata = await self.generate_variant_metadata(
                    pipeline_task,
                    member,
                    queue_entry.experiment_id,
                    queue_entry.variant_assignments
                )
                
                # 创建发布任务
                publish_task = await self.publish_service.create_publish_task(
                    task_id=pipeline_task.task_id,
                    account_id=member.account_id,
                    video_title=metadata['title'],
                    video_description=metadata['description'],
                    video_tags=metadata['tags'],
                    thumbnail_path=metadata.get('thumbnail_path')
                )
                
                publish_tasks.append(publish_task)
            
            # 4. 更新队列状态
            queue_entry.status = 'published'
            queue_entry.actual_publish_time = get_beijing_now()
            self.db.save(queue_entry)
            
            logger.info(f"Successfully published {len(publish_tasks)} tasks for queue {queue_id}")
            
        except Exception as e:
            logger.error(f"Publish failed for queue {queue_id}: {e}")
            queue_entry.status = 'failed'
            queue_entry.error_message = str(e)
            queue_entry.retry_count += 1
            self.db.save(queue_entry)
            
            # 重试逻辑
            if queue_entry.retry_count < 3:
                await self.schedule_retry(queue_id)
```

### 3.5 ABTestEngine - AB测试引擎

```python
class ABTestEngine:
    """AB测试引擎"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.llm_service = LLMService()  # 用于生成变体
        
    async def create_experiment(self, group_id: str, config: dict) -> str:
        """创建AB测试实验"""
        experiment_id = str(uuid.uuid4())
        
        experiment = ABTestExperiment(
            experiment_id=experiment_id,
            group_id=group_id,
            config_id=config['config_id'],
            experiment_name=config['name'],
            test_dimension=config['dimension'],
            hypothesis=config.get('hypothesis'),
            variants=config['variants'],
            status='draft'
        )
        
        self.db.save(experiment)
        return experiment_id
    
    async def generate_variant_metadata(self, base_content: dict, 
                                       member: AccountGroupMember,
                                       experiment_id: str = None) -> dict:
        """生成AB测试变体元数据"""
        
        variant_config = member.variant_config or {}
        metadata = {}
        
        # 生成标题变体
        if 'title_prompt' in variant_config:
            metadata['title'] = await self.llm_service.generate(
                prompt=variant_config['title_prompt'],
                context=base_content
            )
        else:
            metadata['title'] = base_content.get('title', '')
        
        # 生成描述变体
        if 'description_prompt' in variant_config:
            metadata['description'] = await self.llm_service.generate(
                prompt=variant_config['description_prompt'],
                context=base_content
            )
        else:
            metadata['description'] = base_content.get('description', '')
        
        # 生成标签变体
        if 'tag_strategy' in variant_config:
            metadata['tags'] = await self.generate_tags(
                strategy=variant_config['tag_strategy'],
                context=base_content
            )
        else:
            metadata['tags'] = base_content.get('tags', [])
        
        # 生成缩略图（如果配置了）
        if 'thumbnail_prompt' in variant_config:
            metadata['thumbnail_path'] = await self.generate_thumbnail(
                prompt=variant_config['thumbnail_prompt'],
                base_image=base_content.get('thumbnail_path')
            )
        
        # 记录实验数据
        if experiment_id:
            await self.record_variant_usage(
                experiment_id=experiment_id,
                variant_id=member.variant_type,
                account_id=member.account_id,
                metadata=metadata
            )
        
        return metadata
    
    async def analyze_results(self, experiment_id: str) -> dict:
        """分析AB测试结果"""
        results = self.db.get_experiment_results(experiment_id)
        
        # 按变体分组
        variant_stats = {}
        for result in results:
            variant_id = result.variant_id
            if variant_id not in variant_stats:
                variant_stats[variant_id] = {
                    'count': 0,
                    'total_views': 0,
                    'total_likes': 0,
                    'avg_watch_time': 0
                }
            
            stats = variant_stats[variant_id]
            stats['count'] += 1
            stats['total_views'] += result.views
            stats['total_likes'] += result.likes
            stats['avg_watch_time'] += result.watch_time_seconds
        
        # 计算统计显著性
        significance = self.calculate_significance(variant_stats)
        
        return {
            'variant_stats': variant_stats,
            'significance': significance,
            'winner': self.determine_winner(variant_stats, significance)
        }
```

## 4. API接口规范

### 4.1 配置管理API

#### 创建发布配置
```http
POST /api/publish-configs
Content-Type: application/json

{
    "config_name": "小说自动发布",
    "pipeline_type": "novel",
    "pipeline_params": {
        "image_library": "fantasy",
        "image_duration": 60,
        "enable_subtitle": true
    },
    "trigger_type": "monitor",
    "monitor_accounts": [
        "https://youtube.com/@channel1",
        "https://youtube.com/@channel2"
    ],
    "group_id": "group_001",
    "daily_publish_count": 3,
    "publish_interval_hours": 4,
    "publish_start_hour": 8
}

Response:
{
    "config_id": "cfg_12345",
    "message": "配置创建成功"
}
```

#### 获取配置列表
```http
GET /api/publish-configs?active=true&trigger_type=monitor

Response:
{
    "configs": [
        {
            "config_id": "cfg_12345",
            "config_name": "小说自动发布",
            "pipeline_type": "novel",
            "trigger_type": "monitor",
            "group_id": "group_001",
            "daily_publish_count": 3,
            "today_published": 1,
            "is_active": true
        }
    ],
    "total": 1
}
```

### 4.2 账号组管理API

#### 创建账号组
```http
POST /api/account-groups
Content-Type: application/json

{
    "group_name": "测试组A",
    "description": "用于AB测试标题效果",
    "ab_test_dimension": "title",
    "ab_test_enabled": true,
    "members": [
        {
            "account_id": "acc_001",
            "variant_type": "control",
            "variant_config": {
                "title_prompt": "生成简洁的标题"
            }
        },
        {
            "account_id": "acc_002",
            "variant_type": "treatment_a",
            "variant_config": {
                "title_prompt": "生成吸引眼球的标题，包含数字和情绪词"
            }
        }
    ]
}

Response:
{
    "group_id": "group_002",
    "message": "账号组创建成功"
}
```

### 4.3 监控状态API

#### 获取监控状态
```http
GET /api/monitor/status?config_id=cfg_12345

Response:
{
    "config_id": "cfg_12345",
    "monitor_accounts": [
        {
            "account": "https://youtube.com/@channel1",
            "last_check": "2024-01-01T10:00:00Z",
            "detected_videos": 5,
            "processed_videos": 3
        }
    ],
    "today_published": 2,
    "daily_quota": 3,
    "next_publish_time": "2024-01-01T16:00:00Z"
}
```

### 4.4 AB测试API

#### 创建AB测试实验
```http
POST /api/ab-tests/experiments
Content-Type: application/json

{
    "group_id": "group_002",
    "config_id": "cfg_12345",
    "experiment_name": "标题优化测试",
    "test_dimension": "title",
    "hypothesis": "使用情绪词的标题会提高点击率",
    "variants": [
        {
            "variant_id": "control",
            "prompt": "生成简洁明了的标题",
            "allocation": 0.5
        },
        {
            "variant_id": "treatment",
            "prompt": "生成包含情绪词和数字的吸引人标题",
            "allocation": 0.5
        }
    ]
}

Response:
{
    "experiment_id": "exp_789",
    "message": "实验创建成功"
}
```

#### 获取实验结果
```http
GET /api/ab-tests/experiments/exp_789/results

Response:
{
    "experiment_id": "exp_789",
    "status": "running",
    "variant_stats": {
        "control": {
            "count": 50,
            "avg_views": 1200,
            "avg_ctr": 0.032,
            "confidence_interval": [0.028, 0.036]
        },
        "treatment": {
            "count": 50,
            "avg_views": 1500,
            "avg_ctr": 0.041,
            "confidence_interval": [0.037, 0.045]
        }
    },
    "significance": {
        "p_value": 0.012,
        "is_significant": true
    },
    "winner": "treatment",
    "improvement": "28.1%"
}
```

## 5. 前端架构设计

### 5.1 组件结构

```
frontend/src/
├── components/
│   ├── PublishConfig/
│   │   ├── index.tsx              # 主配置组件
│   │   ├── ConfigForm.tsx         # 配置表单
│   │   ├── PipelineSelector.tsx   # Pipeline选择器
│   │   ├── TriggerModeSelector.tsx # 触发模式选择
│   │   └── PublishSettings.tsx    # 发布设置
│   │
│   ├── AccountGroup/
│   │   ├── index.tsx              # 账号组管理主组件
│   │   ├── GroupList.tsx          # 组列表
│   │   ├── GroupForm.tsx          # 创建/编辑组
│   │   ├── MemberManager.tsx      # 成员管理
│   │   └── ABTestConfig.tsx       # AB测试配置
│   │
│   ├── Monitoring/
│   │   ├── Dashboard.tsx          # 监控仪表板
│   │   ├── TaskQueue.tsx          # 任务队列
│   │   ├── PublishCalendar.tsx    # 发布日历
│   │   └── StatusCards.tsx        # 状态卡片
│   │
│   └── ABTest/
│       ├── ExperimentList.tsx     # 实验列表
│       ├── ExperimentForm.tsx     # 创建实验
│       ├── ResultsViewer.tsx      # 结果查看
│       └── VariantComparison.tsx  # 变体对比
│
├── store/
│   ├── index.ts
│   ├── publishConfig.ts           # 配置状态管理
│   ├── accountGroup.ts            # 账号组状态
│   ├── monitoring.ts              # 监控状态
│   └── abTest.ts                  # AB测试状态
│
├── services/
│   ├── publishConfigAPI.ts        # 配置API调用
│   ├── accountGroupAPI.ts         # 账号组API
│   ├── monitoringAPI.ts           # 监控API
│   └── abTestAPI.ts               # AB测试API
│
└── types/
    ├── publishConfig.ts            # 配置类型定义
    ├── accountGroup.ts             # 账号组类型
    └── abTest.ts                   # AB测试类型
```

### 5.2 核心组件实现

#### PublishConfigForm组件
```tsx
import React, { useState, useEffect } from 'react';
import { Form, Input, Select, InputNumber, Switch, Button, Space, Card, Alert } from 'antd';
import { PipelineSelector } from './PipelineSelector';
import { TriggerModeSelector } from './TriggerModeSelector';
import { AccountGroupSelector } from '../AccountGroup/AccountGroupSelector';

interface PublishConfigFormProps {
  onSubmit: (values: PublishConfig) => void;
  initialValues?: PublishConfig;
}

export const PublishConfigForm: React.FC<PublishConfigFormProps> = ({
  onSubmit,
  initialValues
}) => {
  const [form] = Form.useForm();
  const [triggerType, setTriggerType] = useState<'monitor' | 'scheduled'>('monitor');
  const [pipelineType, setPipelineType] = useState<string>('novel');
  
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 构建配置对象
      const config: PublishConfig = {
        ...values,
        pipeline_type: pipelineType,
        trigger_type: triggerType,
        pipeline_params: getPipelineParams(pipelineType, values),
      };
      
      onSubmit(config);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };
  
  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues}
      onFinish={handleSubmit}
    >
      <Card title="基础配置" className="mb-4">
        <Form.Item
          name="config_name"
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="例如：小说自动发布" />
        </Form.Item>
        
        <Form.Item label="Pipeline类型">
          <PipelineSelector
            value={pipelineType}
            onChange={setPipelineType}
          />
        </Form.Item>
        
        {/* Pipeline参数配置 */}
        {pipelineType === 'novel' && (
          <>
            <Form.Item name="image_library" label="图库选择">
              <Select>
                <Option value="fantasy">奇幻</Option>
                <Option value="romance">言情</Option>
                <Option value="history">历史</Option>
              </Select>
            </Form.Item>
            <Form.Item name="image_duration" label="图片时长(秒)">
              <InputNumber min={30} max={120} />
            </Form.Item>
          </>
        )}
        
        {pipelineType === 'comic' && (
          <>
            <Form.Item name="comic_library" label="漫画库">
              <Select>
                <Option value="romance">言情漫画</Option>
                <Option value="action">动作漫画</Option>
              </Select>
            </Form.Item>
            <Form.Item name="chapters_per_video" label="每视频章节数">
              <InputNumber min={1} max={5} />
            </Form.Item>
          </>
        )}
      </Card>
      
      <Card title="触发策略" className="mb-4">
        <Form.Item label="触发模式">
          <TriggerModeSelector
            value={triggerType}
            onChange={setTriggerType}
          />
        </Form.Item>
        
        {triggerType === 'monitor' && (
          <Form.Item
            name="monitor_accounts"
            label="监控账号"
            rules={[{ required: true, message: '请添加监控账号' }]}
          >
            <Select
              mode="tags"
              placeholder="输入YouTube频道URL"
              style={{ width: '100%' }}
            />
          </Form.Item>
        )}
        
        {triggerType === 'scheduled' && (
          <Alert
            message="定时任务将按照发布计划自动生产内容"
            type="info"
            showIcon
            className="mb-3"
          />
        )}
      </Card>
      
      <Card title="发布设置" className="mb-4">
        <Form.Item
          name="group_id"
          label="账号组"
          rules={[{ required: true, message: '请选择账号组' }]}
        >
          <AccountGroupSelector />
        </Form.Item>
        
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="daily_publish_count"
              label="每日发布数量"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={10} />
            </Form.Item>
          </Col>
          
          <Col span={8}>
            <Form.Item
              name="publish_interval_hours"
              label="发布间隔(小时)"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={24} />
            </Form.Item>
          </Col>
          
          <Col span={8}>
            <Form.Item
              name="publish_start_hour"
              label="开始发布时间"
              rules={[{ required: true }]}
            >
              <Select>
                {Array.from({ length: 24 }, (_, i) => (
                  <Option key={i} value={i}>
                    {i}:00
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
      </Card>
      
      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit">
            创建配置
          </Button>
          <Button>取消</Button>
        </Space>
      </Form.Item>
    </Form>
  );
};
```

### 5.3 状态管理（Redux）

```typescript
// store/publishConfig.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { publishConfigAPI } from '../services/publishConfigAPI';

interface PublishConfigState {
  configs: PublishConfig[];
  selectedConfig: PublishConfig | null;
  loading: boolean;
  error: string | null;
}

const initialState: PublishConfigState = {
  configs: [],
  selectedConfig: null,
  loading: false,
  error: null,
};

// 异步操作
export const fetchConfigs = createAsyncThunk(
  'publishConfig/fetchConfigs',
  async () => {
    const response = await publishConfigAPI.getConfigs();
    return response.data;
  }
);

export const createConfig = createAsyncThunk(
  'publishConfig/create',
  async (config: PublishConfig) => {
    const response = await publishConfigAPI.createConfig(config);
    return response.data;
  }
);

// Slice
const publishConfigSlice = createSlice({
  name: 'publishConfig',
  initialState,
  reducers: {
    selectConfig: (state, action) => {
      state.selectedConfig = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConfigs.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchConfigs.fulfilled, (state, action) => {
        state.loading = false;
        state.configs = action.payload;
      })
      .addCase(fetchConfigs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '获取配置失败';
      })
      .addCase(createConfig.fulfilled, (state, action) => {
        state.configs.push(action.payload);
      });
  },
});

export const { selectConfig, clearError } = publishConfigSlice.actions;
export default publishConfigSlice.reducer;
```

## 6. 集成方案

### 6.1 与pipeline_core.py集成

```python
# 修改pipeline_core.py
class VideoPipeline:
    def __init__(self, request: PipelineRequest, config_id: str = None, **kwargs):
        self.request = request
        self.config_id = config_id  # 新增：关联配置ID
        
        # 如果有配置ID，从数据库加载配置参数
        if config_id:
            self.load_config_params()
    
    def load_config_params(self):
        """从配置加载Pipeline参数"""
        config = db_manager.get_config(self.config_id)
        if config:
            # 应用配置中的Pipeline参数
            self.request.image_duration = config.pipeline_params.get(
                'image_duration', 
                self.request.image_duration
            )
            self.request.image_dir = config.pipeline_params.get(
                'image_library',
                self.request.image_dir
            )
```

### 6.2 与publish_service.py集成

```python
# 扩展publish_service.py
class PublishService:
    def create_batch_publish_tasks(self, 
                                  pipeline_task_id: str,
                                  group_id: str,
                                  variant_metadata: Dict[str, dict]) -> List[str]:
        """批量创建发布任务（支持AB测试）"""
        
        publish_task_ids = []
        group_members = self.db.get_group_members(group_id)
        
        for member in group_members:
            account_id = member.account_id
            metadata = variant_metadata.get(account_id, {})
            
            # 创建发布任务
            publish_task_id = self.create_publish_task(
                task_id=pipeline_task_id,
                account_id=account_id,
                video_title=metadata.get('title'),
                video_description=metadata.get('description'),
                video_tags=metadata.get('tags'),
                thumbnail_path=metadata.get('thumbnail_path')
            )
            
            publish_task_ids.append(publish_task_id)
        
        return publish_task_ids
```

## 7. 监控与运维

### 7.1 监控指标

```python
class SystemMetrics:
    """系统监控指标"""
    
    def get_metrics(self) -> dict:
        return {
            # 生产指标
            'production': {
                'total_produced_today': self.get_today_production_count(),
                'production_success_rate': self.get_production_success_rate(),
                'avg_production_time': self.get_avg_production_time(),
                'queue_length': self.get_production_queue_length()
            },
            
            # 发布指标
            'publishing': {
                'total_published_today': self.get_today_publish_count(),
                'publish_success_rate': self.get_publish_success_rate(),
                'pending_publishes': self.get_pending_publish_count(),
                'failed_publishes': self.get_failed_publish_count()
            },
            
            # 监控指标
            'monitoring': {
                'active_monitors': self.get_active_monitor_count(),
                'detected_videos_today': self.get_detected_videos_count(),
                'processed_videos_today': self.get_processed_videos_count()
            },
            
            # AB测试指标
            'ab_testing': {
                'active_experiments': self.get_active_experiments_count(),
                'total_impressions': self.get_total_impressions(),
                'significant_results': self.get_significant_results_count()
            },
            
            # 系统健康
            'health': {
                'api_response_time': self.get_api_response_time(),
                'database_connections': self.get_db_connection_count(),
                'error_rate': self.get_error_rate(),
                'cpu_usage': self.get_cpu_usage(),
                'memory_usage': self.get_memory_usage()
            }
        }
```

### 7.2 告警规则

```yaml
alerts:
  - name: ProductionQueueBacklog
    condition: queue_length > 50
    severity: warning
    action: notify_admin
    
  - name: PublishFailureRate
    condition: publish_success_rate < 0.8
    severity: critical
    action: 
      - notify_admin
      - pause_publishing
    
  - name: MonitorTimeout
    condition: last_monitor_check > 30min
    severity: warning
    action: restart_monitor
    
  - name: DatabaseConnectionExhausted
    condition: database_connections > 90%
    severity: critical
    action:
      - notify_admin
      - scale_database
    
  - name: ABTestAnomalyDetected
    condition: variant_performance_deviation > 50%
    severity: info
    action: notify_analyst
```

### 7.3 日志设计

```python
import structlog

# 配置结构化日志
logger = structlog.get_logger()

class StructuredLogger:
    """结构化日志记录器"""
    
    @staticmethod
    def log_production(config_id: str, task_id: str, status: str, **kwargs):
        """记录生产日志"""
        logger.info(
            "production_event",
            config_id=config_id,
            task_id=task_id,
            status=status,
            timestamp=get_beijing_now().isoformat(),
            **kwargs
        )
    
    @staticmethod
    def log_publish(config_id: str, account_id: str, status: str, **kwargs):
        """记录发布日志"""
        logger.info(
            "publish_event",
            config_id=config_id,
            account_id=account_id,
            status=status,
            timestamp=get_beijing_now().isoformat(),
            **kwargs
        )
    
    @staticmethod
    def log_ab_test(experiment_id: str, variant: str, metric: str, value: float):
        """记录AB测试日志"""
        logger.info(
            "ab_test_event",
            experiment_id=experiment_id,
            variant=variant,
            metric=metric,
            value=value,
            timestamp=get_beijing_now().isoformat()
        )
    
    @staticmethod
    def log_error(error_type: str, error_message: str, **context):
        """记录错误日志"""
        logger.error(
            "error_event",
            error_type=error_type,
            error_message=error_message,
            timestamp=get_beijing_now().isoformat(),
            **context
        )
```

## 8. 实施计划

### 8.1 第一阶段：基础架构（Week 1-2）

**目标**：建立系统基础框架

**交付物**：
- 数据库表结构创建完成
- 基础API框架搭建
- 配置管理服务实现

**关键任务**：
1. 创建数据库迁移脚本
2. 实现PublishTaskConfigService
3. 开发配置CRUD API
4. 创建基础前端配置界面

### 8.2 第二阶段：调度系统（Week 3-4）

**目标**：实现核心调度功能

**交付物**：
- 监控调度器完成
- 定时生产器完成
- 发布时间计算器完成

**关键任务**：
1. 实现MonitorScheduler（重点：定时发布）
2. 实现ScheduledProducer
3. 实现PublishScheduler
4. 集成现有Pipeline系统

### 8.3 第三阶段：AB测试（Week 5-6）

**目标**：完整的AB测试能力

**交付物**：
- AB测试引擎完成
- 变体生成器完成
- 效果追踪系统完成

**关键任务**：
1. 实现ABTestEngine
2. 开发变体生成逻辑
3. 创建实验管理界面
4. 实现统计分析功能

### 8.4 第四阶段：前端开发（Week 7-8）

**目标**：完整的用户界面

**交付物**：
- 配置管理界面
- 账号组管理界面
- 监控仪表板

**关键任务**：
1. 开发PublishConfig组件
2. 开发AccountGroup组件
3. 实现监控Dashboard
4. 集成Redux状态管理

### 8.5 第五阶段：优化完善（Week 9-10）

**目标**：生产级系统优化

**交付物**：
- 完整的错误处理
- 监控告警系统
- 性能优化完成

**关键任务**：
1. 添加重试机制
2. 实现监控指标收集
3. 配置告警规则
4. 性能测试和优化

## 9. 风险管理

### 9.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|----------|
| YouTube API限制 | 高 | 中 | 实现请求限流和缓存机制 |
| Pipeline处理瓶颈 | 高 | 中 | 使用任务队列和并发控制 |
| 数据库性能问题 | 中 | 低 | 优化索引和查询，准备分库方案 |
| AB测试统计偏差 | 中 | 中 | 严格的实验设计和样本量计算 |

### 9.2 业务风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|----------|
| 内容重复发布 | 高 | 低 | 严格的去重机制和缓存 |
| 发布时间冲突 | 中 | 中 | 智能时间分配算法 |
| 账号被限制 | 高 | 低 | 控制发布频率，监控账号状态 |

## 10. 总结

本系统设计实现了从用户触发到账号组自动触发的完整转变，核心特性包括：

1. **Pipeline驱动架构**：灵活支持多种视频生产类型
2. **双模式调度**：监控和定时两种触发方式
3. **定时发布队列**：生产后按计划发布，而非立即发布
4. **完整AB测试**：科学的实验设计和效果评估
5. **高度自动化**：配置后自动运行，减少人工干预

系统采用模块化设计，易于扩展和维护，为后续功能迭代提供了良好基础。