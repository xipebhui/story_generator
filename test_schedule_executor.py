#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试调度执行器功能
包括间隔发布和Cron表达式发布
"""

import asyncio
import json
from datetime import datetime, timedelta
from schedule_executor import get_schedule_executor

async def test_schedule_executor():
    """测试调度执行器"""
    
    print("=" * 60)
    print("调度执行器测试")
    print("=" * 60)
    
    executor = get_schedule_executor()
    
    # 测试1: 每日定时（每天10:30）
    print("\n1. 测试每日定时调度")
    config1 = {
        "schedule_type": "daily",
        "schedule_time": "10:30"
    }
    executor.add_config("daily_test", config1)
    
    # 测试2: 间隔执行（每30分钟）
    print("\n2. 测试间隔执行调度")
    config2 = {
        "schedule_type": "interval",
        "schedule_interval": 30,
        "schedule_interval_unit": "minutes"
    }
    executor.add_config("interval_test", config2)
    
    # 测试3: Cron表达式（每小时的第0分和第30分）
    print("\n3. 测试Cron表达式调度")
    config3 = {
        "schedule_type": "cron",
        "schedule_cron": "0,30 * * * *"  # 每小时的第0分和第30分
    }
    executor.add_config("cron_test", config3)
    
    # 测试4: 每周调度（每周一、三、五的14:00）
    print("\n4. 测试每周调度")
    config4 = {
        "schedule_type": "weekly",
        "schedule_days": [1, 3, 5],  # 周一、三、五
        "schedule_time": "14:00"
    }
    executor.add_config("weekly_test", config4)
    
    # 测试5: 每月调度（每月1号和15号的09:00）
    print("\n5. 测试每月调度")
    config5 = {
        "schedule_type": "monthly",
        "schedule_dates": [1, 15],  # 1号和15号
        "schedule_time": "09:00"
    }
    executor.add_config("monthly_test", config5)
    
    # 获取并显示所有调度状态
    print("\n" + "=" * 60)
    print("所有调度配置状态：")
    print("=" * 60)
    
    status_list = executor.get_schedule_status()
    for status in status_list:
        print(f"\n配置ID: {status['config_id']}")
        print(f"  类型: {status['schedule_type']}")
        print(f"  配置: {json.dumps(status['schedule_config'], ensure_ascii=False)}")
        print(f"  激活: {status['is_active']}")
        print(f"  下次运行: {status['next_run_time']}")
    
    # 测试暂停和恢复
    print("\n" + "=" * 60)
    print("测试暂停和恢复功能")
    print("=" * 60)
    
    print("\n暂停 interval_test...")
    executor.pause_config("interval_test")
    
    print("恢复 interval_test...")
    executor.resume_config("interval_test")
    
    # 测试计算下次运行时间
    print("\n" + "=" * 60)
    print("测试下次运行时间计算")
    print("=" * 60)
    
    # 测试间隔执行的下次运行时间
    from schedule_executor import ScheduleConfig, ScheduleType
    test_config = ScheduleConfig(
        config_id="test",
        schedule_type=ScheduleType.INTERVAL,
        schedule_config={
            "schedule_interval": 2,
            "schedule_interval_unit": "hours"
        },
        last_run_time=datetime.now()
    )
    
    next_run = executor._calculate_next_run(test_config)
    print(f"\n间隔2小时执行:")
    print(f"  当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  下次运行: {next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else '无'}")
    
    # 测试Cron表达式的下次运行时间
    cron_config = ScheduleConfig(
        config_id="cron_test",
        schedule_type=ScheduleType.CRON,
        schedule_config={
            "schedule_cron": "*/15 * * * *"  # 每15分钟
        }
    )
    
    next_run = executor._calculate_next_run(cron_config)
    print(f"\nCron表达式 (每15分钟):")
    print(f"  表达式: */15 * * * *")
    print(f"  下次运行: {next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else '无'}")
    
    # 显示未来5次运行时间
    print(f"\n  未来5次运行时间:")
    current = datetime.now()
    for i in range(5):
        next_run = executor._calculate_next_run(cron_config, current)
        if next_run:
            print(f"    {i+1}. {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            current = next_run + timedelta(seconds=1)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


async def test_schedule_running():
    """测试调度执行器运行"""
    
    print("\n" + "=" * 60)
    print("测试调度执行器运行（10秒）")
    print("=" * 60)
    
    executor = get_schedule_executor()
    
    # 添加一个立即执行的间隔任务（每10秒）
    config = {
        "schedule_type": "interval",
        "schedule_interval": 10,
        "schedule_interval_unit": "seconds"
    }
    executor.add_config("quick_test", config)
    
    # 设置短检查间隔
    executor.check_interval = 5  # 每5秒检查一次
    
    # 启动执行器
    print("\n启动调度执行器...")
    await executor.start()
    
    # 运行10秒
    print("运行中...")
    await asyncio.sleep(10)
    
    # 停止执行器
    print("\n停止调度执行器...")
    await executor.stop()
    
    print("\n测试结束！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_schedule_executor())
    
    # 如果要测试实际运行，取消下面的注释
    # asyncio.run(test_schedule_running())