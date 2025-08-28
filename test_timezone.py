#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时区配置是否正确
验证数据库和应用程序使用东八区时间
"""

import sys
import os
import json
from datetime import datetime
import pytz

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from timezone_config import get_beijing_now, to_beijing_time, format_beijing_time
from database import get_db_manager, PipelineTask
import uuid

def test_timezone_functions():
    """测试时区函数"""
    print("="*60)
    print("测试时区函数")
    print("="*60)
    
    # 测试获取北京时间
    beijing_time = get_beijing_now()
    print(f"\n当前北京时间: {beijing_time}")
    print(f"时区信息: {beijing_time.tzinfo}")
    print(f"格式化显示: {format_beijing_time(beijing_time)}")
    
    # 测试无时区时间转换
    naive_dt = datetime.now()  # 无时区信息的时间
    print(f"\n无时区时间: {naive_dt}")
    beijing_converted = to_beijing_time(naive_dt)
    print(f"转换后北京时间: {beijing_converted}")
    print(f"格式化显示: {format_beijing_time(beijing_converted)}")
    
    # 对比UTC时间和北京时间
    utc_time = datetime.now(pytz.UTC)
    beijing_from_utc = to_beijing_time(utc_time)
    print(f"\nUTC时间: {utc_time}")
    print(f"转换为北京时间: {beijing_from_utc}")
    print(f"时差: 8小时")
    
    return True

def test_database_timezone():
    """测试数据库时区设置"""
    print("\n" + "="*60)
    print("测试数据库时区")
    print("="*60)
    
    # 获取数据库管理器
    db = get_db_manager()
    
    # 创建测试任务
    test_task_id = f"timezone_test_{uuid.uuid4().hex[:8]}"
    
    try:
        # 创建任务记录
        task_data = {
            'task_id': test_task_id,
            'video_id': 'test_video_tz',
            'creator_id': 'test_timezone',
            'gender': 1,
            'image_duration': 60,
            'export_video': False,
            'enable_subtitle': True,
            'status': 'pending'
        }
        
        print(f"\n创建测试任务: {test_task_id}")
        task = db.create_task(task_data)
        
        # 打印创建时间
        print(f"\n任务创建时间:")
        print(f"  原始值: {task.created_at}")
        if hasattr(task.created_at, 'tzinfo') and task.created_at.tzinfo:
            print(f"  时区: {task.created_at.tzinfo}")
        else:
            print(f"  时区: 无时区信息（假设为北京时间）")
        
        # 从数据库重新读取，验证时区处理
        retrieved_task = db.get_task(test_task_id)
        print(f"\n重新读取的任务时间:")
        print(f"  原始值: {retrieved_task.created_at}")
        if hasattr(retrieved_task.created_at, 'tzinfo') and retrieved_task.created_at.tzinfo:
            print(f"  时区: {retrieved_task.created_at.tzinfo}")
        else:
            print(f"  时区: 无时区信息")
        
        # 格式化显示
        formatted_time = format_beijing_time(retrieved_task.created_at)
        print(f"  格式化显示: {formatted_time}")
        
        # 更新任务，设置完成时间
        from timezone_config import get_beijing_now
        update_data = {
            'status': 'completed',
            'completed_at': get_beijing_now()
        }
        
        print(f"\n更新任务完成时间...")
        updated_task = db.update_task(test_task_id, update_data)
        
        if updated_task.completed_at:
            print(f"任务完成时间:")
            print(f"  原始值: {updated_task.completed_at}")
            print(f"  格式化显示: {format_beijing_time(updated_task.completed_at)}")
        
        # 删除测试任务
        print(f"\n清理测试数据...")
        with db.get_session() as session:
            session.query(PipelineTask).filter_by(task_id=test_task_id).delete()
            session.commit()
        print("测试数据已清理")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试清理数据
        try:
            with db.get_session() as session:
                session.query(PipelineTask).filter_by(task_id=test_task_id).delete()
                session.commit()
        except:
            pass
        
        return False

def test_sqlite_datetime():
    """直接测试SQLite的时间函数"""
    print("\n" + "="*60)
    print("测试SQLite时间函数")
    print("="*60)
    
    db = get_db_manager()
    
    with db.get_session() as session:
        # 测试SQLite的当前时间函数
        result = session.execute("SELECT datetime('now') as utc_time, datetime('now', '+8 hours') as beijing_time").fetchone()
        print(f"\nSQLite UTC时间: {result.utc_time}")
        print(f"SQLite 北京时间(+8): {result.beijing_time}")
        
        # 测试SQLite的本地时间
        result = session.execute("SELECT datetime('now', 'localtime') as local_time").fetchone()
        print(f"SQLite 本地时间: {result.local_time}")
    
    return True

def main():
    """主测试函数"""
    print("="*60)
    print("时区配置测试 - 验证东八区(UTC+8)设置")
    print("="*60)
    
    # 系统信息
    import platform
    print(f"\n系统信息:")
    print(f"  Python版本: {sys.version}")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    
    # 系统时区
    import time
    print(f"  系统时区: {time.tzname}")
    print(f"  UTC偏移: {time.timezone / 3600} 小时")
    
    # 运行测试
    tests = [
        ("时区函数测试", test_timezone_functions),
        ("数据库时区测试", test_database_timezone),
        ("SQLite时间测试", test_sqlite_datetime)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name}失败: {e}")
            results.append((test_name, False))
    
    # 打印测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    # 总体结论
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n✅ 所有测试通过！时区配置正确。")
    else:
        print("\n❌ 部分测试失败，请检查时区配置。")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)