#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
执行自动发布系统的数据库表创建
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_path():
    """获取数据库路径"""
    # 优先使用环境变量
    db_path = os.environ.get('DB_PATH')
    if db_path:
        return db_path
    
    # 默认路径
    return './data/pipeline_tasks.db'

def read_migration_sql():
    """读取迁移SQL文件"""
    # 优先使用SQLite版本
    migration_file = Path(__file__).parent / 'migrations' / 'add_auto_publish_tables_sqlite.sql'
    
    if not migration_file.exists():
        # 如果SQLite版本不存在，使用原始版本
        migration_file = Path(__file__).parent / 'migrations' / 'add_auto_publish_tables.sql'
        logger.warning(f"SQLite版本不存在，使用原始MySQL版本: {migration_file}")
        
        if not migration_file.exists():
            logger.error(f"迁移文件不存在: {migration_file}")
            sys.exit(1)
    else:
        logger.info(f"使用SQLite版本迁移文件: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        return f.read()

def execute_migration(db_path, sql_content):
    """执行数据库迁移"""
    # 确保数据库目录存在
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # SQLite不支持某些MySQL语法，需要转换
        sql_content = convert_mysql_to_sqlite(sql_content)
        
        # 分割SQL语句并分类
        statements = sql_content.split(';')
        create_tables = []
        create_indexes = []
        create_triggers = []
        inserts = []
        
        for statement in statements:
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue
            
            # 分类SQL语句
            upper_stmt = statement.upper()
            if 'CREATE TABLE' in upper_stmt:
                create_tables.append(statement)
            elif 'CREATE INDEX' in upper_stmt:
                create_indexes.append(statement)
            elif 'CREATE TRIGGER' in upper_stmt:
                create_triggers.append(statement)
            elif 'INSERT' in upper_stmt:
                inserts.append(statement)
        
        # 按顺序执行：先创建表，再创建索引，再创建触发器，最后插入数据
        logger.info(f"准备创建 {len(create_tables)} 个表")
        for statement in create_tables:
            try:
                cursor.execute(statement)
                logger.info(f"创建表成功: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    logger.info(f"表已存在: {statement[:50]}...")
                else:
                    logger.error(f"创建表失败: {e}")
                    logger.error(f"SQL: {statement[:200]}...")
        
        logger.info(f"准备创建 {len(create_indexes)} 个索引")
        for statement in create_indexes:
            try:
                cursor.execute(statement)
                logger.info(f"创建索引成功: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    logger.info(f"索引已存在: {statement[:50]}...")
                else:
                    logger.error(f"创建索引失败: {e}")
                    logger.error(f"SQL: {statement[:200]}...")
        
        logger.info(f"准备创建 {len(create_triggers)} 个触发器")
        for statement in create_triggers:
            try:
                cursor.execute(statement)
                logger.info(f"创建触发器成功: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    logger.info(f"触发器已存在: {statement[:50]}...")
                else:
                    logger.error(f"创建触发器失败: {e}")
                    logger.error(f"SQL: {statement[:200]}...")
        
        logger.info(f"准备插入 {len(inserts)} 条数据")
        for statement in inserts:
            try:
                cursor.execute(statement)
                logger.info(f"插入数据成功: {statement[:50]}...")
            except sqlite3.Error as e:
                logger.warning(f"插入数据失败（可能已存在）: {e}")
        
        conn.commit()
        logger.info("数据库迁移成功完成")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        conn.close()

def convert_mysql_to_sqlite(sql_content):
    """将MySQL语法转换为SQLite语法"""
    # 如果已经是SQLite格式（包含CREATE INDEX IF NOT EXISTS），直接返回
    if 'CREATE INDEX IF NOT EXISTS' in sql_content:
        logger.info("检测到SQLite格式SQL，跳过转换")
        return sql_content
    
    # 移除MySQL特定的语法
    replacements = [
        ('ENGINE=InnoDB', ''),
        ('DEFAULT CHARSET=utf8mb4', ''),
        ('AUTO_INCREMENT', 'AUTOINCREMENT'),
        ('INT AUTO_INCREMENT', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 
         "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 
         "TIMESTAMP DEFAULT (datetime('now'))"),
        ('JSON', 'TEXT'),  # SQLite没有JSON类型，使用TEXT
        ('DECIMAL(', 'REAL('),  # SQLite使用REAL代替DECIMAL
        ('UNIQUE KEY', 'UNIQUE'),
        ('INDEX ', 'CREATE INDEX IF NOT EXISTS '),
        ('KEY ', ''),  # 移除KEY关键字
        ('FOREIGN KEY', '--FOREIGN KEY'),  # 注释掉外键（可选）
    ]
    
    for old, new in replacements:
        sql_content = sql_content.replace(old, new)
    
    return sql_content

def check_tables_created(db_path):
    """检查表是否创建成功"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    expected_tables = [
        'pipeline_registry',
        'account_groups',
        'account_group_members',
        'publish_configs',
        'ring_schedule_slots',
        'publish_strategies',
        'strategy_assignments',
        'platform_monitors',
        'monitor_results',
        'auto_publish_tasks',
        'strategy_metrics'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    created_tables = []
    missing_tables = []
    
    for table in expected_tables:
        if table in existing_tables:
            created_tables.append(table)
        else:
            missing_tables.append(table)
    
    conn.close()
    
    logger.info(f"已创建的表 ({len(created_tables)}): {', '.join(created_tables)}")
    if missing_tables:
        logger.warning(f"缺失的表 ({len(missing_tables)}): {', '.join(missing_tables)}")
    
    return len(missing_tables) == 0

def insert_sample_data(db_path):
    """插入示例数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 插入默认Pipeline
        cursor.execute("""
            INSERT OR IGNORE INTO pipeline_registry (
                pipeline_id, pipeline_name, pipeline_type, pipeline_class, 
                config_schema, supported_platforms, version, status
            ) VALUES 
            ('story_v3', '故事生成Pipeline V3', 'story', 'pipeline_v3.StoryPipelineV3', 
             '{"video_id": "string", "duration": "integer", "gender": "integer"}',
             '["youtube", "bilibili"]', '1.0.0', 'active'),
            ('news_v1', '新闻汇总Pipeline', 'news', 'pipeline_news.NewsPipeline', 
             '{"topics": "array", "duration": "integer"}',
             '["youtube", "tiktok"]', '1.0.0', 'active')
        """)
        
        # 插入默认账号组
        cursor.execute("""
            INSERT OR IGNORE INTO account_groups (
                group_id, group_name, group_type, description, is_active
            ) VALUES 
            ('default_group', '默认账号组', 'production', '默认生产账号组', 1),
            ('test_group', '测试账号组', 'test', '用于测试的账号组', 1)
        """)
        
        # 插入默认策略
        cursor.execute("""
            INSERT OR IGNORE INTO publish_strategies (
                strategy_id, strategy_name, strategy_type, parameters
            ) VALUES 
            ('round_robin', '轮流发布', 'round_robin', '{"rotation": "sequential"}'),
            ('ab_test_1', 'A/B测试-标题优化', 'ab_test', '{"variants": ["control", "variant_a"], "metric": "ctr"}')
        """)
        
        conn.commit()
        logger.info("示例数据插入成功")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"插入示例数据失败: {e}")
    finally:
        conn.close()

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始执行数据库迁移")
    logger.info("=" * 60)
    
    # 获取数据库路径
    db_path = get_db_path()
    logger.info(f"数据库路径: {db_path}")
    
    # 读取迁移SQL
    logger.info("读取迁移SQL文件...")
    sql_content = read_migration_sql()
    
    # 执行迁移
    logger.info("执行数据库迁移...")
    execute_migration(db_path, sql_content)
    
    # 检查表创建情况
    logger.info("检查表创建情况...")
    success = check_tables_created(db_path)
    
    if success:
        # 插入示例数据
        logger.info("插入示例数据...")
        insert_sample_data(db_path)
        
        logger.info("=" * 60)
        logger.info("✅ 数据库迁移成功完成！")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("❌ 数据库迁移未完全成功，请检查日志")
        logger.error("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()