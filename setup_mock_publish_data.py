#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理并设置mock发布数据
"""

import os
import sqlite3
from datetime import datetime, timedelta
import random
import uuid

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'pipeline_tasks.db')

def ensure_database_exists():
    """确保数据库目录和文件存在"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        print(f"✅ 创建数据目录: {DB_DIR}")
    
    if not os.path.exists(DB_PATH):
        print(f"⚠️ 数据库不存在，创建新数据库: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        conn.close()
    else:
        print(f"✅ 使用现有数据库: {DB_PATH}")

def clean_publish_data():
    """清理现有的发布数据"""
    print("\n" + "=" * 60)
    print("清理现有发布数据")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 获取要清理的数据统计
        cursor.execute("SELECT COUNT(*) FROM publish_tasks")
        count = cursor.fetchone()[0]
        print(f"找到 {count} 条发布记录")
        
        # 清理所有发布数据
        cursor.execute("DELETE FROM publish_tasks")
        conn.commit()
        print(f"✅ 已清理 {count} 条发布记录")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_recent_tasks(limit=5):
    """获取最近的pipeline任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tasks = []
    try:
        cursor.execute("""
            SELECT task_id, status, video_id, creator_id 
            FROM pipeline_tasks 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        
        tasks = cursor.fetchall()
        print(f"\n找到 {len(tasks)} 个Pipeline任务")
        for task in tasks:
            print(f"  - {task[0]} (状态: {task[1]})")
            
    except Exception as e:
        print(f"❌ 获取任务失败: {e}")
    finally:
        conn.close()
    
    return tasks

def create_mock_publish_tasks():
    """创建mock发布任务数据"""
    print("\n" + "=" * 60)
    print("创建Mock发布数据")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取最近的任务
    tasks = get_recent_tasks(5)
    
    if not tasks:
        print("⚠️ 没有找到Pipeline任务，创建测试任务")
        # 创建一个测试任务
        test_task_id = f"test_mock_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO pipeline_tasks (
                task_id, video_id, creator_id, status, 
                created_at, gender, image_duration, export_video, enable_subtitle
            ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, ?)
        """, (test_task_id, 'test_video', 'test_user', 'completed', 1, 60, 1, 1))
        conn.commit()
        tasks = [(test_task_id, 'completed', 'test_video', 'test_user')]
        print(f"✅ 创建测试任务: {test_task_id}")
    
    # 测试账号列表
    test_accounts = [
        ('yt_001_novel', 'YouTube小说频道1'),
        ('yt_002_novel', 'YouTube小说频道2'),
        ('yt_003_novel', 'YouTube小说频道3'),
        ('bearreddit', 'BearReddit频道'),
        ('storytime_channel', 'StoryTime频道')
    ]
    
    created_count = 0
    
    # 为每个任务创建多个发布记录
    for task in tasks[:3]:  # 只处理前3个任务
        task_id, task_status, video_id, creator_id = task
        
        # 如果任务是完成状态，创建发布记录
        if task_status in ['completed', 'failed']:
            print(f"\n为任务 {task_id} 创建发布记录:")
            
            # 随机选择2-4个账号发布
            num_accounts = random.randint(2, min(4, len(test_accounts)))
            selected_accounts = random.sample(test_accounts, num_accounts)
            
            for i, (account_id, account_name) in enumerate(selected_accounts):
                # 生成publish_id
                publish_id = f"pub_{task_id}_{account_id}_{uuid.uuid4().hex[:8]}"
                
                # 随机分配状态
                status_choices = ['success', 'failed', 'pending', 'uploading']
                weights = [0.3, 0.3, 0.2, 0.2]  # 权重分布
                status = random.choices(status_choices, weights=weights)[0]
                
                # 根据状态设置其他字段
                youtube_video_url = None
                youtube_video_id = None
                error_message = None
                upload_completed_at = None
                
                if status == 'success':
                    youtube_video_id = f"yt_{uuid.uuid4().hex[:11]}"
                    youtube_video_url = f"https://youtu.be/{youtube_video_id}"
                    upload_completed_at = datetime.now() - timedelta(hours=random.randint(1, 24))
                elif status == 'failed':
                    error_messages = [
                        "视频文件不存在",
                        "网络连接超时",
                        "YouTube API配额已用完",
                        "账号认证失败",
                        "视频格式不支持"
                    ]
                    error_message = random.choice(error_messages)
                
                # 插入发布记录
                try:
                    cursor.execute("""
                        INSERT INTO publish_tasks (
                            publish_id, task_id, account_id, 
                            video_path, video_title, video_description, video_tags,
                            status, privacy_status,
                            youtube_video_id, youtube_video_url, error_message,
                            created_at, upload_completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                    """, (
                        publish_id, task_id, account_id,
                        f'/videos/{video_id}.mp4', 
                        f'测试视频 - {video_id}',
                        f'这是一个测试视频，创建者: {creator_id}',
                        '["test", "mock", "video"]',
                        status, 'public',
                        youtube_video_id, youtube_video_url, error_message,
                        upload_completed_at
                    ))
                    
                    status_emoji = {
                        'success': '✅',
                        'pending': '⏳',
                        'uploading': '🔄',
                        'failed': '❌'
                    }[status]
                    
                    print(f"  {status_emoji} {account_id}: {status} (ID: {publish_id[:20]}...)")
                    if youtube_video_url:
                        print(f"      URL: {youtube_video_url}")
                    if error_message:
                        print(f"      错误: {error_message}")
                    
                    created_count += 1
                    
                except Exception as e:
                    print(f"  ❌ 创建失败: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 总共创建了 {created_count} 条发布记录")
    
    return created_count

def verify_data():
    """验证创建的数据"""
    print("\n" + "=" * 60)
    print("验证数据")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 统计各状态的发布任务数量
    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM publish_tasks 
        GROUP BY status
    """)
    
    status_stats = cursor.fetchall()
    print("\n发布任务状态统计:")
    for status, count in status_stats:
        status_emoji = {
            'success': '✅',
            'pending': '⏳',
            'uploading': '🔄',
            'failed': '❌'
        }.get(status, '❓')
        print(f"  {status_emoji} {status}: {count}")
    
    # 获取一些示例数据
    cursor.execute("""
        SELECT pt.task_id, COUNT(*) as pub_count,
               SUM(CASE WHEN pt.status = 'success' THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN pt.status = 'failed' THEN 1 ELSE 0 END) as failed_count
        FROM publish_tasks pt
        GROUP BY pt.task_id
        LIMIT 5
    """)
    
    task_stats = cursor.fetchall()
    print("\n任务发布统计:")
    for task_id, pub_count, success_count, failed_count in task_stats:
        print(f"  任务: {task_id[:30]}...")
        print(f"    - 总发布数: {pub_count}")
        print(f"    - 成功: {success_count}")
        print(f"    - 失败: {failed_count}")
    
    conn.close()

if __name__ == "__main__":
    print("开始设置Mock发布数据\n")
    
    # 确保数据库存在
    ensure_database_exists()
    
    # 1. 清理现有数据
    clean_publish_data()
    
    # 2. 创建mock数据
    count = create_mock_publish_tasks()
    
    # 3. 验证数据
    if count > 0:
        verify_data()
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print("\n说明:")
    print("1. 已清理所有旧的发布数据")
    print("2. 为最近的Pipeline任务创建了mock发布记录")
    print("3. 包含各种状态：成功、失败、待发布、上传中")
    print("4. 失败的任务包含错误信息，可以测试重试功能")
    print("5. 所有记录都有publish_id，可以测试删除功能")
    print("\n现在可以在前端查看发布状态，测试重试和删除按钮了！")