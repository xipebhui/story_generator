#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版API的脚本
"""

import requests
import json
import time
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:51082"

def test_pipeline_run():
    """测试运行Pipeline"""
    print("\n=== 测试Pipeline运行 ===")
    
    data = {
        "video_id": "test_video_001",
        "creator_id": "test_creator",
        "gender": 1,
        "duration": 60,
        "export_video": False,
        "enable_subtitle": True
    }
    
    response = requests.post(f"{BASE_URL}/api/pipeline/run", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result['task_id']


def test_task_status(task_id):
    """测试查询任务状态"""
    print(f"\n=== 测试任务状态查询 ===")
    print(f"任务ID: {task_id}")
    
    response = requests.get(f"{BASE_URL}/api/pipeline/status/{task_id}")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def test_task_history():
    """测试任务历史查询"""
    print("\n=== 测试任务历史查询 ===")
    
    params = {
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/api/pipeline/history", params=params)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def test_statistics():
    """测试统计信息"""
    print("\n=== 测试统计信息 ===")
    
    response = requests.get(f"{BASE_URL}/api/pipeline/statistics")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def test_accounts():
    """测试账号管理"""
    print("\n=== 测试账号列表 ===")
    
    response = requests.get(f"{BASE_URL}/api/accounts")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"总账号数: {result['total']}")
    
    # 显示前3个账号
    for account in result['accounts'][:3]:
        print(f"- {account['account_name']} ({account['account_id']})")
    
    return result['accounts']


def test_create_publish(task_id, account_ids):
    """测试创建发布任务"""
    print("\n=== 测试创建发布任务 ===")
    
    data = {
        "task_id": task_id,
        "account_ids": account_ids[:2],  # 使用前2个账号
        "video_title": "测试视频标题",
        "video_description": "这是一个测试视频描述",
        "video_tags": ["测试", "API", "Pipeline"],
        "privacy_status": "private"
    }
    
    response = requests.post(f"{BASE_URL}/api/publish/create", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def test_publish_history():
    """测试发布历史查询"""
    print("\n=== 测试发布历史查询 ===")
    
    params = {
        "limit": 10
    }
    
    response = requests.get(f"{BASE_URL}/api/publish/history", params=params)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始API测试")
    print("=" * 60)
    
    try:
        # 1. 测试账号管理
        accounts = test_accounts()
        account_ids = [acc['account_id'] for acc in accounts]
        
        # 2. 测试运行Pipeline（注意：这会创建一个模拟任务）
        # task_id = test_pipeline_run()
        # time.sleep(2)  # 等待任务开始
        
        # 使用模拟的task_id进行测试
        task_id = "test_creator_test_video_001_mock"
        
        # 3. 测试任务状态
        # test_task_status(task_id)
        
        # 4. 测试任务历史
        test_task_history()
        
        # 5. 测试统计信息
        test_statistics()
        
        # 6. 测试创建发布任务（注意：需要一个完成的任务）
        # test_create_publish(task_id, account_ids)
        
        # 7. 测试发布历史
        test_publish_history()
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()