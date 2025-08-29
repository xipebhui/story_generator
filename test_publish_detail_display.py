#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布状态详情展示功能
"""

import requests
import json
import sqlite3
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:51082"

# 认证Token
AUTH_TOKEN = "e20fe249-d47c-4b58-994f-190e95c047e5"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_task_with_publish_details():
    """测试包含发布详情的任务"""
    print("=" * 60)
    print("测试任务发布状态详情")
    print("=" * 60)
    
    # 1. 找一个有发布任务的pipeline task
    print("\n1. 查找有发布记录的任务...")
    conn = sqlite3.connect('data/pipeline_tasks.db')
    cursor = conn.cursor()
    
    # 查找有发布任务的pipeline task
    cursor.execute("""
        SELECT DISTINCT pt.task_id 
        FROM publish_tasks pub 
        JOIN pipeline_tasks pt ON pub.task_id = pt.task_id
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if not result:
        print("   ❌ 没有找到有发布记录的任务")
        conn.close()
        return
    
    task_id = result[0]
    print(f"   ✅ 找到任务: {task_id}")
    
    # 2. 获取该任务的发布详情
    print("\n2. 获取任务的发布详情...")
    cursor.execute("""
        SELECT 
            pub.publish_id,
            pub.task_id,
            pub.account_id,
            pub.status,
            pub.youtube_video_url,
            pub.error_message,
            pub.created_at
        FROM publish_tasks pub
        WHERE pub.task_id = ?
    """, (task_id,))
    
    publish_tasks = cursor.fetchall()
    conn.close()
    
    print(f"   发布任务数: {len(publish_tasks)}")
    for pt in publish_tasks:
        status_emoji = {
            'success': '✅',
            'pending': '⏳', 
            'uploading': '🔄',
            'failed': '❌'
        }.get(pt[3], '❓')
        
        print(f"   {status_emoji} 账号: {pt[2]} - 状态: {pt[3]}")
        if pt[4]:  # YouTube URL
            print(f"      URL: {pt[4]}")
        if pt[5]:  # Error message
            print(f"      错误: {pt[5][:50]}...")
    
    # 3. 通过API获取任务状态，验证发布信息
    print("\n3. 通过API获取任务状态...")
    response = requests.get(
        f"{BASE_URL}/api/pipeline/status/{task_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"   ❌ 获取任务状态失败: {response.status_code}")
        return
    
    task_data = response.json()
    print(f"   ✅ 成功获取任务状态")
    
    # 4. 验证发布状态数据
    print("\n4. 验证发布状态数据...")
    
    if 'publish_status' in task_data:
        ps = task_data['publish_status']
        print(f"   发布状态统计:")
        print(f"   - 总数: {ps['total']}")
        print(f"   - 成功: {ps['success']}")
        print(f"   - 待发布: {ps['pending']}")
        print(f"   - 上传中: {ps['uploading']}")
        print(f"   - 失败: {ps['failed']}")
        
        # 验证失败的任务是否被统计
        if ps['failed'] > 0:
            print(f"   ✅ 失败的发布任务已被正确统计: {ps['failed']} 个")
        
        # 验证总数是否正确
        if ps['total'] == len(publish_tasks):
            print(f"   ✅ 总数统计正确: {ps['total']}")
        else:
            print(f"   ❌ 总数统计不匹配: API返回 {ps['total']}，实际 {len(publish_tasks)}")
    else:
        print("   ❌ API响应中没有publish_status字段")
    
    if 'published_accounts' in task_data:
        print(f"\n   发布账号详情 ({len(task_data['published_accounts'])} 个):")
        for acc in task_data['published_accounts']:
            status_emoji = {
                'success': '✅',
                'pending': '⏳',
                'uploading': '🔄',
                'failed': '❌'
            }.get(acc['status'], '❓')
            
            print(f"   {status_emoji} {acc['account_name']}: {acc['status']}")
            if acc.get('youtube_video_url'):
                print(f"      URL: {acc['youtube_video_url']}")
            if acc.get('error_message'):
                print(f"      错误: {acc['error_message'][:50]}...")
    else:
        print("   ⚠️ API响应中没有published_accounts字段")
    
    return task_id

def create_test_publish_tasks():
    """创建测试发布任务，包含各种状态"""
    print("\n" + "=" * 60)
    print("创建测试发布任务")
    print("=" * 60)
    
    # 1. 创建一个新的测试任务
    print("\n1. 创建测试Pipeline任务...")
    create_data = {
        "video_id": f"test_detail_{datetime.now().strftime('%H%M%S')}",
        "creator_id": "test_user",
        "gender": 1,
        "duration": 30,
        "export_video": False,
        "enable_subtitle": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/pipeline/run",
        json=create_data,
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"   ❌ 创建任务失败: {response.text}")
        return None
    
    task_id = response.json()['task_id']
    print(f"   ✅ 任务创建成功: {task_id}")
    
    # 2. 直接在数据库中创建多个发布任务（模拟不同状态）
    print("\n2. 创建模拟发布任务...")
    conn = sqlite3.connect('data/pipeline_tasks.db')
    cursor = conn.cursor()
    
    test_publish_tasks = [
        (f"pub_{task_id}_001", task_id, 'yt_001_novel', 'success', 
         'https://youtube.com/watch?v=test001', None),
        (f"pub_{task_id}_002", task_id, 'yt_002_novel', 'failed',
         None, '上传失败：视频文件不存在'),
        (f"pub_{task_id}_003", task_id, 'yt_003_novel', 'pending',
         None, None),
        (f"pub_{task_id}_004", task_id, 'yt_004_novel', 'uploading',
         None, None),
        (f"pub_{task_id}_005", task_id, 'yt_005_novel', 'failed',
         None, '网络连接超时')
    ]
    
    for pub_id, t_id, acc_id, status, url, error in test_publish_tasks:
        try:
            cursor.execute("""
                INSERT INTO publish_tasks (
                    publish_id, task_id, account_id, status, 
                    youtube_video_url, error_message,
                    video_path, video_title, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (pub_id, t_id, acc_id, status, url, error, 
                  '/test/video.mp4', 'Test Video'))
            print(f"   ✅ 创建 {status} 状态的发布任务: {acc_id}")
        except Exception as e:
            print(f"   ❌ 创建发布任务失败: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n   📊 预期统计:")
    print(f"   - 总数: 5")
    print(f"   - 成功: 1")
    print(f"   - 失败: 2 (应该被统计)")
    print(f"   - 待发布: 1")
    print(f"   - 上传中: 1")
    
    return task_id

if __name__ == "__main__":
    print("开始测试发布状态详情展示功能\n")
    
    # 1. 测试现有任务的发布状态
    existing_task_id = test_task_with_publish_details()
    
    # 2. 创建新的测试任务
    new_task_id = create_test_publish_tasks()
    
    if new_task_id:
        print(f"\n3. 验证新创建的测试任务...")
        # 再次调用测试函数验证新任务
        import time
        time.sleep(1)  # 等待数据同步
        
        response = requests.get(
            f"{BASE_URL}/api/pipeline/status/{new_task_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'publish_status' in data:
                ps = data['publish_status']
                print(f"\n   实际统计:")
                print(f"   - 总数: {ps['total']}")
                print(f"   - 成功: {ps['success']}")
                print(f"   - 失败: {ps['failed']} ✅ 失败任务已被统计")
                print(f"   - 待发布: {ps['pending']}")
                print(f"   - 上传中: {ps['uploading']}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示:")
    print("1. 在前端详情页中，点击任务查看详情")
    print("2. 切换到'发布状态'标签页")
    print("3. 可以看到所有发布账号的详细状态，包括失败的账号")
    print("4. 失败的发布任务会显示错误信息")
    print(f"5. 测试任务ID: {new_task_id if new_task_id else existing_task_id}")