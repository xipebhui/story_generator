#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移工具
支持SQLite到MySQL的迁移
"""

import argparse
import sys
import logging
from datetime import datetime
from database import DatabaseManager, PipelineTask, Account, PublishTask

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_sqlite_to_mysql(sqlite_path: str, mysql_url: str):
    """
    从SQLite迁移到MySQL
    
    Args:
        sqlite_path: SQLite数据库文件路径
        mysql_url: MySQL连接字符串
    """
    logger.info(f"开始迁移: SQLite -> MySQL")
    logger.info(f"源数据库: {sqlite_path}")
    logger.info(f"目标数据库: {mysql_url}")
    
    try:
        # 创建SQLite管理器
        sqlite_url = f"sqlite:///{sqlite_path}"
        sqlite_db = DatabaseManager(sqlite_url)
        
        # 执行迁移
        sqlite_db.migrate_to_mysql(mysql_url)
        
        logger.info("迁移完成!")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)


def backup_database(db_url: str, backup_path: str):
    """
    备份数据库
    
    Args:
        db_url: 数据库连接URL
        backup_path: 备份文件路径
    """
    import shutil
    
    if 'sqlite' in db_url:
        # SQLite直接复制文件
        source_path = db_url.replace('sqlite:///', '')
        shutil.copy2(source_path, backup_path)
        logger.info(f"数据库已备份到: {backup_path}")
    else:
        logger.error("目前只支持SQLite备份")


def cleanup_old_data(db_url: str, days: int = 30):
    """
    清理旧数据
    
    Args:
        db_url: 数据库连接URL
        days: 保留最近N天的数据
    """
    db = DatabaseManager(db_url)
    deleted = db.cleanup_old_tasks(days)
    logger.info(f"已删除 {deleted} 条超过 {days} 天的记录")


def main():
    parser = argparse.ArgumentParser(description='数据库迁移和管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 迁移命令
    migrate_parser = subparsers.add_parser('migrate', help='迁移数据库')
    migrate_parser.add_argument('--from', dest='source', required=True, help='源数据库路径')
    migrate_parser.add_argument('--to', dest='target', required=True, help='目标数据库URL')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--db', required=True, help='数据库URL')
    backup_parser.add_argument('--output', required=True, help='备份文件路径')
    
    # 清理命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧数据')
    cleanup_parser.add_argument('--db', required=True, help='数据库URL')
    cleanup_parser.add_argument('--days', type=int, default=30, help='保留天数（默认30天）')
    
    args = parser.parse_args()
    
    if args.command == 'migrate':
        migrate_sqlite_to_mysql(args.source, args.target)
    elif args.command == 'backup':
        backup_database(args.db, args.output)
    elif args.command == 'cleanup':
        cleanup_old_data(args.db, args.days)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()