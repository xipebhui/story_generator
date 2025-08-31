-- =====================================================
-- 账号驱动自动发布系统 - SQLite数据库迁移脚本
-- =====================================================

-- 1. Pipeline注册表
CREATE TABLE IF NOT EXISTS pipeline_registry (
    pipeline_id VARCHAR(50) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    pipeline_type VARCHAR(50) NOT NULL,
    pipeline_class VARCHAR(200) NOT NULL,
    config_schema TEXT,
    supported_platforms TEXT DEFAULT '["youtube"]',
    version VARCHAR(20) DEFAULT '1.0.0',
    status VARCHAR(20) DEFAULT 'active',
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_type ON pipeline_registry(pipeline_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_status ON pipeline_registry(status);

-- 2. 账号组表
CREATE TABLE IF NOT EXISTS account_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    group_type VARCHAR(20) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_group_type ON account_groups(group_type);
CREATE INDEX IF NOT EXISTS idx_group_active ON account_groups(is_active);

-- 3. 账号组成员表
CREATE TABLE IF NOT EXISTS account_group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) DEFAULT 'member',
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    UNIQUE(group_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_group_members ON account_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_account_role ON account_group_members(account_id, role);

-- 4. 发布配置表
CREATE TABLE IF NOT EXISTS publish_configs (
    config_id VARCHAR(50) PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL UNIQUE,
    group_id VARCHAR(50) NOT NULL,
    pipeline_id VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL,
    trigger_config TEXT NOT NULL,
    strategy_id VARCHAR(50),
    priority INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT 1,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipeline_registry(pipeline_id)
);

CREATE INDEX IF NOT EXISTS idx_config_group_pipeline ON publish_configs(group_id, pipeline_id);
CREATE INDEX IF NOT EXISTS idx_config_active ON publish_configs(is_active);

-- 5. 环形调度表
CREATE TABLE IF NOT EXISTS ring_schedule_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    slot_date DATE NOT NULL,
    slot_hour INTEGER NOT NULL CHECK (slot_hour >= 0 AND slot_hour <= 23),
    slot_minute INTEGER NOT NULL CHECK (slot_minute >= 0 AND slot_minute <= 59),
    slot_index INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    task_id VARCHAR(50),
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (config_id) REFERENCES publish_configs(config_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    UNIQUE(config_id, slot_date, slot_hour, slot_minute, account_id)
);

CREATE INDEX IF NOT EXISTS idx_slot_schedule ON ring_schedule_slots(slot_date, slot_hour, status);
CREATE INDEX IF NOT EXISTS idx_slot_config_date ON ring_schedule_slots(config_id, slot_date);
CREATE INDEX IF NOT EXISTS idx_slot_account_date ON ring_schedule_slots(account_id, slot_date);
CREATE INDEX IF NOT EXISTS idx_slot_lookup ON ring_schedule_slots(config_id, status, slot_date, slot_hour);

-- 6. 策略表
CREATE TABLE IF NOT EXISTS publish_strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    parameters TEXT,
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT 1,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_type ON publish_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_strategy_active ON publish_strategies(is_active);

-- 7. 策略分配表
CREATE TABLE IF NOT EXISTS strategy_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id VARCHAR(50) NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    variant_name VARCHAR(50) NOT NULL,
    variant_config TEXT,
    weight REAL DEFAULT 1.0,
    is_control BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES publish_strategies(strategy_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    UNIQUE(strategy_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_assignment_strategy ON strategy_assignments(strategy_id);
CREATE INDEX IF NOT EXISTS idx_assignment_group ON strategy_assignments(group_id);

-- 8. 平台监控表
CREATE TABLE IF NOT EXISTS platform_monitors (
    monitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform VARCHAR(20) NOT NULL,
    monitor_type VARCHAR(50) NOT NULL,
    target_identifier VARCHAR(200) NOT NULL,
    check_interval INTEGER DEFAULT 300,
    last_check TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    config TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, monitor_type, target_identifier)
);

CREATE INDEX IF NOT EXISTS idx_monitor_platform ON platform_monitors(platform, monitor_type);
CREATE INDEX IF NOT EXISTS idx_monitor_active ON platform_monitors(is_active, last_check, check_interval);

-- 9. 监控结果表
CREATE TABLE IF NOT EXISTS monitor_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL,
    content_id VARCHAR(100),
    content_type VARCHAR(50),
    content_data TEXT,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN DEFAULT 0,
    metadata TEXT,
    FOREIGN KEY (monitor_id) REFERENCES platform_monitors(monitor_id)
);

CREATE INDEX IF NOT EXISTS idx_result_monitor ON monitor_results(monitor_id, is_processed);
CREATE INDEX IF NOT EXISTS idx_result_content ON monitor_results(content_id);

-- 10. 执行任务表
CREATE TABLE IF NOT EXISTS auto_publish_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    pipeline_id VARCHAR(50) NOT NULL,
    slot_id INTEGER,
    strategy_id VARCHAR(50),
    variant_name VARCHAR(50),
    pipeline_status VARCHAR(20) DEFAULT 'pending',
    pipeline_result TEXT,
    publish_status VARCHAR(20) DEFAULT 'pending',
    publish_result TEXT,
    priority INTEGER DEFAULT 50,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (config_id) REFERENCES publish_configs(config_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipeline_registry(pipeline_id)
);

CREATE INDEX IF NOT EXISTS idx_task_status ON auto_publish_tasks(pipeline_status, publish_status);
CREATE INDEX IF NOT EXISTS idx_task_account ON auto_publish_tasks(account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_task_schedule ON auto_publish_tasks(scheduled_at, pipeline_status);

-- 11. 策略指标表
CREATE TABLE IF NOT EXISTS strategy_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id VARCHAR(50) NOT NULL,
    variant_name VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    custom_metrics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES publish_strategies(strategy_id),
    UNIQUE(strategy_id, variant_name, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_metric_strategy ON strategy_metrics(strategy_id, metric_date);
CREATE INDEX IF NOT EXISTS idx_metric_variant ON strategy_metrics(variant_name, metric_date);

-- =====================================================
-- 插入示例数据
-- =====================================================

-- 插入示例Pipeline
INSERT OR IGNORE INTO pipeline_registry (
    pipeline_id, pipeline_name, pipeline_type, pipeline_class, config_schema
) VALUES 
    ('story_v3', 'YouTube故事生成V3', 'content_generation', 
     'story_pipeline_v3_runner.StoryPipelineV3Runner',
     '{"type":"object","properties":{"video_id":{"type":"string"},"duration":{"type":"integer","default":120}}}'),
    
    ('metadata_gen', 'YouTube元数据生成', 'metadata',
     'pipeline_steps_youtube_metadata.GenerateYouTubeMetadataStep',
     '{"type":"object","properties":{"content_path":{"type":"string"}}}'),
    
    ('video_merge', '视频拼接', 'content_processing',
     'pipeline_video_merge.VideoMergePipeline',
     '{"type":"object","properties":{"video_paths":{"type":"array"}}}');

-- 插入示例账号组
INSERT OR IGNORE INTO account_groups (
    group_id, group_name, group_type, description
) VALUES
    ('default_group', '默认账号组', 'production', '默认的生产账号组'),
    ('test_group', '测试账号组', 'test', '用于测试的账号组'),
    ('experiment_group', '实验账号组', 'experiment', 'A/B测试实验组');

-- 创建更新时间触发器（SQLite版本）
CREATE TRIGGER IF NOT EXISTS update_pipeline_registry_timestamp 
    AFTER UPDATE ON pipeline_registry
BEGIN
    UPDATE pipeline_registry SET updated_at = CURRENT_TIMESTAMP WHERE pipeline_id = NEW.pipeline_id;
END;

CREATE TRIGGER IF NOT EXISTS update_account_groups_timestamp 
    AFTER UPDATE ON account_groups
BEGIN
    UPDATE account_groups SET updated_at = CURRENT_TIMESTAMP WHERE group_id = NEW.group_id;
END;

CREATE TRIGGER IF NOT EXISTS update_publish_configs_timestamp 
    AFTER UPDATE ON publish_configs
BEGIN
    UPDATE publish_configs SET updated_at = CURRENT_TIMESTAMP WHERE config_id = NEW.config_id;
END;

CREATE TRIGGER IF NOT EXISTS update_ring_schedule_slots_timestamp 
    AFTER UPDATE ON ring_schedule_slots
BEGIN
    UPDATE ring_schedule_slots SET updated_at = CURRENT_TIMESTAMP WHERE slot_id = NEW.slot_id;
END;

CREATE TRIGGER IF NOT EXISTS update_publish_strategies_timestamp 
    AFTER UPDATE ON publish_strategies
BEGIN
    UPDATE publish_strategies SET updated_at = CURRENT_TIMESTAMP WHERE strategy_id = NEW.strategy_id;
END;

CREATE TRIGGER IF NOT EXISTS update_platform_monitors_timestamp 
    AFTER UPDATE ON platform_monitors
BEGIN
    UPDATE platform_monitors SET updated_at = CURRENT_TIMESTAMP WHERE monitor_id = NEW.monitor_id;
END;