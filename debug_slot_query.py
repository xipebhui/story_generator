#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试槽位查询
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from database import get_db_manager, init_database
from sqlalchemy import text

# 加载环境变量
from config_loader import load_env_file
load_env_file()

def debug_query():
    """调试查询"""
    init_database()
    db = get_db_manager()
    
    config_id = "config_20250906224223_32e8650d"
    current_time = datetime.now()
    
    print(f"当前时间: {current_time}")
    print(f"当前日期: {current_time.date()}")
    print(f"当前小时: {current_time.hour}")
    print(f"当前分钟: {current_time.minute}")
    
    with db.get_session() as session:
        # 查看所有槽位
        print(f"\n所有槽位:")
        result = session.execute(text("""
            SELECT slot_id, slot_date, slot_hour, slot_minute, status, account_id
            FROM ring_schedule_slots
            WHERE config_id = :config_id
        """), {"config_id": config_id}).fetchall()
        
        for row in result:
            print(f"  ID={row[0]}, 日期={row[1]}, 时间={row[2]:02d}:{row[3]:02d}, 状态={row[4]}, 账号={row[5]}")
        
        # 模拟get_next_slot的查询
        print(f"\n模拟get_next_slot查询:")
        print(f"  查询条件:")
        print(f"    config_id = {config_id}")
        print(f"    status = pending")
        print(f"    日期时间 >= 当前时间")
        
        query_result = session.execute(text("""
            SELECT slot_id, slot_date, slot_hour, slot_minute, status
            FROM ring_schedule_slots
            WHERE config_id = :config_id
            AND status = 'pending'
            AND (
                slot_date > :current_date
                OR (slot_date = :current_date AND slot_hour > :current_hour)
                OR (slot_date = :current_date AND slot_hour = :current_hour AND slot_minute >= :current_minute)
            )
            ORDER BY slot_date, slot_hour, slot_minute
            LIMIT 1
        """), {
            "config_id": config_id,
            "current_date": current_time.date(),
            "current_hour": current_time.hour,
            "current_minute": current_time.minute
        }).fetchone()
        
        if query_result:
            print(f"\n找到槽位:")
            print(f"  ID={query_result[0]}, {query_result[1]} {query_result[2]:02d}:{query_result[3]:02d}")
        else:
            print(f"\n没有找到符合条件的槽位")
            print(f"\n原因分析:")
            print(f"  槽位日期: 2025-09-06")
            print(f"  槽位时间: 22:44")
            print(f"  当前日期: {current_time.date()}")
            print(f"  当前时间: {current_time.hour:02d}:{current_time.minute:02d}")
            
            if current_time.date() == datetime(2025, 9, 6).date():
                if current_time.hour > 22 or (current_time.hour == 22 and current_time.minute > 44):
                    print(f"  -> 槽位时间已过（当前时间 > 22:44）")
                else:
                    print(f"  -> 槽位时间未到")
            else:
                print(f"  -> 日期不匹配")

if __name__ == "__main__":
    debug_query()