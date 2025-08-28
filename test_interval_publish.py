#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试间隔发布功能
"""

import requests
import json
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:51082"

# 认证Token（使用创建的测试用户token）
AUTH_TOKEN = "e20fe249-d47c-4b58-994f-190e95c047e5"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_interval_publish():
    """测试间隔发布功能"""
    print("=" * 60)
    print("测试间隔发布功能")
    print("=" * 60)
    
    # 1. 先创建一个测试任务
    print("\n1. 创建测试任务...")
    create_data = {
        "video_id": "test_interval_001",
        "creator_id": "test_user",
        "account_name": "youtube-001-小说",
        "gender": 1,
        "duration": 60,
        "image_dir": "default",
        "export_video": False,
        "enable_subtitle": True
    }
    
    response = requests.post(f"{BASE_URL}/api/pipeline/run", json=create_data, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"   ❌ 创建任务失败: {response.text}")
        return
    
    result = response.json()
    task_id = result['task_id']
    print(f"   ✅ 任务创建成功: {task_id}")
    
    # 2. 测试间隔发布
    print("\n2. 测试间隔发布（3小时间隔）...")
    
    publish_data = {
        "task_id": task_id,
        "account_ids": [
            "yt_001_novel",
            "yt_002_novel", 
            "yt_003_novel"
        ],
        "video_title": "测试间隔发布视频",
        "video_description": "这是一个测试间隔发布功能的视频",
        "video_tags": ["test", "interval", "publish"],
        "publish_interval_hours": 3,  # 3小时间隔
        "privacy_status": "public"
    }
    
    print(f"   请求参数:")
    print(f"   - 账号数量: {len(publish_data['account_ids'])}")
    print(f"   - 发布间隔: {publish_data['publish_interval_hours']} 小时")
    print(f"   - 账号列表: {publish_data['account_ids']}")
    
    # 发送发布请求
    publish_response = requests.post(
        f"{BASE_URL}/api/publish/schedule",
        json=publish_data,
        headers=HEADERS
    )
    
    if publish_response.status_code != 200:
        print(f"   ❌ 发布失败: {publish_response.text}")
        return
    
    publish_result = publish_response.json()
    
    print(f"\n3. 发布结果:")
    print(f"   总消息: {publish_result.get('message', '')}")
    
    if 'summary' in publish_result:
        summary = publish_result['summary']
        print(f"   - 总任务数: {summary.get('total', 0)}")
        print(f"   - 立即发布: {summary.get('immediate', 0)}")
        print(f"   - 定时发布: {summary.get('scheduled', 0)}")
        print(f"   - 失败数量: {summary.get('failed', 0)}")
    
    print(f"\n4. 详细任务信息:")
    current_time = datetime.now()
    
    for i, result in enumerate(publish_result.get('results', [])):
        account_id = result.get('account_id')
        status = result.get('status')
        scheduled_time = result.get('scheduled_time')
        message = result.get('message')
        
        print(f"\n   账号 {i+1}: {account_id}")
        print(f"   - 状态: {status}")
        print(f"   - 消息: {message}")
        
        if scheduled_time:
            scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            time_diff = (scheduled_dt.replace(tzinfo=None) - current_time).total_seconds() / 3600
            print(f"   - 计划发布时间: {scheduled_time}")
            print(f"   - 距离现在: {time_diff:.1f} 小时")
    
    # 5. 验证间隔时间
    print(f"\n5. 验证间隔时间:")
    results = publish_result.get('results', [])
    
    if len(results) >= 2:
        # 检查第一个任务应该立即发布
        first_task = results[0]
        if first_task.get('status') == 'uploading':
            print(f"   ✅ 第一个任务立即发布")
        else:
            print(f"   ❌ 第一个任务未立即发布，状态: {first_task.get('status')}")
        
        # 检查后续任务的间隔
        for i in range(1, len(results)):
            task = results[i]
            if task.get('scheduled_time'):
                scheduled_dt = datetime.fromisoformat(task.get('scheduled_time').replace('Z', '+00:00'))
                expected_hours = i * publish_data['publish_interval_hours']
                actual_hours = (scheduled_dt.replace(tzinfo=None) - current_time).total_seconds() / 3600
                
                print(f"   任务 {i+1}:")
                print(f"     - 预期间隔: {expected_hours} 小时")
                print(f"     - 实际间隔: {actual_hours:.1f} 小时")
                
                # 允许1分钟的误差
                if abs(actual_hours - expected_hours) < 0.02:  
                    print(f"     ✅ 间隔时间正确")
                else:
                    print(f"     ❌ 间隔时间不正确")
    
    # 6. 查询调度队列
    print(f"\n6. 查询调度队列:")
    queue_response = requests.get(
        f"{BASE_URL}/api/publish/scheduler/queue",
        headers=HEADERS
    )
    
    if queue_response.status_code == 200:
        queue_data = queue_response.json()
        scheduled_count = queue_data.get('scheduled_count', 0)
        print(f"   定时队列中的任务数: {scheduled_count}")
        
        if 'tasks' in queue_data:
            for task in queue_data['tasks'][:5]:  # 只显示前5个
                print(f"   - {task.get('publish_id')}: {task.get('scheduled_time')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_interval_publish()