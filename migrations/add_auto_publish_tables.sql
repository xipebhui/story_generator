-- =====================================================
-- 账号驱动自动发布系统 - 数据库迁移脚本
-- =====================================================

-- 1. Pipeline注册表
CREATE TABLE IF NOT EXISTS pipeline_registry (
    pipeline_id VARCHAR(50) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    pipeline_type VARCHAR(50) NOT NULL, -- 'story', 'news', 'tutorial', etc
    pipeline_class VARCHAR(200) NOT NULL, -- Python class path
    config_schema JSON, -- Pipeline配置模板
    supported_platforms JSON DEFAULT '["youtube"]', -- 支持的平台列表
    version VARCHAR(20) DEFAULT '1.0.0',
    status VARCHAR(20) DEFAULT 'active', -- active, deprecated, testing
    metadata JSON, -- 额外元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_pipeline_type (pipeline_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 账号组表
CREATE TABLE IF NOT EXISTS account_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,
    group_type VARCHAR(20) NOT NULL, -- 'experiment', 'production', 'test'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON, -- 额外配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_group_name (group_name),
    INDEX idx_group_type (group_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 账号组成员表
CREATE TABLE IF NOT EXISTS account_group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) DEFAULT 'member', -- 'control', 'experiment', 'member'
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    UNIQUE KEY uk_group_account (group_id, account_id),
    INDEX idx_account_role (account_id, role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 发布配置表
CREATE TABLE IF NOT EXISTS publish_configs (
    config_id VARCHAR(50) PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    pipeline_id VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL, -- 'scheduled', 'monitor'
    trigger_config JSON NOT NULL, -- 触发器配置
    strategy_id VARCHAR(50), -- 关联的策略
    priority INT DEFAULT 50,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipeline_registry(pipeline_id),
    UNIQUE KEY uk_config_name (config_name),
    INDEX idx_group_pipeline (group_id, pipeline_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 环形调度表
CREATE TABLE IF NOT EXISTS ring_schedule_slots (
    slot_id INT AUTO_INCREMENT PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    slot_date DATE NOT NULL,
    slot_hour INT NOT NULL CHECK (slot_hour >= 0 AND slot_hour <= 23),
    slot_minute INT NOT NULL CHECK (slot_minute >= 0 AND slot_minute <= 59),
    slot_index INT NOT NULL, -- 在环中的位置
    status VARCHAR(20) DEFAULT 'pending', -- pending, scheduled, completed, failed
    task_id VARCHAR(50), -- 关联的任务ID
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (config_id) REFERENCES publish_configs(config_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    UNIQUE KEY uk_slot (config_id, slot_date, slot_hour, slot_minute, account_id),
    INDEX idx_schedule (slot_date, slot_hour, status),
    INDEX idx_config_date (config_id, slot_date),
    INDEX idx_account_date (account_id, slot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 策略表
CREATE TABLE IF NOT EXISTS publish_strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(30) NOT NULL, -- 'ab_test', 'round_robin', 'weighted'
    parameters JSON NOT NULL, -- 策略参数
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_strategy_name (strategy_name),
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_active_date (is_active, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 策略分配表
CREATE TABLE IF NOT EXISTS strategy_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id VARCHAR(50) NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    variant_name VARCHAR(50) NOT NULL, -- 'control', 'variant_a', 'variant_b'
    variant_config JSON, -- 变体特定配置
    weight DECIMAL(5,2) DEFAULT 1.0, -- 权重
    is_control BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (strategy_id) REFERENCES publish_strategies(strategy_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    UNIQUE KEY uk_strategy_group (strategy_id, group_id),
    INDEX idx_group_variant (group_id, variant_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 平台监控配置表
CREATE TABLE IF NOT EXISTS platform_monitors (
    monitor_id VARCHAR(50) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL, -- 'youtube', 'bilibili', 'douyin', 'tiktok'
    monitor_type VARCHAR(30) NOT NULL, -- 'competitor', 'trending', 'keyword'
    target_identifier VARCHAR(200) NOT NULL, -- 频道ID, 关键词等
    config JSON NOT NULL, -- 监控配置
    last_check TIMESTAMP NULL,
    check_interval INT DEFAULT 3600, -- 检查间隔(秒)
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_platform_type (platform, monitor_type),
    INDEX idx_active_check (is_active, last_check)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 监控结果表
CREATE TABLE IF NOT EXISTS monitor_results (
    result_id INT AUTO_INCREMENT PRIMARY KEY,
    monitor_id VARCHAR(50) NOT NULL,
    content_id VARCHAR(100) NOT NULL, -- 平台内容ID
    content_title TEXT,
    content_data JSON, -- 完整内容数据
    metrics JSON, -- 观看数、点赞数等
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (monitor_id) REFERENCES platform_monitors(monitor_id),
    UNIQUE KEY uk_monitor_content (monitor_id, content_id),
    INDEX idx_captured (captured_at, processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. 执行任务表(扩展现有publish_tasks表)
CREATE TABLE IF NOT EXISTS auto_publish_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    config_id VARCHAR(50) NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    pipeline_id VARCHAR(50) NOT NULL,
    slot_id INT, -- 关联的调度槽
    strategy_id VARCHAR(50), -- 使用的策略
    variant_name VARCHAR(50), -- 策略变体
    
    -- Pipeline执行信息
    pipeline_config JSON, -- Pipeline配置
    pipeline_status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    pipeline_result JSON, -- Pipeline执行结果
    
    -- 发布信息
    publish_status VARCHAR(20) DEFAULT 'pending', -- pending, scheduled, published, failed
    publish_time TIMESTAMP NULL,
    publish_result JSON, -- 发布结果
    
    -- 平台信息
    platform VARCHAR(20) DEFAULT 'youtube',
    platform_content_id VARCHAR(200), -- 平台返回的内容ID
    platform_url TEXT, -- 内容URL
    
    -- 元数据
    priority INT DEFAULT 50,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    metadata JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    
    FOREIGN KEY (config_id) REFERENCES publish_configs(config_id),
    FOREIGN KEY (group_id) REFERENCES account_groups(group_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipeline_registry(pipeline_id),
    FOREIGN KEY (slot_id) REFERENCES ring_schedule_slots(slot_id),
    
    INDEX idx_status (pipeline_status, publish_status),
    INDEX idx_schedule (scheduled_at, publish_status),
    INDEX idx_config_account (config_id, account_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. 策略效果跟踪表
CREATE TABLE IF NOT EXISTS strategy_metrics (
    metric_id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id VARCHAR(50) NOT NULL,
    variant_name VARCHAR(50) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    
    -- 关键指标
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    watch_time_minutes DECIMAL(10,2) DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    
    -- 时间戳
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hours_since_publish INT DEFAULT 0,
    
    FOREIGN KEY (strategy_id) REFERENCES publish_strategies(strategy_id),
    FOREIGN KEY (task_id) REFERENCES auto_publish_tasks(task_id),
    
    INDEX idx_strategy_variant (strategy_id, variant_name),
    INDEX idx_measured (measured_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- 初始数据
-- =====================================================

-- 插入默认Pipeline
INSERT INTO pipeline_registry (pipeline_id, pipeline_name, pipeline_type, pipeline_class, config_schema, supported_platforms) VALUES
('story_v3', '故事生成Pipeline V3', 'story', 'pipeline_v3.StoryPipelineV3', 
 '{"video_id": "string", "duration": "integer", "gender": "integer"}',
 '["youtube", "bilibili"]'),
('news_v1', '新闻汇总Pipeline', 'news', 'pipeline_news.NewsPipeline', 
 '{"topics": "array", "duration": "integer"}',
 '["youtube", "tiktok"]');

-- 插入默认账号组
INSERT INTO account_groups (group_id, group_name, group_type, description) VALUES
('default_group', '默认账号组', 'production', '默认生产账号组'),
('test_group', '测试账号组', 'test', '用于测试的账号组');

-- 插入默认策略
INSERT INTO publish_strategies (strategy_id, strategy_name, strategy_type, parameters) VALUES
('round_robin', '轮流发布', 'round_robin', '{"rotation": "sequential"}'),
('ab_test_1', 'A/B测试-标题优化', 'ab_test', '{"variants": ["control", "variant_a"], "metric": "ctr"}');

-- =====================================================
-- 存储过程
-- =====================================================

DELIMITER $$

-- 生成环形调度槽位
CREATE PROCEDURE generate_ring_slots(
    IN p_config_id VARCHAR(50),
    IN p_date DATE,
    IN p_start_hour INT,
    IN p_end_hour INT,
    IN p_accounts JSON
)
BEGIN
    DECLARE account_count INT;
    DECLARE total_minutes INT;
    DECLARE interval_minutes INT;
    DECLARE current_minute INT DEFAULT 0;
    DECLARE i INT DEFAULT 0;
    DECLARE account_id VARCHAR(50);
    
    -- 计算参数
    SET account_count = JSON_LENGTH(p_accounts);
    SET total_minutes = (p_end_hour - p_start_hour) * 60;
    SET interval_minutes = FLOOR(total_minutes / account_count);
    
    -- 生成槽位
    WHILE i < account_count DO
        SET account_id = JSON_UNQUOTE(JSON_EXTRACT(p_accounts, CONCAT('$[', i, ']')));
        
        INSERT INTO ring_schedule_slots (
            config_id, account_id, slot_date,
            slot_hour, slot_minute, slot_index
        ) VALUES (
            p_config_id, account_id, p_date,
            p_start_hour + FLOOR(current_minute / 60),
            current_minute MOD 60,
            i
        ) ON DUPLICATE KEY UPDATE
            slot_index = i,
            status = 'pending';
        
        SET current_minute = current_minute + interval_minutes;
        SET i = i + 1;
    END WHILE;
END$$

-- 获取下一个执行槽位
CREATE FUNCTION get_next_slot(p_config_id VARCHAR(50))
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE next_slot_id INT;
    
    SELECT slot_id INTO next_slot_id
    FROM ring_schedule_slots
    WHERE config_id = p_config_id
      AND status = 'pending'
      AND slot_date >= CURDATE()
      AND (slot_date > CURDATE() OR 
           (slot_date = CURDATE() AND 
            slot_hour * 60 + slot_minute >= HOUR(NOW()) * 60 + MINUTE(NOW())))
    ORDER BY slot_date, slot_hour, slot_minute
    LIMIT 1;
    
    RETURN next_slot_id;
END$$

DELIMITER ;

-- =====================================================
-- 索引优化
-- =====================================================

-- 为高频查询添加复合索引
CREATE INDEX idx_task_status_time ON auto_publish_tasks(pipeline_status, publish_status, scheduled_at);
CREATE INDEX idx_slot_lookup ON ring_schedule_slots(config_id, status, slot_date, slot_hour);
CREATE INDEX idx_monitor_active ON platform_monitors(is_active, last_check, check_interval);

-- =====================================================
-- 触发器
-- =====================================================

DELIMITER $$

-- 自动更新updated_at字段
CREATE TRIGGER update_pipeline_registry_timestamp 
BEFORE UPDATE ON pipeline_registry
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

CREATE TRIGGER update_account_groups_timestamp 
BEFORE UPDATE ON account_groups
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

CREATE TRIGGER update_publish_configs_timestamp 
BEFORE UPDATE ON publish_configs
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;