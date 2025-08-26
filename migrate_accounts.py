#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号数据迁移脚本
用于在不同环境之间导出和导入账号数据
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# 加载环境变量
from config_loader import load_env_file
load_env_file()

# 导入数据库模块
from database import init_database, Account
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Note: The database.py Account model has these fields:
# - account_id (unique identifier)
# - account_name (display name)
# - profile_id (BitBrowser Profile ID)
# - channel_url (optional)
# - window_number (optional)
# - description (optional)
# - is_active (boolean, default=True)
# - created_at, updated_at (timestamps)

# But the actual Account table in database.py line 104-135 shows:
# The model matches what we're using here

def export_accounts(output_file: str = None):
    """
    导出所有账号数据到JSON文件
    
    Args:
        output_file: 输出文件路径，默认为 accounts_export_YYYYMMDD_HHMMSS.json
    """
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"accounts_export_{timestamp}.json"
    
    # 初始化数据库
    db_manager = init_database()
    
    # 获取所有账号
    with db_manager.get_session() as session:
        accounts = session.query(Account).all()
        
        # 转换为字典列表
        accounts_data = []
        for account in accounts:
            account_dict = {
                'account_id': account.account_id,
                'account_name': account.account_name,
                'profile_id': account.profile_id,
                'channel_url': account.channel_url,
                'window_number': account.window_number,
                'description': account.description,
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'updated_at': account.updated_at.isoformat() if account.updated_at else None
            }
            accounts_data.append(account_dict)
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'export_time': datetime.now().isoformat(),
            'account_count': len(accounts_data),
            'accounts': accounts_data
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 成功导出 {len(accounts_data)} 个账号到: {output_file}")
    return output_file

def import_accounts(input_file: str, clear_existing: bool = False):
    """
    从JSON文件导入账号数据
    
    Args:
        input_file: 输入文件路径
        clear_existing: 是否清空现有账号数据
    """
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return False
    
    # 读取文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    accounts_data = data.get('accounts', [])
    if not accounts_data:
        print("❌ 文件中没有账号数据")
        return False
    
    # 初始化数据库
    db_manager = init_database()
    
    with db_manager.get_session() as session:
        # 清空现有数据（如果需要）
        if clear_existing:
            existing_count = session.query(Account).count()
            if existing_count > 0:
                confirm = input(f"⚠️  确认要删除现有的 {existing_count} 个账号吗？(yes/no): ")
                if confirm.lower() == 'yes':
                    session.query(Account).delete()
                    session.commit()
                    print(f"已删除 {existing_count} 个现有账号")
                else:
                    print("取消操作")
                    return False
        
        # 导入账号
        imported_count = 0
        updated_count = 0
        
        for account_data in accounts_data:
            # 检查是否已存在
            existing = session.query(Account).filter_by(
                account_id=account_data['account_id']
            ).first()
            
            if existing:
                # 更新现有账号
                existing.account_name = account_data['account_name']
                existing.profile_id = account_data['profile_id']
                existing.channel_url = account_data.get('channel_url')
                existing.window_number = account_data.get('window_number')
                existing.description = account_data.get('description')
                existing.is_active = account_data.get('is_active', True)
                updated_count += 1
                print(f"更新账号: {account_data['account_id']}")
            else:
                # 创建新账号
                account = Account(
                    account_id=account_data['account_id'],
                    account_name=account_data['account_name'],
                    profile_id=account_data['profile_id'],
                    channel_url=account_data.get('channel_url'),
                    window_number=account_data.get('window_number'),
                    description=account_data.get('description'),
                    is_active=account_data.get('is_active', True)
                )
                session.add(account)
                imported_count += 1
                print(f"导入账号: {account_data['account_id']}")
        
        session.commit()
    
    print(f"\n✅ 操作完成:")
    print(f"  - 新导入: {imported_count} 个账号")
    print(f"  - 更新: {updated_count} 个账号")
    return True

def list_accounts():
    """列出当前数据库中的所有账号"""
    db_manager = init_database()
    
    with db_manager.get_session() as session:
        accounts = session.query(Account).all()
        
        if not accounts:
            print("当前数据库中没有账号")
            return
        
        print(f"\n当前数据库中有 {len(accounts)} 个账号:")
        print("-" * 60)
        for account in accounts:
            print(f"ID: {account.account_id}")
            print(f"  名称: {account.account_name}")
            print(f"  Profile ID: {account.profile_id}")
            print(f"  频道URL: {account.channel_url or '未设置'}")
            print(f"  窗口序号: {account.window_number or '未设置'}")
            print(f"  描述: {account.description or '无'}")
            print(f"  状态: {'活跃' if account.is_active else '未激活'}")
            print(f"  创建时间: {account.created_at}")
            print("-" * 60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='账号数据迁移工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 导出账号
  python migrate_accounts.py export
  python migrate_accounts.py export -o my_accounts.json
  
  # 导入账号
  python migrate_accounts.py import -i accounts_export_20241201_120000.json
  python migrate_accounts.py import -i my_accounts.json --clear
  
  # 列出账号
  python migrate_accounts.py list
  
注意:
  - 导出的文件包含profile_id等敏感信息，请妥善保管
  - 导入时默认不会删除现有账号，使用 --clear 参数可清空现有数据
  - 如果账号ID已存在，将更新该账号信息
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='操作命令')
    
    # 导出命令
    export_parser = subparsers.add_parser('export', help='导出账号数据')
    export_parser.add_argument('-o', '--output', help='输出文件路径')
    
    # 导入命令
    import_parser = subparsers.add_parser('import', help='导入账号数据')
    import_parser.add_argument('-i', '--input', required=True, help='输入文件路径')
    import_parser.add_argument('--clear', action='store_true', 
                              help='清空现有账号数据后再导入')
    
    # 列出命令
    list_parser = subparsers.add_parser('list', help='列出当前所有账号')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'export':
        export_accounts(args.output)
    elif args.command == 'import':
        import_accounts(args.input, args.clear)
    elif args.command == 'list':
        list_accounts()

if __name__ == "__main__":
    main()