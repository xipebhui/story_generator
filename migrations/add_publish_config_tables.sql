-- Pipeline驱动的账号组自动发布系统 - 数据库迁移脚本
-- 执行前请备份数据库

-- ============================================
-- 1. 账号组表
-- ============================================
CREATE TABLE IF NOT EXISTS account_groups (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账号组管理表';

-- ============================================
-- 2. 账号组成员表
-- ============================================
CREATE TABLE IF NOT EXISTS account_group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    
    -- AB测试变体配置
    variant_type VARCHAR(20) COMMENT 'control/treatment_a/treatment_b',
    variant_config JSON COMMENT '变体配置：包含title_prompt, thumbnail_prompt, tag_strategy等',
    
    -- 成员角色
    is_control BOOLEAN DEFAULT false COMMENT '是否为对照组',
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_group_account (group_id, account_id),
    INDEX idx_group_id (group_id),
    INDEX idx_account_id (account_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账号组成员关系表';

-- ============================================
-- 3. 发布任务配置表（核心）
-- ============================================
CREATE TABLE IF NOT EXISTS publish_task_configs (
    config_id VARCHAR(50) PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL,
    
    -- Pipeline配置
    pipeline_type VARCHAR(20) NOT NULL COMMENT '小说novel/漫画comic/搬运repost',
    pipeline_params JSON COMMENT 'Pipeline参数：image_library, image_duration等',
    
    -- 触发策略
    trigger_type VARCHAR(20) NOT NULL COMMENT 'monitor（监控）/scheduled（定时）',
    monitor_accounts JSON COMMENT '监控的YouTube账号列表',
    
    -- 发布配置
    group_id VARCHAR(50) NOT NULL,
    daily_publish_count INT DEFAULT 3 COMMENT '每日发布数量',
    publish_interval_hours INT DEFAULT 4 COMMENT '发布间隔（小时）',
    publish_start_hour INT DEFAULT 8 COMMENT '开始发布的小时（0-23）',
    
    -- 进度追踪
    today_published INT DEFAULT 0 COMMENT '今日已发布数量',
    last_reset_date DATE COMMENT '上次重置日期',
    last_publish_time TIMESTAMP NULL COMMENT '上次发布时间',
    
    -- 定时任务专用
    content_cursor JSON COMMENT '内容游标：如漫画章节进度',
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_group_id (group_id),
    INDEX idx_active_type (is_active, trigger_type),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布任务配置表';

-- ============================================
-- 4. AB测试实验表
-- ============================================
CREATE TABLE IF NOT EXISTS ab_test_experiments (
    experiment_id VARCHAR(50) PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    config_id VARCHAR(50) NOT NULL,
    
    -- 实验配置
    experiment_name VARCHAR(200) NOT NULL,
    test_dimension VARCHAR(20) NOT NULL COMMENT 'title/thumbnail/tags',
    hypothesis TEXT COMMENT '实验假设',
    
    -- 变体定义
    variants JSON COMMENT '变体配置数组',
    
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AB测试实验表';

-- ============================================
-- 5. AB测试结果表
-- ============================================
CREATE TABLE IF NOT EXISTS ab_test_results (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AB测试结果表';

-- ============================================
-- 6. 监控缓存表
-- ============================================
CREATE TABLE IF NOT EXISTS monitor_cache (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监控缓存表';

-- ============================================
-- 7. 发布队列表
-- ============================================
CREATE TABLE IF NOT EXISTS publish_queue (
    queue_id VARCHAR(50) PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    pipeline_task_id VARCHAR(50) NOT NULL,
    
    -- 发布计划
    scheduled_publish_time TIMESTAMP NOT NULL,
    actual_publish_time TIMESTAMP NULL,
    
    -- AB测试
    experiment_id VARCHAR(50),
    variant_assignments JSON COMMENT '变体分配：账号到变体的映射',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/publishing/published/failed',
    retry_count INT DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_status (config_id, status),
    INDEX idx_scheduled_time (scheduled_publish_time),
    FOREIGN KEY (config_id) REFERENCES publish_task_configs(config_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布队列表';

-- ============================================
-- 8. 扩展现有表
-- ============================================

-- 扩展pipeline_tasks表
ALTER TABLE pipeline_tasks 
ADD COLUMN IF NOT EXISTS config_id VARCHAR(50) COMMENT '关联的发布配置',
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) COMMENT 'monitor/scheduled/manual',
ADD COLUMN IF NOT EXISTS source_ref VARCHAR(200) COMMENT 'YouTube URL或漫画章节',
ADD INDEX IF NOT EXISTS idx_config_id (config_id);

-- 扩展publish_tasks表
ALTER TABLE publish_tasks
ADD COLUMN IF NOT EXISTS experiment_id VARCHAR(50) COMMENT 'AB测试实验ID',
ADD COLUMN IF NOT EXISTS variant_id VARCHAR(50) COMMENT '使用的变体ID',
ADD COLUMN IF NOT EXISTS variant_metadata JSON COMMENT '变体生成的元数据',
ADD INDEX IF NOT EXISTS idx_experiment (experiment_id);

-- ============================================
-- 9. 插入初始数据（可选）
-- ============================================

-- 创建默认账号组
INSERT IGNORE INTO account_groups (group_id, group_name, description, ab_test_enabled)
VALUES 
    ('default_group', '默认账号组', '系统默认账号组', false),
    ('test_group_a', '测试组A', '用于AB测试的账号组', true);

-- ============================================
-- 10. 创建视图（便于查询）
-- ============================================

-- 配置状态视图
CREATE OR REPLACE VIEW v_config_status AS
SELECT 
    c.config_id,
    c.config_name,
    c.pipeline_type,
    c.trigger_type,
    g.group_name,
    c.daily_publish_count,
    c.today_published,
    c.is_active,
    COUNT(DISTINCT m.account_id) as account_count
FROM publish_task_configs c
LEFT JOIN account_groups g ON c.group_id = g.group_id
LEFT JOIN account_group_members m ON g.group_id = m.group_id
GROUP BY c.config_id;

-- 发布队列视图
CREATE OR REPLACE VIEW v_publish_queue_status AS
SELECT 
    DATE(scheduled_publish_time) as publish_date,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM publish_queue
GROUP BY DATE(scheduled_publish_time);

-- ============================================
-- 11. 存储过程（自动化任务）
-- ============================================

-- 重置每日配额
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS sp_reset_daily_quota()
BEGIN
    UPDATE publish_task_configs
    SET today_published = 0,
        last_reset_date = CURDATE()
    WHERE last_reset_date < CURDATE()
    AND is_active = true;
END$$
DELIMITER ;

-- 清理过期监控缓存（30天）
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS sp_clean_monitor_cache()
BEGIN
    DELETE FROM monitor_cache
    WHERE detected_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
    AND is_processed = true;
END$$
DELIMITER ;

-- ============================================
-- 12. 创建定时事件（需要启用event_scheduler）
-- ============================================

-- 启用事件调度器
-- SET GLOBAL event_scheduler = ON;

-- 每日凌晨重置配额
CREATE EVENT IF NOT EXISTS event_reset_daily_quota
ON SCHEDULE EVERY 1 DAY
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 00:00:00')
DO CALL sp_reset_daily_quota();

-- 每周清理缓存
CREATE EVENT IF NOT EXISTS event_clean_cache
ON SCHEDULE EVERY 1 WEEK
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 03:00:00')
DO CALL sp_clean_monitor_cache();

-- ============================================
-- 迁移完成提示
-- ============================================
SELECT '数据库迁移完成！' as message,
       COUNT(*) as '新建表数量' 
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
AND table_name IN (
    'account_groups',
    'account_group_members',
    'publish_task_configs',
    'ab_test_experiments',
    'ab_test_results',
    'monitor_cache',
    'publish_queue'
);