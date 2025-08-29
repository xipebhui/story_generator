#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布状态展示功能 - 使用模拟发布
"""

import requests
import json
import time
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:51082"

# 认证Token
AUTH_TOKEN = "e20fe249-d47c-4b58-994f-190e95c047e5"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def create_and_publish_test():
    """创建测试任务并模拟发布"""
    print("=" * 60)
    print("创建测试任务并模拟发布流程")
    print("=" * 60)
    
    # 1. 创建一个已完成的任务
    print("\n1. 创建已完成的测试任务...")
    
    # 先创建任务
    create_data = {
        "video_id": f"mock_video_{datetime.now().strftime('%H%M%S')}",
        "creator_id": "test_user",
        "gender": 1,
        "duration": 30,
        "export_video": True,
        "enable_subtitle": True
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/pipeline/run",
        json=create_data,
        headers=HEADERS
    )
    
    if create_response.status_code != 200:
        print(f"   ❌ 创建任务失败: {create_response.text}")
        return
    
    task_id = create_response.json()['task_id']
    print(f"   ✅ 任务创建成功: {task_id}")
    
    # 2. 等待任务完成（或手动更新状态）
    print("\n2. 等待任务处理...")
    # 由于是测试，任务可能会失败，我们只需要一个task_id即可
    time.sleep(2)
    
    # 3. 发布到多个账号
    print("\n3. 发布到多个账号...")
    publish_data = {
        "task_id": task_id,
        "account_ids": ["yt_001_novel", "yt_002_novel", "yt_003_novel"],
        "video_title": "测试发布状态展示 - Mock视频",
        "video_description": "这是一个用于测试发布状态展示的模拟视频",
        "video_tags": ["test", "mock", "status"],
        "privacy_status": "private"
    }
    
    publish_response = requests.post(
        f"{BASE_URL}/api/publish/schedule",
        json=publish_data,
        headers=HEADERS
    )
    
    if publish_response.status_code != 200:
        print(f"   ⚠️ 发布调度可能失败（预期行为）: {publish_response.text}")
    else:
        print(f"   ✅ 发布任务创建成功")
    
    # 4. 模拟更新发布任务状态（直接操作数据库）
    print("\n4. 模拟发布任务状态更新...")
    # 这里我们可以通过API或直接数据库来模拟不同的发布状态
    
    # 5. 获取任务状态，查看发布信息
    print("\n5. 获取任务的发布状态...")
    time.sleep(1)  # 等待数据更新
    
    status_response = requests.get(
        f"{BASE_URL}/api/pipeline/status/{task_id}",
        headers=HEADERS
    )
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"   任务状态: {status_data.get('status', '未知')}")
        
        if 'publish_summary' in status_data:
            print(f"   发布状态摘要: {status_data['publish_summary']}")
        
        if 'publish_status' in status_data:
            ps = status_data['publish_status']
            print(f"   发布统计:")
            print(f"     • 总数: {ps['total']}")
            print(f"     • 成功: {ps['success']}")
            print(f"     • 待发布: {ps['pending']}")
            print(f"     • 上传中: {ps['uploading']}")
            print(f"     • 失败: {ps['failed']}")
        
        if 'published_accounts' in status_data and status_data['published_accounts']:
            print(f"   发布账号详情:")
            for acc in status_data['published_accounts']:
                status_emoji = {
                    'success': '✅',
                    'pending': '⏳',
                    'uploading': '🔄',
                    'failed': '❌'
                }.get(acc['status'], '❓')
                print(f"     {status_emoji} {acc['account_name']}: {acc['status']}")
                if acc.get('youtube_video_url'):
                    print(f"        URL: {acc['youtube_video_url']}")
    
    return task_id

def check_dashboard_data():
    """检查Dashboard API返回的数据"""
    print("\n" + "=" * 60)
    print("检查Dashboard任务列表数据")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/pipeline/tasks",
        params={"page": 1, "page_size": 10},
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n总任务数: {data['total']}")
        
        # 找出有发布信息的任务
        tasks_with_publish = [
            task for task in data['tasks'] 
            if task.get('publish_status', {}).get('total', 0) > 0
        ]
        
        if tasks_with_publish:
            print(f"\n发现 {len(tasks_with_publish)} 个有发布信息的任务:")
            for task in tasks_with_publish[:3]:  # 显示前3个
                print(f"\n任务ID: {task['task_id']}")
                print(f"Pipeline状态: {task['status']}")
                print(f"发布摘要: {task.get('publish_summary', '无')}")
                
                ps = task.get('publish_status', {})
                print(f"发布统计: 总={ps.get('total', 0)}, "
                      f"成功={ps.get('success', 0)}, "
                      f"待发布={ps.get('pending', 0)}, "
                      f"失败={ps.get('failed', 0)}")
        else:
            print("\n暂无发布信息的任务")

if __name__ == "__main__":
    print("开始测试发布状态展示功能（模拟版）\n")
    
    # 创建并发布测试任务
    task_id = create_and_publish_test()
    
    # 检查Dashboard数据
    check_dashboard_data()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示：")
    print("1. 发布任务可能因为视频文件不存在而失败（这是正常的）")
    print("2. 但发布任务记录会被创建，可以在UI中看到发布状态")
    print("3. 访问 http://localhost:3001 查看Dashboard中的发布状态展示")