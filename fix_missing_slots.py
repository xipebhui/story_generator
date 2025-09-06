#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复缺失的时间槽
为已创建但没有时间槽的配置补充生成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from ring_scheduler import get_ring_scheduler
from database import init_database, get_db_manager
from sqlalchemy import text
import json

# 加载环境变量
from config_loader import load_env_file
load_env_file()

def fix_interval_config_slots():
    """修复interval类型配置的时间槽"""
    print("修复interval类型配置的时间槽...")
    
    init_database()
    db = get_db_manager()
    ring_scheduler = get_ring_scheduler()
    
    with db.get_session() as session:
        # 查找interval类型但没有时间槽的配置
        configs = session.execute(text("""
            SELECT pc.config_id, pc.config_name, pc.group_id, pc.trigger_config
            FROM publish_configs pc
            WHERE pc.trigger_type = 'scheduled'
            AND pc.is_active = 1
            AND JSON_EXTRACT(pc.trigger_config, '$.schedule_type') = 'interval'
            AND NOT EXISTS (
                SELECT 1 FROM ring_schedule_slots rss 
                WHERE rss.config_id = pc.config_id
            )
        """)).fetchall()
        
        print(f"找到 {len(configs)} 个需要修复的interval配置")
        
        for config in configs:
            config_id = config[0]
            config_name = config[1]
            group_id = config[2]
            trigger_config = json.loads(config[3])
            
            print(f"\n处理配置: {config_name} ({config_id})")
            print(f"  触发配置: {trigger_config}")
            
            # 获取账号
            accounts = session.execute(text("""
                SELECT a.account_id FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                WHERE agm.group_id = :group_id AND a.is_active = 1
                LIMIT 1
            """), {"group_id": group_id}).fetchall()
            
            if not accounts:
                print(f"  ✗ 组 {group_id} 没有活跃账号")
                continue
            
            account_id = accounts[0][0]
            
            # 计算间隔
            interval_value = trigger_config.get('interval', trigger_config.get('schedule_interval', 1))
            interval_unit = trigger_config.get('unit', trigger_config.get('schedule_interval_unit', 'hours'))
            
            if interval_unit == 'minutes':
                interval_hours = interval_value / 60
            elif interval_unit == 'hours':
                interval_hours = interval_value
            elif interval_unit == 'days':
                interval_hours = interval_value * 24
            else:
                interval_hours = 1
            
            print(f"  账号: {account_id}")
            print(f"  间隔: {interval_value} {interval_unit} = {interval_hours} 小时")
            
            # 生成时间槽
            slots = ring_scheduler.generate_interval_slots(
                config_id=config_id,
                account_id=account_id,
                interval_hours=interval_hours,
                config_index=0,
                total_configs=1,
                days_ahead=7
            )
            
            print(f"  生成了 {len(slots)} 个时间槽")
            
            # 保存时间槽
            for slot in slots:
                session.execute(text("""
                    INSERT INTO ring_schedule_slots (
                        config_id, account_id, slot_date, 
                        slot_hour, slot_minute, slot_index,
                        status, metadata
                    ) VALUES (
                        :config_id, :account_id, :slot_date,
                        :slot_hour, :slot_minute, :slot_index,
                        :status, :metadata
                    )
                """), {
                    "config_id": slot.config_id,
                    "account_id": slot.account_id,
                    "slot_date": slot.slot_date,
                    "slot_hour": slot.slot_time.hour,
                    "slot_minute": slot.slot_time.minute,
                    "slot_index": slot.slot_index,
                    "status": slot.status,
                    "metadata": json.dumps(slot.metadata) if slot.metadata else None
                })
            
            session.commit()
            print(f"  ✓ 成功保存时间槽")
            
            # 显示前3个时间槽
            if slots:
                print(f"  前3个时间槽:")
                for i, slot in enumerate(slots[:3]):
                    print(f"    {i+1}. {slot.datetime.strftime('%Y-%m-%d %H:%M')}")


