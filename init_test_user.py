#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试用户
"""

from database import get_db_manager
from auth_middleware import hash_password, generate_api_key

def create_test_user():
    """创建测试用户"""
    db = get_db_manager()
    
    # 检查是否已存在测试用户
    existing_user = db.get_user_by_username("test_user")
    if existing_user:
        print(f"测试用户已存在，API Key: {existing_user.api_key}")
        return existing_user.api_key
    
    # 创建测试用户
    api_key = generate_api_key()
    user_data = {
        "username": "test_user",
        "password_hash": hash_password("test123"),
        "api_key": api_key,
        "is_active": True
    }
    
    user = db.create_user(user_data)
    print(f"创建测试用户成功")
    print(f"用户名: test_user")
    print(f"API Key: {api_key}")
    
    return api_key

if __name__ == "__main__":
    api_key = create_test_user()
    print(f"\n使用此API Key进行测试: {api_key}")