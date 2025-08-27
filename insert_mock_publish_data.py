#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入mock发布数据到数据库，用于测试发布历史接口
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
import random
import os
import sys

def insert_mock_publish_data(db_path):
    """插入mock发布数据"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("连接到数据库成功")
        
        # 先获取一些已存在的pipeline任务ID（如果有的话）
        cursor.execute("SELECT id, task_id, video_id FROM pipeline_tasks LIMIT 5")
        pipeline_tasks = cursor.fetchall()
        
        # 定义一些mock账号ID
        mock_accounts = [
            'bearreddit',
            'storytime_channel',
            'ai_videos',
            'tech_stories',
            'daily_tales'
        ]
        
        # 定义一些状态
        statuses = ['success', 'success', 'success', 'failed', 'uploading', 'pending']
        
        # 插入mock发布任务
        mock_publishes = []
        base_time = datetime.now() - timedelta(days=7)  # 从7天前开始
        
        for i in range(12):  # 创建12条mock数据
            # 选择一个pipeline任务（如果有的话）
            if pipeline_tasks and i < len(pipeline_tasks):
                _, task_id, video_id = pipeline_tasks[i % len(pipeline_tasks)]
            else:
                # 创建mock的task_id和video_id
                task_id = f"mock_task_{uuid.uuid4().hex[:8]}"
                video_id = f"mock_video_{random.choice(['abc123xyz', 'def456uvw', 'ghi789rst', 'jkl012mno'])}"
            
            # 使用时间戳确保唯一性
            publish_id = f"pub_mock_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{uuid.uuid4().hex[:8]}"
            account_id = mock_accounts[i % len(mock_accounts)]
            status = statuses[i % len(statuses)]
            
            # 创建时间递增
            created_at = base_time + timedelta(hours=i*12)
            
            # 根据状态设置不同的字段
            youtube_video_id = None
            youtube_video_url = None
            error_message = None
            upload_response = {}
            upload_completed_at = None
            
            if status == 'success':
                video_hash = uuid.uuid4().hex[:11]
                youtube_video_id = video_hash
                youtube_video_url = f"https://youtu.be/{video_hash}"
                upload_completed_at = created_at + timedelta(minutes=random.randint(5, 30))
                upload_response = {
                    "results": [{
                        "status": "SUCCESS",
                        "url": youtube_video_url,
                        "executionTime": random.randint(100, 500)
                    }]
                }
            elif status == 'failed':
                error_message = random.choice([
                    "视频上传失败：网络连接超时",
                    "账号认证失败",
                    "视频格式不支持",
                    "文件大小超出限制"
                ])
                upload_completed_at = created_at + timedelta(minutes=random.randint(2, 10))
                upload_response = {
                    "results": [{
                        "status": "FAIL",
                        "error": error_message
                    }]
                }
            elif status == 'uploading':
                # 上传中的任务
                pass
            else:  # pending
                # 待处理的任务
                pass
            
            # 构建发布数据
            publish_data = {
                'publish_id': publish_id,
                'task_id': task_id,
                'account_id': account_id,
                'video_path': f"/data/videos/{task_id}/output.mp4",  # 添加必需的video_path字段
                'video_title': f"测试视频 {i+1} - {video_id[:8]}",
                'video_description': f"这是一个测试视频描述。由AI自动生成的内容，包含了精彩的故事情节。\n\n标签：#{account_id} #AI生成 #测试",
                'video_tags': json.dumps(['AI生成', '测试视频', '自动发布', account_id], ensure_ascii=False),
                'thumbnail_path': f"/data/thumbnails/{task_id}.jpg" if random.random() > 0.3 else None,
                'privacy_status': random.choice(['public', 'public', 'unlisted', 'private']),
                'status': status,
                'youtube_video_id': youtube_video_id,
                'youtube_video_url': youtube_video_url,
                'error_message': error_message,
                'upload_response': json.dumps(upload_response, ensure_ascii=False) if upload_response else None,
                'created_at': created_at.isoformat(),
                'upload_started_at': (created_at + timedelta(seconds=30)).isoformat() if status != 'pending' else None,
                'upload_completed_at': upload_completed_at.isoformat() if upload_completed_at else None,
                'is_scheduled': 0,
                'scheduled_time': None
            }
            
            mock_publishes.append(publish_data)
        
        # 插入数据到publish_tasks表
        for data in mock_publishes:
            # 构建插入SQL
            columns = []
            values = []
            placeholders = []
            
            for key, value in data.items():
                if value is not None:
                    columns.append(key)
                    values.append(value)
                    placeholders.append('?')
            
            sql = f"INSERT INTO publish_tasks ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            try:
                cursor.execute(sql, values)
                print(f"✅ 插入发布任务: {data['publish_id']} - 状态: {data['status']}")
            except sqlite3.IntegrityError as e:
                # 如果ID已存在，跳过
                print(f"⚠️  发布任务已存在: {data['publish_id']}")
                continue
            except Exception as e:
                print(f"❌ 插入失败: {e}")
                continue
        
        # 提交更改
        conn.commit()
        
        # 显示统计信息
        cursor.execute("SELECT COUNT(*) FROM publish_tasks")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT status, COUNT(*) FROM publish_tasks GROUP BY status")
        status_stats = cursor.fetchall()
        
        print("\n" + "="*50)
        print("发布任务统计:")
        print(f"总数: {total_count}")
        print("\n状态分布:")
        for status, count in status_stats:
            print(f"  {status}: {count}")
        
        # 显示最近的几条记录
        cursor.execute("""
            SELECT publish_id, task_id, account_id, status, youtube_video_url, created_at 
            FROM publish_tasks 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_tasks = cursor.fetchall()
        
        print("\n最近的发布任务:")
        for task in recent_tasks:
            publish_id, task_id, account_id, status, url, created_at = task
            print(f"  {publish_id[:30]}... | {account_id} | {status} | {url or 'N/A'}")
        
        conn.close()
        print("\n✅ Mock数据插入完成!")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

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
            print(f"尝试过的路径: {possible_paths}")
            sys.exit(1)
    
    print("="*50)
    print("插入Mock发布数据")
    print("="*50)
    print(f"数据库路径: {os.path.abspath(db_path)}")
    print()
    
    insert_mock_publish_data(db_path)

if __name__ == "__main__":
    main()