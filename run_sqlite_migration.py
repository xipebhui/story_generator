#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接执行SQLite迁移脚本
"""

import sqlite3
import os
from pathlib import Path

def main():
    # 确保数据库目录存在
    os.makedirs("./data", exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect("./data/pipeline_tasks.db")
    cursor = conn.cursor()
    
    # 读取SQL文件
    sql_file = Path("migrations/add_auto_publish_tables_sqlite.sql")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 直接执行整个脚本
    try:
        cursor.executescript(sql_content)
        conn.commit()
        print("✅ 数据库迁移成功！")
        
        # 检查创建的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"创建的表 ({len(tables)}): {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
