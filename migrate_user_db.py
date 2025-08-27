#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 为现有用户表添加新字段
"""

import sqlite3
import os
import sys
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

def migrate_database(db_path):
    """执行数据库迁移"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"连接到数据库: {db_path}")
        
        # 检查users表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            logger.warning("users表不存在，跳过迁移")
            return True
        
        # 添加status字段（如果不存在）
        if not check_column_exists(cursor, 'users', 'status'):
            logger.info("添加status字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL
            """)
            logger.info("✅ status字段添加成功")
        else:
            logger.info("status字段已存在，跳过")
        
        # 添加last_login字段（如果不存在）
        if not check_column_exists(cursor, 'users', 'last_login'):
            logger.info("添加last_login字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_login DATETIME
            """)
            logger.info("✅ last_login字段添加成功")
        else:
            logger.info("last_login字段已存在，跳过")
        
        # 更新现有用户的status为active（如果有is_active字段）
        if check_column_exists(cursor, 'users', 'is_active'):
            logger.info("根据is_active字段更新status...")
            cursor.execute("""
                UPDATE users 
                SET status = CASE 
                    WHEN is_active = 1 THEN 'active' 
                    ELSE 'inactive' 
                END
                WHERE status IS NULL OR status = ''
            """)
            affected_rows = cursor.rowcount
            logger.info(f"✅ 更新了{affected_rows}个用户的status")
        
        # 提交更改
        conn.commit()
        
        # 显示当前表结构
        logger.info("\n当前users表结构:")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            logger.info(f"  {col[1]} - {col[2]}")
        
        # 显示用户统计
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"\n用户总数: {user_count}")
        
        if check_column_exists(cursor, 'users', 'status'):
            cursor.execute("SELECT status, COUNT(*) FROM users GROUP BY status")
            status_stats = cursor.fetchall()
            if status_stats:
                logger.info("用户状态分布:")
                for status, count in status_stats:
                    logger.info(f"  {status}: {count}")
        
        conn.close()
        logger.info("\n✅ 数据库迁移完成!")
        return True
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    # 获取数据库路径
    db_path = os.environ.get('DB_PATH', './data/pipeline_tasks.db')
    
    if not os.path.exists(db_path):
        # 尝试其他可能的路径
        possible_paths = [
            './data/pipeline_tasks.db',
            '../data/pipeline_tasks.db',
            './pipeline_tasks.db',
            '../pipeline_tasks.db'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
        else:
            logger.error("找不到数据库文件，请确保数据库文件存在")
            logger.info(f"尝试过的路径: {possible_paths}")
            sys.exit(1)
    
    logger.info("="*60)
    logger.info("数据库迁移工具 - 添加用户新字段")
    logger.info("="*60)
    logger.info(f"\n数据库路径: {os.path.abspath(db_path)}")
    
    # 创建备份
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"已创建备份: {backup_path}")
    except Exception as e:
        logger.warning(f"创建备份失败: {e}")
        response = input("是否继续迁移？(y/n): ")
        if response.lower() != 'y':
            logger.info("取消迁移")
            sys.exit(0)
    
    # 执行迁移
    if migrate_database(db_path):
        logger.info("\n迁移成功！新字段已添加到users表。")
        logger.info("注意：")
        logger.info("1. status字段默认值为'active'")
        logger.info("2. last_login字段在用户首次登录后会自动更新")
        logger.info("3. 备份文件保存在: " + backup_path)
    else:
        logger.error("\n迁移失败！数据库未更改。")
        logger.info(f"如需恢复，可使用备份文件: {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()