#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动触发任务测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from account_driven_executor import get_account_driven_executor
from ring_scheduler import get_ring_scheduler
from database import init_database

# 加载环境变量
from config_loader import load_env_file
load_env_file()

def test_trigger():
    """测试触发任务"""
    print("初始化服务...")
    init_database()
    
    # 获取执行器和调度器
    executor = get_account_driven_executor()
    scheduler = get_ring_scheduler()
    
    # 获取配置的槽位
    config_id = "config_20250906224223_32e8650d"
    print(f"\n查找配置 {config_id} 的槽位...")
    
    next_slot = scheduler.get_next_slot(config_id)
    
    if next_slot:
        print(f"找到槽位:")
        print(f"  槽位ID: {next_slot.slot_id}")
        print(f"  账号: {next_slot.account_id}")
        print(f"  时间: {next_slot.datetime}")
        print(f"  状态: {next_slot.status}")
        
        # 检查是否应该执行
        from datetime import timedelta
        prepare_time = next_slot.datetime - timedelta(minutes=5)
        current_time = datetime.now()
        
        print(f"\n时间检查:")
        print(f"  当前时间: {current_time}")
        print(f"  准备时间: {prepare_time}")
        print(f"  应该执行: {current_time >= prepare_time}")
        
        if current_time >= prepare_time:
            print("\n满足执行条件，应该创建任务")
        else:
            time_diff = (prepare_time - current_time).total_seconds() / 60
            print(f"\n还需等待 {time_diff:.1f} 分钟")
    else:
        print("没有找到待执行的槽位")
        
        # 查看所有槽位
        from database import get_db_manager
        db = get_db_manager()
        with db.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT slot_id, slot_date, slot_hour, slot_minute, status
                FROM ring_schedule_slots
                WHERE config_id = :config_id
                ORDER BY slot_date DESC, slot_hour DESC, slot_minute DESC
                LIMIT 5
            """), {"config_id": config_id}).fetchall()
            
            print(f"\n最近的槽位:")
            for row in result:
                print(f"  ID={row[0]}, {row[1]} {row[2]:02d}:{row[3]:02d}, 状态={row[4]}")

if __name__ == "__main__":
    test_trigger()