#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建视频源追踪表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import get_db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_video_sources_table():
    """创建视频源表"""
    db = get_db_manager()
    engine = db.engine
    
    # 创建表的SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS video_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform VARCHAR(50) NOT NULL,
        creator_id VARCHAR(255) NOT NULL,
        video_id VARCHAR(255) NOT NULL,
        video_url TEXT,
        cover_url TEXT,
        title TEXT,
        description TEXT,
        published_at DATETIME NOT NULL,
        fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        processed_at DATETIME,
        status VARCHAR(50) DEFAULT 'pending',
        process_error TEXT,
        metadata TEXT,
        UNIQUE(platform, creator_id, video_id)
    );
    """
    
    # 创建索引的SQL
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_platform_creator ON video_sources(platform, creator_id);",
        "CREATE INDEX IF NOT EXISTS idx_platform_video ON video_sources(platform, video_id);",
        "CREATE INDEX IF NOT EXISTS idx_status_published ON video_sources(status, published_at);",
        "CREATE INDEX IF NOT EXISTS idx_creator_status ON video_sources(creator_id, status);",
    ]
    
    try:
        with engine.connect() as conn:
            # 创建表
            conn.execute(text(create_table_sql))
            logger.info("Created video_sources table")
            
            # 创建索引
            for index_sql in create_indexes_sql:
                conn.execute(text(index_sql))
            logger.info("Created indexes for video_sources table")
            
            conn.commit()
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    create_video_sources_table()