def implement_daily_schedule():
    """实现daily类型的调度（简单版本）"""
    print("\n处理daily类型配置...")
    
    db = get_db_manager()
    ring_scheduler = get_ring_scheduler()
    
    with db.get_session() as session:
        # 查找daily类型的配置
        configs = session.execute(text("""
            SELECT pc.config_id, pc.config_name, pc.group_id, pc.trigger_config
            FROM publish_configs pc
            WHERE pc.trigger_type = 'scheduled'
            AND pc.is_active = 1
            AND JSON_EXTRACT(pc.trigger_config, '$.schedule_type') = 'daily'
        """)).fetchall()
        
        print(f"找到 {len(configs)} 个daily配置")
        
        for config in configs:
            config_id = config[0]
            config_name = config[1]
            group_id = config[2]
            trigger_config = json.loads(config[3])
            
            print(f"\n处理配置: {config_name} ({config_id})")
            print(f"  每日时间: {trigger_config.get('time', 'unknown')}")
            
            # 获取账号
            accounts = session.execute(text("""
                SELECT a.account_id FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                WHERE agm.group_id = :group_id AND a.is_active = 1
                LIMIT 1
            """), {"group_id": group_id}).fetchall()
            
            if not accounts:
                print(f"  ✗ 组 {group_id} 没有活跃账号")
                continue
            
            account_id = accounts[0][0]
            
            # 将daily转换为24小时间隔
            # 这是一个简化实现，实际应该在指定时间执行
            slots = ring_scheduler.generate_interval_slots(
                config_id=config_id,
                account_id=account_id,
                interval_hours=24,  # 每24小时
                config_index=0,
                total_configs=1,
                days_ahead=7
            )
            
            print(f"  生成了 {len(slots)} 个时间槽（每24小时）")
            
            # 保存时间槽
            for slot in slots:
                session.execute(text("""
                    INSERT INTO ring_schedule_slots (
                        config_id, account_id, slot_date, 
                        slot_hour, slot_minute, slot_index,
                        status, metadata
                    ) VALUES (
                        :config_id, :account_id, :slot_date,
                        :slot_hour, :slot_minute, :slot_index,
                        :status, :metadata
                    )
                """), {
                    "config_id": slot.config_id,
                    "account_id": slot.account_id,
                    "slot_date": slot.slot_date,
                    "slot_hour": slot.slot_time.hour,
                    "slot_minute": slot.slot_time.minute,
                    "slot_index": slot.slot_index,
                    "status": slot.status,
                    "metadata": json.dumps({"schedule_type": "daily"})
                })
            
            session.commit()
            print(f"  ✓ 成功保存时间槽")


def check_slots_status():
    """检查时间槽状态"""
    print("\n" + "="*60)
    print("时间槽状态检查")
    print("="*60)
    
    db = get_db_manager()
    
    with db.get_session() as session:
        # 统计时间槽
        result = session.execute(text("""
            SELECT 
                config_id,
                COUNT(*) as total_slots,
                MIN(slot_date || ' ' || printf('%02d:%02d', slot_hour, slot_minute)) as first_slot,
                MAX(slot_date || ' ' || printf('%02d:%02d', slot_hour, slot_minute)) as last_slot
            FROM ring_schedule_slots
            WHERE status = 'pending'
            GROUP BY config_id
        """)).fetchall()
        
        if result:
            print("\n当前时间槽状态:")
            for row in result:
                print(f"  配置: {row[0][:20]}...")
                print(f"    总槽位: {row[1]}")
                print(f"    首个: {row[2]}")
                print(f"    最后: {row[3]}")
        else:
            print("没有待执行的时间槽")


if __name__ == "__main__":
    print("="*60)
    print("修复缺失的时间槽")
    print("="*60)
    
    # 修复interval配置
    fix_interval_config_slots()
    
    # 实现daily调度（简化版）
    implement_daily_schedule()
    
    # 检查状态
    check_slots_status()
    
    print("\n修复完成！")