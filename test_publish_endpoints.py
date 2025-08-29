#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布任务重试和删除端点
"""

import requests
import json
import time
import os
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:51082"

# 从环境变量或默认值获取API Key
API_KEY = os.environ.get('TEST_API_KEY', '')

def get_headers():
    """获取请求头"""
    if API_KEY:
        return {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
    return {'Content-Type': 'application/json'}

def test_api_endpoints():
    """测试发布相关的API端点"""
    print("=" * 60)
    print("测试发布任务重试和删除端点")
    print("=" * 60)
    
    # 1. 测试获取发布历史
    print("\n1. 获取发布历史...")
    headers = get_headers()
    print(f"使用认证: {'是' if API_KEY else '否（如果API要求认证可能会失败）'}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/publish/history?limit=5", headers=headers)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"发布任务总数: {data.get('total', 0)}")
            publish_tasks = data.get('publish_tasks', [])
            
            # 显示前几个发布任务
            for i, task in enumerate(publish_tasks[:3]):
                print(f"任务 {i+1}: {task['publish_id']} - 状态: {task['status']}")
            
            # 选择一个任务进行测试
            if publish_tasks:
                test_publish_id = publish_tasks[0]['publish_id']
                test_status = publish_tasks[0]['status']
                print(f"选择测试任务: {test_publish_id} (状态: {test_status})")
                
                # 2. 测试重试端点
                print(f"\n2. 测试重试端点 (任务状态: {test_status})...")
                retry_response = requests.post(f"{BASE_URL}/api/publish/retry/{test_publish_id}", headers=headers)
                print(f"重试请求状态码: {retry_response.status_code}")
                if retry_response.status_code == 200:
                    print("重试请求成功:")
                    print(json.dumps(retry_response.json(), ensure_ascii=False, indent=2))
                elif retry_response.status_code == 400:
                    print("重试被拒绝 (可能任务状态不允许重试):")
                    print(json.dumps(retry_response.json(), ensure_ascii=False, indent=2))
                else:
                    print(f"重试请求失败: {retry_response.text}")
                
                # 3. 测试删除端点（对于非上传中的任务）
                if test_status != 'uploading':
                    print(f"\n3. 测试删除端点...")
                    delete_response = requests.delete(f"{BASE_URL}/api/publish/task/{test_publish_id}", headers=headers)
                    print(f"删除请求状态码: {delete_response.status_code}")
                    if delete_response.status_code == 200:
                        print("删除成功:")
                        print(json.dumps(delete_response.json(), ensure_ascii=False, indent=2))
                        
                        # 验证删除是否成功
                        verify_response = requests.get(f"{BASE_URL}/api/publish/history", headers=headers)
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            remaining_tasks = [t for t in verify_data.get('publish_tasks', []) 
                                            if t['publish_id'] == test_publish_id]
                            if not remaining_tasks:
                                print("✓ 验证成功：任务已从数据库中删除")
                            else:
                                print("✗ 验证失败：任务仍存在于数据库中")
                    else:
                        print(f"删除失败: {delete_response.text}")
                else:
                    print(f"\n3. 跳过删除测试 (任务正在上传中)")
            else:
                print("没有找到可用的发布任务进行测试")
        else:
            print(f"获取发布历史失败: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保API服务器正在运行在 http://localhost:51082")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

def test_error_cases():
    """测试错误情况"""
    print("\n" + "=" * 60)
    print("测试错误情况")
    print("=" * 60)
    
    fake_publish_id = "fake_publish_id_12345"
    headers = get_headers()
    
    # 测试不存在的发布任务
    print(f"\n1. 测试重试不存在的发布任务...")
    try:
        response = requests.post(f"{BASE_URL}/api/publish/retry/{fake_publish_id}", headers=headers)
        print(f"状态码: {response.status_code}")
        if response.status_code == 404:
            print("✓ 正确返回404错误:")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        else:
            print(f"✗ 意外的响应: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print(f"\n2. 测试删除不存在的发布任务...")
    try:
        response = requests.delete(f"{BASE_URL}/api/publish/task/{fake_publish_id}", headers=headers)
        print(f"状态码: {response.status_code}")
        if response.status_code == 404:
            print("✓ 正确返回404错误:")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        else:
            print(f"✗ 意外的响应: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_health_check():
    """测试健康检查"""
    print("\n" + "=" * 60)
    print("健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ API服务器运行正常:")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        else:
            print(f"✗ 健康检查失败: {response.text}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")

if __name__ == "__main__":
    print(f"开始测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 先进行健康检查
    test_health_check()
    
    # 测试正常情况
    test_api_endpoints()
    
    # 测试错误情况
    test_error_cases()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)