#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布状态展示功能
"""

import requests
import json
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:51082"

# 认证Token
AUTH_TOKEN = "e20fe249-d47c-4b58-994f-190e95c047e5"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_task_list_with_publish_status():
    """测试任务列表接口，检查发布状态信息"""
    print("=" * 60)
    print("测试任务列表接口（包含发布状态）")
    print("=" * 60)
    
    # 1. 获取任务列表
    print("\n1. 获取任务列表...")
    response = requests.get(
        f"{BASE_URL}/api/pipeline/tasks",
        params={
            "page": 1,
            "page_size": 5
        },
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"   ❌ 获取任务列表失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return
    
    result = response.json()
    print(f"   ✅ 成功获取任务列表")
    print(f"   - 总任务数: {result.get('total', 0)}")
    print(f"   - 当前页任务数: {len(result.get('tasks', []))}")
    
    # 2. 分析每个任务的发布状态
    print("\n2. 任务发布状态详情:")
    tasks = result.get('tasks', [])
    
    for i, task in enumerate(tasks[:3], 1):  # 只显示前3个
        print(f"\n   任务 {i}: {task['task_id']}")
        print(f"   - Pipeline状态: {task['status']}")
        
        # 发布状态信息
        if 'publish_summary' in task:
            print(f"   - 发布状态摘要: {task['publish_summary']}")
        
        if 'publish_status' in task and task['publish_status']:
            ps = task['publish_status']
            print(f"   - 发布统计:")
            print(f"     • 总数: {ps.get('total', 0)}")
            print(f"     • 成功: {ps.get('success', 0)}")
            print(f"     • 待发布: {ps.get('pending', 0)}")
            print(f"     • 上传中: {ps.get('uploading', 0)}")
            print(f"     • 失败: {ps.get('failed', 0)}")
        
        if 'published_accounts' in task and task['published_accounts']:
            print(f"   - 发布账号详情:")
            for account in task['published_accounts'][:2]:  # 只显示前2个账号
                print(f"     • {account['account_name']}: {account['status']}")
                if account.get('youtube_video_url'):
                    print(f"       URL: {account['youtube_video_url']}")
        elif task['status'] == 'completed':
            print("   - 发布账号详情: 未发布")

def test_single_task_status():
    """测试单个任务的状态接口"""
    print("\n" + "=" * 60)
    print("测试单个任务状态接口")
    print("=" * 60)
    
    # 先获取一个任务ID
    response = requests.get(
        f"{BASE_URL}/api/pipeline/tasks",
        params={"page": 1, "page_size": 1},
        headers=HEADERS
    )
    
    if response.status_code != 200 or not response.json().get('tasks'):
        print("   ❌ 无法获取任务列表")
        return
    
    task_id = response.json()['tasks'][0]['task_id']
    print(f"\n1. 获取任务 {task_id} 的状态...")
    
    # 获取任务状态
    status_response = requests.get(
        f"{BASE_URL}/api/pipeline/status/{task_id}",
        headers=HEADERS
    )
    
    if status_response.status_code != 200:
        print(f"   ❌ 获取状态失败: {status_response.status_code}")
        return
    
    status_data = status_response.json()
    print(f"   ✅ 成功获取任务状态")
    
    # 显示发布状态
    if 'publish_status' in status_data:
        print(f"   发布状态统计: {status_data['publish_status']}")
    
    if 'published_accounts' in status_data:
        print(f"   发布账号数: {len(status_data['published_accounts'])}")
        for account in status_data['published_accounts'][:3]:
            print(f"   - {account['account_name']}: {account['status']}")

def create_test_task_and_publish():
    """创建一个测试任务并发布，用于测试发布状态展示"""
    print("\n" + "=" * 60)
    print("创建测试任务并发布")
    print("=" * 60)
    
    # 1. 创建任务
    print("\n1. 创建测试任务...")
    create_data = {
        "video_id": f"test_status_{datetime.now().strftime('%H%M%S')}",
        "creator_id": "test_user",
        "gender": 1,
        "duration": 30,
        "export_video": False,
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
    
    # 2. 模拟发布到多个账号
    print("\n2. 发布到多个账号...")
    publish_data = {
        "task_id": task_id,
        "account_ids": ["yt_001_novel", "yt_002_novel"],
        "video_title": "测试发布状态展示",
        "video_description": "这是一个测试视频",
        "video_tags": ["test", "status"],
        "privacy_status": "public"
    }
    
    publish_response = requests.post(
        f"{BASE_URL}/api/publish/schedule",
        json=publish_data,
        headers=HEADERS
    )
    
    if publish_response.status_code != 200:
        print(f"   ❌ 发布失败: {publish_response.text}")
        return
    
    print(f"   ✅ 发布任务创建成功")
    
    # 3. 再次获取任务状态，查看发布信息
    print("\n3. 获取任务的发布状态...")
    status_response = requests.get(
        f"{BASE_URL}/api/pipeline/status/{task_id}",
        headers=HEADERS
    )
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        if 'publish_summary' in status_data:
            print(f"   发布状态摘要: {status_data.get('publish_summary', '未知')}")
        if 'publish_status' in status_data:
            ps = status_data['publish_status']
            print(f"   发布统计: 总数={ps['total']}, 成功={ps['success']}, 待发布={ps['pending']}")

if __name__ == "__main__":
    print("开始测试发布状态展示功能\n")
    
    # 测试任务列表
    test_task_list_with_publish_status()
    
    # 测试单个任务状态
    test_single_task_status()
    
    # 创建测试任务并发布
    create_test_task_and_publish()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)