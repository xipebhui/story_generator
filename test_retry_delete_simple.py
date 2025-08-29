#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试发布任务的重试和删除功能
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

def test_retry_functionality():
    """测试重试功能"""
    print("=" * 60)
    print("测试重试功能")
    print("=" * 60)
    
    # 使用之前创建的测试任务ID (包含各种状态的发布任务)
    test_publish_id = "pub_test_user_test_detail_233803_e14ec8c2_002"  # 失败的任务
    
    print(f"\n1. 尝试重试失败的发布任务: {test_publish_id}")
    
    response = requests.post(
        f"{BASE_URL}/api/publish/retry/{test_publish_id}",
        headers=HEADERS
    )
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 重试成功")
        print(f"   消息: {result.get('message', '')}")
        if 'new_publish_id' in result:
            print(f"   新发布ID: {result['new_publish_id']}")
    else:
        print(f"   ❌ 重试失败: {response.text}")
    
    # 测试重试成功的任务（应该失败）
    success_publish_id = "pub_test_user_test_detail_233803_e14ec8c2_001"
    print(f"\n2. 尝试重试成功的发布任务（应该失败）: {success_publish_id}")
    
    response = requests.post(
        f"{BASE_URL}/api/publish/retry/{success_publish_id}",
        headers=HEADERS
    )
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✅ 正确拒绝了重试成功任务的请求")
        print(f"   错误信息: {response.json().get('detail', '')}")
    else:
        print(f"   ❌ 意外结果: {response.text}")

def test_delete_functionality():
    """测试删除功能"""
    print("\n" + "=" * 60)
    print("测试删除功能")
    print("=" * 60)
    
    # 使用测试发布任务ID
    test_publish_id = "pub_test_user_test_detail_233803_e14ec8c2_005"  # 失败的任务
    
    print(f"\n1. 删除发布任务记录: {test_publish_id}")
    
    response = requests.delete(
        f"{BASE_URL}/api/publish/task/{test_publish_id}",
        headers=HEADERS
    )
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 删除成功")
        print(f"   消息: {result.get('message', '')}")
    else:
        print(f"   ❌ 删除失败: {response.text}")
    
    # 尝试删除不存在的任务（应该返回404）
    non_existent_id = "pub_non_existent_task"
    print(f"\n2. 尝试删除不存在的任务（应该失败）: {non_existent_id}")
    
    response = requests.delete(
        f"{BASE_URL}/api/publish/task/{non_existent_id}",
        headers=HEADERS
    )
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 404:
        print(f"   ✅ 正确返回404错误")
        print(f"   错误信息: {response.json().get('detail', '')}")
    else:
        print(f"   ❌ 意外结果: {response.text}")

def test_frontend_display():
    """测试前端显示更新"""
    print("\n" + "=" * 60)
    print("测试前端状态显示")
    print("=" * 60)
    
    # 获取测试任务的状态
    task_id = "test_user_test_detail_233803_e14ec8c2"
    
    print(f"\n获取任务状态: {task_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/pipeline/status/{task_id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 获取状态成功")
        
        if 'publish_status' in data:
            ps = data['publish_status']
            print(f"\n   发布状态统计:")
            print(f"   - 总数: {ps['total']}")
            print(f"   - 成功: {ps['success']}")
            print(f"   - 失败: {ps['failed']}")
            print(f"   - 待发布: {ps['pending']}")
            print(f"   - 上传中: {ps['uploading']}")
        
        if 'published_accounts' in data and data['published_accounts']:
            print(f"\n   发布账号状态:")
            for acc in data['published_accounts'][:5]:  # 最多显示5个
                status_emoji = {
                    'success': '✅',
                    'pending': '⏳',
                    'uploading': '🔄',
                    'failed': '❌'
                }.get(acc['status'], '❓')
                print(f"   {status_emoji} {acc.get('account_name', 'Unknown')}: {acc['status']}")
                if acc.get('publish_id'):
                    print(f"      ID: {acc['publish_id']}")
    else:
        print(f"   ❌ 获取状态失败: {response.status_code}")

if __name__ == "__main__":
    print("开始测试发布任务重试和删除功能\n")
    
    # 1. 测试重试功能
    test_retry_functionality()
    
    # 2. 测试删除功能
    test_delete_functionality()
    
    # 3. 验证前端显示
    test_frontend_display()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n说明:")
    print("1. 重试功能：只允许failed或cancelled状态的任务重试")
    print("2. 删除功能：可以删除任何非uploading状态的任务")
    print("3. 前端显示：通过发布状态Tab页可以看到重试和删除按钮")
    print("4. 操作后数据会自动刷新")