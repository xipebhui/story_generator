#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复和测试账号组功能
"""

from database import get_db_manager, Account
from models_auto_publish import AccountGroupModel, AccountGroupMemberModel
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_accounts():
    """创建测试账号"""
    print("\n创建测试账号")
    print("="*50)
    
    db = get_db_manager()
    test_accounts = [
        {"account_id": "yt_008_novel", "account_name": "小说频道008", "profile_id": "profile_008"},
        {"account_id": "yt_009_novel", "account_name": "小说频道009", "profile_id": "profile_009"},
        {"account_id": "yt_010_novel", "account_name": "小说频道010", "profile_id": "profile_010"},
    ]
    
    with db.get_session() as session:
        for acc_data in test_accounts:
            # 检查是否存在
            existing = session.query(Account).filter_by(
                account_id=acc_data["account_id"]
            ).first()
            
            if not existing:
                account = Account(
                    account_id=acc_data["account_id"],
                    account_name=acc_data["account_name"],
                    profile_id=acc_data["profile_id"],
                    channel_url=f"https://youtube.com/@{acc_data['account_id']}",
                    is_active=True
                )
                session.add(account)
                print(f"✅ 创建账号: {acc_data['account_id']}")
            else:
                print(f"⚠️ 账号已存在: {acc_data['account_id']}")
        
        session.commit()

def list_all_accounts():
    """列出所有账号"""
    print("\n所有账号列表")
    print("="*50)
    
    db = get_db_manager()
    with db.get_session() as session:
        accounts = session.query(Account).filter_by(is_active=True).all()
        
        print(f"共找到 {len(accounts)} 个账号:")
        for acc in accounts:
            print(f"  - {acc.account_id}: {acc.account_name} (profile: {acc.profile_id})")

def check_account_groups():
    """检查账号组及其成员"""
    print("\n账号组信息")
    print("="*50)
    
    db = get_db_manager()
    with db.get_session() as session:
        groups = session.query(AccountGroupModel).filter_by(is_active=True).all()
        
        print(f"共找到 {len(groups)} 个账号组:")
        for group in groups:
            # 获取成员
            members = session.query(AccountGroupMemberModel).filter_by(
                group_id=group.group_id,
                is_active=True
            ).all()
            
            print(f"\n组ID: {group.group_id}")
            print(f"组名: {group.group_name}")
            print(f"类型: {group.group_type}")
            print(f"成员数: {len(members)}")
            
            if members:
                print("成员列表:")
                for member in members:
                    # 获取账号信息
                    account = session.query(Account).filter_by(
                        account_id=member.account_id
                    ).first()
                    
                    if account:
                        print(f"  - {account.account_id}: {account.account_name}")
                    else:
                        print(f"  - {member.account_id}: [账号不存在]")

def fix_orphan_members():
    """修复孤立的成员记录（账号不存在的成员）"""
    print("\n修复孤立成员记录")
    print("="*50)
    
    db = get_db_manager()
    with db.get_session() as session:
        # 获取所有成员
        all_members = session.query(AccountGroupMemberModel).filter_by(
            is_active=True
        ).all()
        
        orphan_count = 0
        for member in all_members:
            # 检查账号是否存在
            account = session.query(Account).filter_by(
                account_id=member.account_id
            ).first()
            
            if not account:
                print(f"⚠️ 发现孤立成员: {member.account_id} in group {member.group_id}")
                # 可以选择删除或标记为非活跃
                member.is_active = False
                orphan_count += 1
        
        if orphan_count > 0:
            session.commit()
            print(f"✅ 标记 {orphan_count} 个孤立成员为非活跃")
        else:
            print("✅ 没有发现孤立成员")

if __name__ == "__main__":
    print("账号组功能修复和测试")
    print("="*50)
    
    # 1. 创建测试账号
    create_test_accounts()
    
    # 2. 列出所有账号
    list_all_accounts()
    
    # 3. 检查账号组
    check_account_groups()
    
    # 4. 修复孤立成员
    fix_orphan_members()
    
    print("\n修复完成！")
    print("\n现在可以:")
    print("1. 重启服务")
    print("2. 访问账号组管理页面")
    print("3. 账号组列表应该能显示成员信息了")