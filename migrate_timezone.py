#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移数据库时间到东八区
如果数据库中的时间是UTC时间，需要调整为东八区
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_manager, PipelineTask, PublishTask, Account, User
from timezone_config import to_beijing_time, format_beijing_time

def check_and_migrate_timestamps():
    """检查并迁移时间戳到东八区"""
    
    print("="*60)
    print("时区迁移工具 - 检查并更新数据库时间戳")
    print("="*60)
    
    db = get_db_manager()
    
    with db.get_session() as session:
        # 检查Pipeline任务的时间
        print("\n检查Pipeline任务时间...")
        sample_task = session.query(PipelineTask).first()
        
        if sample_task:
            print(f"\n示例任务: {sample_task.task_id}")
            print(f"  创建时间: {sample_task.created_at}")
            
            # 判断是否需要迁移（如果时间看起来像UTC）
            if sample_task.created_at:
                # 如果时间没有时区信息，或者时区不是东八区
                beijing_time = to_beijing_time(sample_task.created_at)
                print(f"  北京时间: {format_beijing_time(beijing_time)}")
                
                # 获取当前时间，判断是否需要调整
                now = datetime.now()
                time_diff = now - sample_task.created_at.replace(tzinfo=None) if sample_task.created_at.tzinfo else now - sample_task.created_at
                
                # 如果时间差异超过7小时，可能需要调整时区
                if abs(time_diff.total_seconds()) > 7 * 3600:
                    print("\n⚠️  检测到时间可能是UTC时间，需要迁移")
                    
                    # 询问用户是否要迁移
                    response = input("\n是否要将所有时间戳调整8小时到东八区? (y/n): ")
                    
                    if response.lower() == 'y':
                        migrate_all_timestamps(session)
                    else:
                        print("跳过迁移")
                else:
                    print("\n✅ 时间戳看起来已经是正确的东八区时间")
        else:
            print("没有找到任务记录")
    
    print("\n" + "="*60)
    print("迁移检查完成")
    print("="*60)

def migrate_all_timestamps(session):
    """迁移所有时间戳"""
    
    print("\n开始迁移时间戳...")
    
    # 迁移PipelineTask
    print("\n迁移Pipeline任务时间...")
    tasks = session.query(PipelineTask).all()
    for task in tasks:
        if task.created_at and not hasattr(task.created_at, 'tzinfo'):
            # 假设原时间是UTC，加8小时
            task.created_at = task.created_at + timedelta(hours=8)
        
        if task.started_at and not hasattr(task.started_at, 'tzinfo'):
            task.started_at = task.started_at + timedelta(hours=8)
        
        if task.completed_at and not hasattr(task.completed_at, 'tzinfo'):
            task.completed_at = task.completed_at + timedelta(hours=8)
    
    print(f"  更新了 {len(tasks)} 个任务")
    
    # 迁移PublishTask
    print("\n迁移发布任务时间...")
    publish_tasks = session.query(PublishTask).all()
    for task in publish_tasks:
        if task.created_at and not hasattr(task.created_at, 'tzinfo'):
            task.created_at = task.created_at + timedelta(hours=8)
        
        if task.updated_at and not hasattr(task.updated_at, 'tzinfo'):
            task.updated_at = task.updated_at + timedelta(hours=8)
        
        if task.upload_started_at and not hasattr(task.upload_started_at, 'tzinfo'):
            task.upload_started_at = task.upload_started_at + timedelta(hours=8)
        
        if task.upload_completed_at and not hasattr(task.upload_completed_at, 'tzinfo'):
            task.upload_completed_at = task.upload_completed_at + timedelta(hours=8)
        
        if task.scheduled_time and not hasattr(task.scheduled_time, 'tzinfo'):
            task.scheduled_time = task.scheduled_time + timedelta(hours=8)
    
    print(f"  更新了 {len(publish_tasks)} 个发布任务")
    
    # 迁移Account
    print("\n迁移账号时间...")
    accounts = session.query(Account).all()
    for account in accounts:
        if account.created_at and not hasattr(account.created_at, 'tzinfo'):
            account.created_at = account.created_at + timedelta(hours=8)
        
        if account.updated_at and not hasattr(account.updated_at, 'tzinfo'):
            account.updated_at = account.updated_at + timedelta(hours=8)
    
    print(f"  更新了 {len(accounts)} 个账号")
    
    # 迁移User
    print("\n迁移用户时间...")
    users = session.query(User).all()
    for user in users:
        if user.created_at and not hasattr(user.created_at, 'tzinfo'):
            user.created_at = user.created_at + timedelta(hours=8)
        
        if user.updated_at and not hasattr(user.updated_at, 'tzinfo'):
            user.updated_at = user.updated_at + timedelta(hours=8)
        
        if user.last_login and not hasattr(user.last_login, 'tzinfo'):
            user.last_login = user.last_login + timedelta(hours=8)
    
    print(f"  更新了 {len(users)} 个用户")
    
    # 提交更改
    print("\n提交更改...")
    session.commit()
    
    print("\n✅ 时间戳迁移完成！")

def main():
    """主函数"""
    check_and_migrate_timestamps()

if __name__ == "__main__":
    main()