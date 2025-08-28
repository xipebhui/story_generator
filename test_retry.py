#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重试功能 - 验证任务ID是否保持不变
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:51082"

# 认证Token（使用创建的测试用户token）
AUTH_TOKEN = "e20fe249-d47c-4b58-994f-190e95c047e5"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_retry_preserves_task_id():
    """测试重试功能是否保留原任务ID"""
    
    # 1. 创建一个测试任务
    print("=" * 60)
    print("测试重试功能 - 验证任务ID保持不变")
    print("=" * 60)
    
    # 创建任务参数
    create_data = {
        "video_id": "test_retry_001",
        "creator_id": "test_user",
        "account_name": "youtube-001-小说",  # 包含账号名称
        "gender": 1,
        "duration": 60,
        "image_dir": "default",
        "export_video": False,
        "enable_subtitle": True
    }
    
    print("\n1. 创建测试任务...")
    print(f"   请求参数: {json.dumps(create_data, ensure_ascii=False, indent=2)}")
    
    # 发送创建请求
    response = requests.post(f"{BASE_URL}/api/pipeline/run", json=create_data, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"   ❌ 创建任务失败: {response.text}")
        return
    
    result = response.json()
    original_task_id = result['task_id']
    print(f"   ✅ 任务创建成功")
    print(f"   任务ID: {original_task_id}")
    
    # 2. 查询任务状态
    print("\n2. 查询任务状态...")
    status_response = requests.get(f"{BASE_URL}/api/pipeline/status/{original_task_id}", headers=HEADERS)
    
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"   任务状态: {status['status']}")
        print(f"   当前阶段: {status.get('current_stage', '未开始')}")
    
    # 3. 等待任务完成或失败
    print("\n3. 等待任务完成或失败...")
    max_wait = 30  # 最多等待30秒
    wait_count = 0
    
    while wait_count < max_wait:
        status_check = requests.get(f"{BASE_URL}/api/pipeline/status/{original_task_id}", headers=HEADERS)
        if status_check.status_code == 200:
            current_status = status_check.json()
            print(f"   [{wait_count}s] 状态: {current_status['status']}, 阶段: {current_status.get('current_stage', '未知')}")
            
            if current_status['status'] in ['completed', 'failed']:
                print(f"   任务已结束，状态: {current_status['status']}")
                break
        
        time.sleep(1)
        wait_count += 1
    
    print("\n4. 测试重试功能...")
    print(f"   原任务ID: {original_task_id}")
    
    # 发送重试请求
    retry_response = requests.post(f"{BASE_URL}/api/pipeline/retry/{original_task_id}", headers=HEADERS)
    
    if retry_response.status_code != 200:
        print(f"   ❌ 重试失败: {retry_response.text}")
        return
    
    retry_result = retry_response.json()
    retry_task_id = retry_result['task_id']
    
    print(f"   ✅ 重试成功")
    print(f"   重试后任务ID: {retry_task_id}")
    print(f"   重试次数: {retry_result.get('retry_count', 1)}")
    print(f"   消息: {retry_result.get('message', '')}")
    
    # 5. 验证任务ID是否保持一致
    print("\n5. 验证结果...")
    if original_task_id == retry_task_id:
        print(f"   ✅ 成功！任务ID保持不变: {original_task_id}")
    else:
        print(f"   ❌ 失败！任务ID发生了变化:")
        print(f"      原任务ID: {original_task_id}")
        print(f"      新任务ID: {retry_task_id}")
    
    # 6. 再次查询状态确认
    print("\n6. 查询重试后的任务状态...")
    final_status_response = requests.get(f"{BASE_URL}/api/pipeline/status/{retry_task_id}", headers=HEADERS)
    
    if final_status_response.status_code == 200:
        final_status = final_status_response.json()
        print(f"   任务状态: {final_status['status']}")
        print(f"   进度: {json.dumps(final_status.get('progress', {}), ensure_ascii=False)}")
    
    # 7. 检查账号信息是否保留
    print("\n7. 验证账号信息...")
    if "youtube-001-小说" in original_task_id:
        print(f"   ✅ 原任务ID包含账号信息")
    else:
        print(f"   ⚠️ 原任务ID不包含账号信息")
    
    if "youtube-001-小说" in retry_task_id:
        print(f"   ✅ 重试任务ID包含账号信息")
    else:
        print(f"   ⚠️ 重试任务ID不包含账号信息")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_retry_preserves_task_id()
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()