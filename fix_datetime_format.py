#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库中的日期时间格式问题
"""

import sqlite3
import os
import sys
from datetime import datetime
import re

def fix_datetime_fields(db_path):
    """修复publish_tasks表中的日期时间格式"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("连接到数据库成功")
        
        # 获取所有publish_tasks记录
        cursor.execute("""
            SELECT id, created_at, upload_started_at, upload_completed_at, scheduled_time
            FROM publish_tasks
        """)
        
        tasks = cursor.fetchall()
        print(f"找到 {len(tasks)} 条发布记录")
        
        fixed_count = 0
        
        for task in tasks:
            task_id = task[0]
            updates = []
            params = []
            
            # 检查每个日期字段
            for i, field_name in enumerate(['created_at', 'upload_started_at', 'upload_completed_at', 'scheduled_time'], 1):
                date_str = task[i]
                if date_str:
                    # 检查格式是否正确
                    if 'T' in date_str and '.' in date_str:
                        # ISO格式，需要转换为SQLite格式
                        try:
                            # 解析ISO格式
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            # 转换为SQLite格式 (YYYY-MM-DD HH:MM:SS)
                            sqlite_format = dt.strftime('%Y-%m-%d %H:%M:%S')
                            updates.append(f"{field_name} = ?")
                            params.append(sqlite_format)
                            print(f"  修复记录 {task_id} 的 {field_name}: {date_str} -> {sqlite_format}")
                        except Exception as e:
                            print(f"  警告：无法解析日期 {date_str}: {e}")
            
            # 执行更新
            if updates:
                sql = f"UPDATE publish_tasks SET {', '.join(updates)} WHERE id = ?"
                params.append(task_id)
                cursor.execute(sql, params)
                fixed_count += 1
        
        # 提交更改
        conn.commit()
        
        print(f"\n修复完成！共修复了 {fixed_count} 条记录")
        
        # 验证修复结果
        cursor.execute("SELECT id, created_at FROM publish_tasks LIMIT 3")
        examples = cursor.fetchall()
        print("\n修复后的示例:")
        for task_id, created_at in examples:
            print(f"  记录 {task_id}: {created_at}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
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
            print("找不到数据库文件")
            sys.exit(1)
    
    print("="*60)
    print("修复数据库日期时间格式")
    print("="*60)
    print(f"数据库路径: {os.path.abspath(db_path)}\n")
    
    # 创建备份
    from datetime import datetime
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"已创建备份: {backup_path}\n")
    except Exception as e:
        print(f"警告：创建备份失败: {e}\n")
    
    fix_datetime_fields(db_path)

if __name__ == "__main__":
    main()