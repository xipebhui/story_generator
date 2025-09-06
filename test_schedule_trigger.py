#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试调度触发工具
支持创建立即触发或指定时间触发的配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from ring_scheduler import get_ring_scheduler
from database import init_database, get_db_manager
from sqlalchemy import text
import json
import argparse

# 加载环境变量
from config_loader import load_env_file
load_env_file()

def create_test_config(trigger_time_str=None, interval_minutes=None):
    """
    创建测试配置
    
    Args:
        trigger_time_str: 触发时间字符串，格式 "HH:MM" 或 "now" 表示立即
        interval_minutes: 间隔分钟数，如果设置则创建间隔触发
    """
    init_database()
    db = get_db_manager()
    ring_scheduler = get_ring_scheduler()
    
    # 生成配置ID
    config_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确定触发类型和时间
    if trigger_time_str == "now":
        # 立即触发（2分钟后）
        trigger_time = datetime.now() + timedelta(minutes=2)
        config_name = f"测试立即触发_{trigger_time.strftime('%H:%M')}"
        print(f"创建立即触发配置，将在 {trigger_time.strftime('%H:%M:%S')} 执行")
    elif trigger_time_str:
        # 指定时间触发
        hour, minute = map(int, trigger_time_str.split(':'))
        trigger_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if trigger_time < datetime.now():
            trigger_time += timedelta(days=1)  # 如果时间已过，设置为明天
        config_name = f"测试定时触发_{trigger_time.strftime('%H:%M')}"
        print(f"创建定时触发配置，将在 {trigger_time.strftime('%Y-%m-%d %H:%M')} 执行")
    elif interval_minutes:
        # 间隔触发
        config_name = f"测试间隔触发_每{interval_minutes}分钟"
        print(f"创建间隔触发配置，每 {interval_minutes} 分钟执行一次")
    else:
        print("请指定触发方式")
        return
    
    with db.get_session() as session:
        try:
            # 1. 创建配置
            if interval_minutes:
                trigger_config = {
                    "schedule_type": "interval",
                    "schedule_interval": interval_minutes,
                    "schedule_interval_unit": "minutes"
                }
            else:
                trigger_config = {
                    "schedule_type": "once",
                    "scheduled_time": trigger_time.isoformat()
                }
            
            # 插入配置
            session.execute(text("""
                INSERT INTO publish_configs (
                    config_id, config_name, group_id, pipeline_id,
                    pipeline_config, trigger_type, trigger_config,
                    strategy_id, priority, is_active, created_at, updated_at
                ) VALUES (
                    :config_id, :config_name, :group_id, :pipeline_id,
                    :pipeline_config, :trigger_type, :trigger_config,
                    :strategy_id, :priority, :is_active, :created_at, :updated_at
                )
            """), {
                "config_id": config_id,
                "config_name": config_name,
                "group_id": "group_20250903165020",  # 使用默认组
                "pipeline_id": "story_gen_v5",
                "pipeline_config": json.dumps({"test": True}),
                "trigger_type": "scheduled",
                "trigger_config": json.dumps(trigger_config),
                "strategy_id": None,
                "priority": 100,  # 高优先级
                "is_active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            
            # 2. 获取账号
            accounts = session.execute(text("""
                SELECT a.account_id FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                WHERE agm.group_id = :group_id AND a.is_active = 1
                LIMIT 1
            """), {"group_id": "group_20250903165020"}).fetchall()
            
            if not accounts:
                print("错误：没有找到活跃账号")
                session.rollback()
                return
            
            account_id = accounts[0][0]
            
            # 3. 生成时间槽
            if interval_minutes:
                # 间隔触发
                interval_hours = interval_minutes / 60
                slots = ring_scheduler.generate_interval_slots(
                    config_id=config_id,
                    account_id=account_id,
                    interval_hours=interval_hours,
                    config_index=0,
                    total_configs=1,
                    days_ahead=1  # 只生成1天的槽位
                )
            else:
                # 单次触发
                from ring_scheduler import TimeSlot
                slots = [TimeSlot(
                    slot_id=None,
                    config_id=config_id,
                    account_id=account_id,
                    slot_date=trigger_time.date(),
                    slot_time=trigger_time.time(),
                    slot_index=0,
                    status="pending",
                    metadata={"trigger_type": "once"}
                )]
            
            # 4. 保存时间槽
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
            
            print(f"\n✅ 成功创建配置:")
            print(f"  配置ID: {config_id}")
            print(f"  配置名称: {config_name}")
            print(f"  账号: {account_id}")
            print(f"  生成槽位数: {len(slots)}")
            
            if slots:
                print(f"\n  前3个时间槽:")
                for i, slot in enumerate(slots[:3]):
                    print(f"    {i+1}. {slot.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return config_id
            
        except Exception as e:
            session.rollback()
            print(f"❌ 创建失败: {e}")
            return None


def list_configs():
    """列出所有活跃的配置"""
    db = get_db_manager()
    
    with db.get_session() as session:
        configs = session.execute(text("""
            SELECT 
                pc.config_id,
                pc.config_name,
                pc.trigger_config,
                pc.is_active,
                COUNT(rss.slot_id) as slot_count,
                MIN(rss.slot_date || ' ' || printf('%02d:%02d', rss.slot_hour, rss.slot_minute)) as next_slot
            FROM publish_configs pc
            LEFT JOIN ring_schedule_slots rss ON pc.config_id = rss.config_id AND rss.status = 'pending'
            WHERE pc.trigger_type = 'scheduled'
            GROUP BY pc.config_id
            ORDER BY pc.created_at DESC
        """)).fetchall()
        
        print("\n" + "="*80)
        print("当前调度配置")
        print("="*80)
        
        for config in configs:
            config_id = config[0]
            config_name = config[1]
            trigger_config = json.loads(config[2]) if config[2] else {}
            is_active = config[3]
            slot_count = config[4]
            next_slot = config[5]
            
            status = "✅ 活跃" if is_active else "⏸️  暂停"
            
            print(f"\n{status} {config_name}")
            print(f"  ID: {config_id}")
            print(f"  类型: {trigger_config.get('schedule_type', 'unknown')}")
            print(f"  待执行槽位: {slot_count}")
            if next_slot:
                print(f"  下次执行: {next_slot}")


def cleanup_configs():
    """清理所有测试配置"""
    db = get_db_manager()
    
    with db.get_session() as session:
        # 删除测试配置的时间槽
        session.execute(text("""
            DELETE FROM ring_schedule_slots 
            WHERE config_id LIKE 'test_%'
        """))
        
        # 删除测试配置
        result = session.execute(text("""
            DELETE FROM publish_configs 
            WHERE config_id LIKE 'test_%'
        """))
        
        session.commit()
        
        print(f"✅ 清理了测试配置")


def main():
    parser = argparse.ArgumentParser(description='测试调度触发工具')
    parser.add_argument('action', choices=['create', 'list', 'cleanup'], 
                       help='操作类型')
    parser.add_argument('--time', help='触发时间 (HH:MM) 或 "now" 表示立即')
    parser.add_argument('--interval', type=int, help='间隔分钟数')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        if args.time or args.interval:
            create_test_config(args.time, args.interval)
        else:
            print("请指定 --time 或 --interval 参数")
            print("示例:")
            print("  python test_schedule_trigger.py create --time now      # 2分钟后触发")
            print("  python test_schedule_trigger.py create --time 14:30    # 14:30触发")
            print("  python test_schedule_trigger.py create --interval 30   # 每30分钟触发")
    
    elif args.action == 'list':
        list_configs()
    
    elif args.action == 'cleanup':
        cleanup_configs()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("测试调度触发工具")
        print("="*50)
        print("\n使用方法:")
        print("  # 创建立即触发（2分钟后）")
        print("  python test_schedule_trigger.py create --time now")
        print("\n  # 创建指定时间触发")
        print("  python test_schedule_trigger.py create --time 14:30")
        print("\n  # 创建间隔触发")  
        print("  python test_schedule_trigger.py create --interval 30")
        print("\n  # 列出所有配置")
        print("  python test_schedule_trigger.py list")
        print("\n  # 清理测试配置")
        print("  python test_schedule_trigger.py cleanup")
    else:
        main()