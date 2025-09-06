#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为每日定时任务生成指定时间的槽位
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, date, time
from database import init_database, get_db_manager
from ring_scheduler import TimeSlot
from sqlalchemy import text
import json
import logging

# 加载环境变量
from config_loader import load_env_file
load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_daily_slots_at_time(
    config_id: str,
    account_id: str,
    scheduled_time: str,  # 格式: "HH:MM"
    start_date: date = None,
    days_ahead: int = 7
) -> list:
    """
    为每日定时任务生成指定时间的槽位
    
    Args:
        config_id: 配置ID
        account_id: 账号ID
        scheduled_time: 每日执行时间，格式"HH:MM"
        start_date: 开始日期，默认今天
        days_ahead: 生成多少天的槽位
    
    Returns:
        生成的槽位列表
    """
    if start_date is None:
        start_date = date.today()
    
    # 解析时间
    hour, minute = map(int, scheduled_time.split(':'))
    
    slots = []
    for i in range(days_ahead):
        slot_date = start_date + timedelta(days=i)
        
        slot = TimeSlot(
            slot_id=None,
            config_id=config_id,
            account_id=account_id,
            slot_date=slot_date,
            slot_time=time(hour, minute),
            slot_index=i,
            status="pending",
            metadata={"schedule_type": "daily", "scheduled_time": scheduled_time}
        )
        slots.append(slot)
    
    return slots

def process_daily_configs():
    """处理所有每日定时配置，生成槽位"""
    init_database()
    db = get_db_manager()
    
    with db.get_session() as session:
        # 查找所有每日定时配置
        configs = session.execute(text("""
            SELECT pc.config_id, pc.config_name, pc.group_id, pc.trigger_config
            FROM publish_configs pc
            WHERE pc.trigger_type = 'scheduled'
            AND pc.is_active = 1
            AND JSON_EXTRACT(pc.trigger_config, '$.schedule_type') = 'daily'
        """)).fetchall()
        
        logger.info(f"找到 {len(configs)} 个每日定时配置")
        
        for config in configs:
            config_id = config[0]
            config_name = config[1]
            group_id = config[2]
            trigger_config = json.loads(config[3])
            
            scheduled_time = trigger_config.get('time', '00:00')
            logger.info(f"\n处理配置: {config_name} ({config_id})")
            logger.info(f"  每日执行时间: {scheduled_time}")
            
            # 获取账号组的账号
            accounts = session.execute(text("""
                SELECT a.account_id FROM accounts a
                JOIN account_group_members agm ON a.account_id = agm.account_id
                WHERE agm.group_id = :group_id AND a.is_active = 1
            """), {"group_id": group_id}).fetchall()
            
            if not accounts:
                logger.warning(f"  ✗ 组 {group_id} 没有活跃账号")
                continue
            
            # 为每个账号生成槽位（如果需要多账号轮流发布）
            # 这里简化为只用第一个账号
            account_id = accounts[0][0]
            logger.info(f"  使用账号: {account_id}")
            
            # 检查未来3天内的槽位情况
            end_date = date.today() + timedelta(days=3)
            existing_slots = session.execute(text("""
                SELECT slot_date FROM ring_schedule_slots
                WHERE config_id = :config_id
                AND slot_date >= :today
                AND slot_date < :end_date
                AND status IN ('pending', 'scheduled')
            """), {
                "config_id": config_id,
                "today": date.today(),
                "end_date": end_date
            }).fetchall()
            
            existing_dates = {slot[0] for slot in existing_slots}
            logger.info(f"  已有槽位日期: {sorted(existing_dates)}")
            
            # 计算需要生成的日期
            needed_dates = []
            for i in range(3):  # 只生成未来3天
                check_date = date.today() + timedelta(days=i)
                if check_date not in existing_dates:
                    needed_dates.append(check_date)
            
            if not needed_dates:
                logger.info(f"  未来3天槽位已完整，无需生成")
                continue
            
            logger.info(f"  需要生成槽位的日期: {needed_dates}")
            
            # 为缺失的日期生成槽位
            hour, minute = map(int, scheduled_time.split(':'))
            saved_count = 0
            
            for slot_date in needed_dates:
                try:
                    session.execute(text("""
                        INSERT INTO ring_schedule_slots (
                            config_id, account_id, slot_date, 
                            slot_hour, slot_minute, slot_index,
                            status, metadata, created_at, updated_at
                        ) VALUES (
                            :config_id, :account_id, :slot_date,
                            :slot_hour, :slot_minute, :slot_index,
                            :status, :metadata, datetime('now'), datetime('now')
                        )
                    """), {
                        "config_id": config_id,
                        "account_id": account_id,
                        "slot_date": slot_date,
                        "slot_hour": hour,
                        "slot_minute": minute,
                        "slot_index": 0,
                        "status": "pending",
                        "metadata": json.dumps({"schedule_type": "daily", "scheduled_time": scheduled_time})
                    })
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"    槽位 {slot_date} {scheduled_time} 已存在或保存失败: {e}")
            
            session.commit()
            logger.info(f"  ✓ 成功保存 {saved_count} 个槽位")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("生成每日定时任务槽位")
    logger.info("=" * 60)
    
    process_daily_configs()
    
    logger.info("\n槽位生成完成！")

if __name__ == "__main__":
    main()