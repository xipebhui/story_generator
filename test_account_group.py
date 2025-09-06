#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试账号组功能
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000/api/auto-publish"

# 测试数据
test_group_data = {
    "group_name": "测试账号组_自动化",
    "group_type": "production",
    "description": "用于自动化测试的账号组",
    "account_ids": ["yt_010_novel", "yt_009_novel", "yt_008_novel"]
}

def test_create_group():
    """测试创建账号组"""
    print("\n1. 测试创建账号组")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/account-groups",
        json=test_group_data
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"创建成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get("group_id")
    else:
        print(f"创建失败: {response.text}")
        return None

def test_list_groups():
    """测试列出账号组"""
    print("\n2. 测试列出账号组")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/account-groups")
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"账号组列表:")
        for group in result.get("groups", []):
            print(f"\n  组ID: {group['group_id']}")
            print(f"  组名称: {group['group_name']}")
            print(f"  成员数: {group['member_count']}")
            
            # 打印成员信息（如果有）
            if "members" in group and group["members"]:
                print(f"  成员列表:")
                for member in group["members"]:
                    print(f"    - {member['account_id']} ({member.get('account_name', 'N/A')})")
    else:
        print(f"查询失败: {response.text}")

def test_group_detail(group_id):
    """测试获取账号组详情"""
    print(f"\n3. 测试获取账号组详情: {group_id}")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/account-groups/{group_id}")
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"账号组详情: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"查询失败: {response.text}")

def test_group_members(group_id):
    """测试获取账号组成员"""
    print(f"\n4. 测试获取账号组成员: {group_id}")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/account-groups/{group_id}/members")
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"成员信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"查询失败: {response.text}")

def check_accounts():
    """检查账号是否存在"""
    print("\n5. 检查账号是否存在")
    print("="*50)
    
    # 这里需要直接查询数据库或调用账号管理API
    print("检查账号: yt_010_novel, yt_009_novel, yt_008_novel")
    print("如果账号不存在，需要先创建这些账号")

if __name__ == "__main__":
    print("账号组功能测试")
    print("="*50)
    
    # 测试创建
    # group_id = test_create_group()
    
    # 测试列表
    test_list_groups()
    
    # 测试详情（使用已存在的组）
    test_group_detail("group_20250902234836")
    
    # 测试成员
    test_group_members("group_20250902234836")
    
    # 检查账号
    check_accounts()
    
    print("\n测试完成！")
    print("\n建议:")
    print("1. 确保账号 yt_010_novel, yt_009_novel 等已经存在于accounts表中")
    print("2. 检查日志输出，查看账号组创建过程中的详细信息")
    print("3. 使用新的列表接口应该能看到members字段")