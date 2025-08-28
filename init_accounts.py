#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动初始化账号数据
只在需要重置或首次设置时运行
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from account_service import get_account_service
from database import get_db_manager

def init_accounts(force=False):
    """
    初始化账号数据
    
    Args:
        force: 是否强制重新初始化（会覆盖现有账号）
    """
    print("="*60)
    print("账号初始化工具")
    print("="*60)
    
    account_service = get_account_service()
    db = get_db_manager()
    
    # 检查现有账号
    existing_accounts = account_service.get_all_accounts(active_only=False)
    
    if existing_accounts and not force:
        print(f"\n当前已有 {len(existing_accounts)} 个账号:")
        for acc in existing_accounts:
            status = "✅ 活跃" if acc.get('is_active', False) else "❌ 禁用"
            print(f"  - {acc.get('account_name')} ({acc.get('account_id')}) {status}")
        
        response = input("\n是否要重新初始化账号？这将保留已有账号，只添加缺失的账号 (y/N): ")
        if response.lower() != 'y':
            print("取消操作")
            return
    
    # 初始化账号
    print("\n开始初始化账号...")
    created_count = account_service.initialize_accounts(force=force)
    
    print(f"\n✅ 初始化完成，新增 {created_count} 个账号")
    
    # 显示所有账号
    all_accounts = account_service.get_all_accounts(active_only=False)
    print(f"\n当前共有 {len(all_accounts)} 个账号:")
    
    for acc in all_accounts:
        status = "✅ 活跃" if acc.get('is_active', False) else "❌ 禁用"
        print(f"  - {acc.get('account_name')} ({acc.get('account_id')}) {status}")
        print(f"    Profile ID: {acc.get('profile_id')}")
        print(f"    窗口序号: {acc.get('window_number')}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='初始化YouTube账号数据')
    parser.add_argument('--force', action='store_true', 
                       help='强制重新初始化（会覆盖现有账号）')
    
    args = parser.parse_args()
    
    if args.force:
        print("⚠️  警告：强制模式会覆盖所有现有账号数据！")
        response = input("确定要继续吗？(yes/N): ")
        if response.lower() != 'yes':
            print("取消操作")
            return
    
    init_accounts(force=args.force)

if __name__ == "__main__":
    main()