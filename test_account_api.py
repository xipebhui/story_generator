#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试账号管理API接口
"""

import requests
import json
import uuid
from datetime import datetime

# API基础配置
BASE_URL = "http://localhost:8000"
API_KEY = "test_api_key_123"  # 使用测试API密钥

# 请求头
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_create_account():
    """测试创建账号"""
    print("\n" + "="*60)
    print("测试创建账号接口 - POST /api/accounts")
    print("="*60)
    
    # 生成测试账号数据
    test_account = {
        "account_id": f"test_account_{uuid.uuid4().hex[:8]}",
        "account_name": f"测试账号-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "profile_id": uuid.uuid4().hex,
        "window_number": "9999",
        "description": "这是一个测试账号",
        "is_active": True,
        "channel_url": "https://www.youtube.com/@testchannel"
    }
    
    print(f"\n1. 创建新账号:")
    print(f"   账号ID: {test_account['account_id']}")
    print(f"   账号名称: {test_account['account_name']}")
    
    # 发送创建请求
    response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json=test_account
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 创建成功: {result.get('message')}")
        print(f"   返回数据: {json.dumps(result.get('account'), ensure_ascii=False, indent=2)}")
        return test_account['account_id']
    else:
        print(f"   ❌ 创建失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return None

def test_get_account(account_id):
    """测试获取账号信息"""
    print("\n2. 获取账号信息:")
    print(f"   账号ID: {account_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/accounts/{account_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        account = response.json()
        print(f"   ✅ 获取成功:")
        print(f"   账号名称: {account.get('account_name')}")
        print(f"   Profile ID: {account.get('profile_id')}")
        print(f"   状态: {'激活' if account.get('is_active') else '禁用'}")
    else:
        print(f"   ❌ 获取失败: {response.status_code}")
        print(f"   错误信息: {response.text}")

def test_list_accounts():
    """测试获取账号列表"""
    print("\n3. 获取账号列表:")
    
    response = requests.get(
        f"{BASE_URL}/api/accounts",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 获取成功:")
        print(f"   账号总数: {result.get('total')}")
        
        accounts = result.get('accounts', [])
        if accounts:
            print("   账号列表:")
            for acc in accounts[:5]:  # 显示前5个
                status = "✅" if acc.get('is_active') else "❌"
                print(f"     {status} {acc.get('account_id')} - {acc.get('account_name')}")
            
            if len(accounts) > 5:
                print(f"     ... 还有 {len(accounts) - 5} 个账号")
    else:
        print(f"   ❌ 获取失败: {response.status_code}")
        print(f"   错误信息: {response.text}")

def test_update_account_status(account_id):
    """测试更新账号状态"""
    print("\n4. 更新账号状态:")
    print(f"   账号ID: {account_id}")
    print(f"   设置为: 禁用")
    
    response = requests.put(
        f"{BASE_URL}/api/accounts/{account_id}/status?is_active=false",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 更新成功: {result.get('message')}")
    else:
        print(f"   ❌ 更新失败: {response.status_code}")
        print(f"   错误信息: {response.text}")

def test_delete_account(account_id):
    """测试删除账号"""
    print("\n5. 删除账号:")
    print(f"   账号ID: {account_id}")
    
    response = requests.delete(
        f"{BASE_URL}/api/accounts/{account_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 删除成功:")
        print(f"   消息: {result.get('message')}")
        print(f"   操作: {result.get('action')}")
    else:
        print(f"   ❌ 删除失败: {response.status_code}")
        print(f"   错误信息: {response.text}")

def test_create_duplicate_account():
    """测试创建重复账号（应该失败）"""
    print("\n6. 测试创建重复账号（预期失败）:")
    
    # 使用固定的账号ID
    duplicate_account = {
        "account_id": "yt_004_novel",  # 这个ID已存在
        "account_name": "重复的账号",
        "profile_id": "test_profile_id"
    }
    
    print(f"   尝试创建已存在的账号ID: {duplicate_account['account_id']}")
    
    response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json=duplicate_account
    )
    
    if response.status_code != 200:
        print(f"   ✅ 正确拒绝创建重复账号")
        print(f"   状态码: {response.status_code}")
        try:
            error = response.json()
            print(f"   错误信息: {error.get('detail')}")
        except:
            print(f"   错误信息: {response.text}")
    else:
        print(f"   ❌ 错误：不应该允许创建重复账号")

def test_delete_account_with_tasks():
    """测试删除有发布任务的账号（应该软删除）"""
    print("\n7. 测试删除有发布任务的账号:")
    
    # 使用一个可能有发布任务的账号
    account_id = "bearreddit"
    
    print(f"   尝试删除账号: {account_id}")
    print(f"   注：如果账号有发布任务，将被标记为不活跃而非删除")
    
    response = requests.delete(
        f"{BASE_URL}/api/accounts/{account_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 操作成功:")
        print(f"   消息: {result.get('message')}")
        print(f"   操作类型: {result.get('action')}")
        
        if result.get('action') == 'deactivated':
            print(f"   说明: 账号有发布任务，已标记为不活跃")
        else:
            print(f"   说明: 账号已被完全删除")
    else:
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("账号管理API测试")
    print("="*60)
    print(f"API服务器: {BASE_URL}")
    print(f"请确保API服务已启动")
    
    try:
        # 测试服务是否可用
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ API服务不可用，请先启动服务")
            return
    except:
        print("❌ 无法连接到API服务，请先启动服务")
        return
    
    # 运行测试
    print("\n开始测试...")
    
    # 1. 创建账号
    account_id = test_create_account()
    
    if account_id:
        # 2. 获取账号信息
        test_get_account(account_id)
        
        # 3. 获取账号列表
        test_list_accounts()
        
        # 4. 更新账号状态
        test_update_account_status(account_id)
        
        # 5. 删除账号
        test_delete_account(account_id)
    
    # 6. 测试创建重复账号
    test_create_duplicate_account()
    
    # 7. 测试删除有任务的账号
    test_delete_account_with_tasks()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    main()