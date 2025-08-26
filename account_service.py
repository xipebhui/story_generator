#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理服务
负责YouTube账号的初始化和管理
"""

import logging
from typing import List, Dict, Any, Optional
from database import get_db_manager, Account

logger = logging.getLogger(__name__)

# 预定义的账号数据
PRESET_ACCOUNTS = [
    {
        "account_id": "yt_009_novel_remote_1",
        "account_name": "youtube-009-小说-远端_1",
        "profile_id": "609c4b20df3149209eebeea474a2d7c2",
        "window_number": "1974",
        "description": "窗口序号: 1974",
        "is_active": True
    },
    {
        "account_id": "yt_010_novel",
        "account_name": "youtube-010-小说",
        "profile_id": "34f2833b44dc46f9a1645cc364647ed1",
        "window_number": "1973",
        "description": "窗口序号: 1973",
        "is_active": True
    },
    {
        "account_id": "yt_009_novel",
        "account_name": "youtube-009-小说",
        "profile_id": "73438dd4924c4a11a970ed647f88404d",
        "window_number": "1972",
        "description": "窗口序号: 1972",
        "is_active": True
    },
    {
        "account_id": "yt_008_novel_1",
        "account_name": "youtube-008-小说_1",
        "profile_id": "e6015e07704b43dbbb656ca71f203a42",
        "window_number": "1971",
        "description": "窗口序号: 1971",
        "is_active": True
    },
    {
        "account_id": "yt_007_deprecated",
        "account_name": "youtube-007-废了",
        "profile_id": "44810ff5155b41129a2884a5ebbb7ae8",
        "window_number": "1970",
        "description": "窗口序号: 1970",
        "is_active": False  # 标记为不活跃
    },
    {
        "account_id": "yt_004_same",
        "account_name": "youtube-004-一样的号",
        "profile_id": "72a55bd4d9794c839dfbb8d6e4a4ef18",
        "window_number": "1969",
        "description": "窗口序号: 1969",
        "is_active": True
    },
    {
        "account_id": "yt_005_novel",
        "account_name": "youtube-005-小说",
        "profile_id": "b4281319094d40f09804ce5a55b86645",
        "window_number": "1968",
        "description": "窗口序号: 1968",
        "is_active": True
    },
    {
        "account_id": "yt_004_novel",
        "account_name": "youtube-004-小说",
        "profile_id": "901dfe74956c480bae42ba8178bbfe6a",
        "window_number": "1967",
        "description": "窗口序号: 1967",
        "is_active": True
    },
    {
        "account_id": "yt_0622",
        "account_name": "0622",
        "profile_id": "1d232a5b810046b09b913f658ed8e152",
        "window_number": "1966",
        "description": "窗口序号: 1966",
        "is_active": True
    },
    {
        "account_id": "yt_0624",
        "account_name": "0624",
        "profile_id": "b4137d12faf54446a43187307ed770dc",
        "window_number": "1965",
        "description": "窗口序号: 1965",
        "is_active": True
    },
    {
        "account_id": "yt_0623",
        "account_name": "0623",
        "profile_id": "c3127778f3a140c790be9d209ae57f62",
        "window_number": "1964",
        "description": "窗口序号: 1964",
        "is_active": True
    },
    {
        "account_id": "yt_1122",
        "account_name": "1122",
        "profile_id": "cbccb8ef8dc340f5bd77c37c665f45ab",
        "window_number": "1963",
        "description": "窗口序号: 1963",
        "is_active": True
    },
    {
        "account_id": "yt_003_novel",
        "account_name": "youtube-003-小说",
        "profile_id": "d9adfc1638fe4028be414c04ed9da3d5",
        "window_number": "1962",
        "description": "窗口序号: 1962",
        "is_active": True
    },
    {
        "account_id": "yt_002_novel",
        "account_name": "youtube-002-小说",
        "profile_id": "5ec48b6dd0e146708e0606042fd5bbbe",
        "window_number": "1961",
        "description": "窗口序号: 1961",
        "is_active": True
    },
    {
        "account_id": "yt_001_novel",
        "account_name": "youtube-001-小说",
        "profile_id": "1590cf235ecf4d66bf7e1f57242d520f",
        "window_number": "1960",
        "description": "窗口序号: 1960",
        "is_active": True
    }
]


class AccountService:
    """账号管理服务类"""
    
    def __init__(self):
        self.db = get_db_manager()
        self._initialized = False
    
    def initialize_accounts(self, force: bool = False) -> int:
        """
        初始化账号数据
        
        Args:
            force: 是否强制重新初始化（会清除现有数据）
        
        Returns:
            创建的账号数量
        """
        created_count = 0
        
        for account_data in PRESET_ACCOUNTS:
            try:
                # 检查账号是否存在
                existing = self.db.get_account(account_data['account_id'])
                
                if existing and not force:
                    logger.debug(f"账号已存在，跳过: {account_data['account_id']}")
                    continue
                
                if existing and force:
                    # 更新现有账号
                    self.db.update_account(account_data['account_id'], account_data)
                    logger.info(f"更新账号: {account_data['account_id']}")
                else:
                    # 创建新账号
                    self.db.create_account(account_data)
                    created_count += 1
                    logger.info(f"创建账号: {account_data['account_id']}")
                    
            except Exception as e:
                logger.error(f"初始化账号失败 {account_data['account_id']}: {e}")
        
        self._initialized = True
        logger.info(f"账号初始化完成，新增 {created_count} 个账号")
        return created_count
    
    def get_all_accounts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有账号
        
        Args:
            active_only: 是否只返回活跃账号
        
        Returns:
            账号列表
        """
        if not self._initialized:
            self.initialize_accounts()
        
        if active_only:
            accounts = self.db.get_active_accounts()
        else:
            with self.db.get_session() as session:
                accounts = session.query(Account).all()
        
        return [account.to_dict() for account in accounts]
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取账号信息
        
        Args:
            account_id: 账号ID
        
        Returns:
            账号信息字典，不存在返回None
        """
        account = self.db.get_account(account_id)
        return account.to_dict() if account else None
    
    def get_account_by_name(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取账号信息
        
        Args:
            account_name: 账号名称
        
        Returns:
            账号信息字典，不存在返回None
        """
        with self.db.get_session() as session:
            account = session.query(Account).filter_by(account_name=account_name).first()
            return account.to_dict() if account else None
    
    def get_accounts_for_rotation(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        获取用于轮流发布的账号列表
        
        Args:
            limit: 返回账号数量
        
        Returns:
            账号列表
        """
        # 获取活跃账号
        accounts = self.get_all_accounts(active_only=True)
        
        # 按最近发布时间排序（这里简化处理，实际可根据发布历史排序）
        # TODO: 可以根据PublishTask表的历史记录来选择最少使用的账号
        
        return accounts[:limit]
    
    def update_account_status(self, account_id: str, is_active: bool) -> bool:
        """
        更新账号状态
        
        Args:
            account_id: 账号ID
            is_active: 是否激活
        
        Returns:
            更新是否成功
        """
        result = self.db.update_account(account_id, {'is_active': is_active})
        return result is not None
    
    def get_account_statistics(self, account_id: str) -> Dict[str, Any]:
        """
        获取账号统计信息
        
        Args:
            account_id: 账号ID
        
        Returns:
            统计信息字典
        """
        with self.db.get_session() as session:
            from database import PublishTask
            
            # 总发布数
            total = session.query(PublishTask)\
                .filter_by(account_id=account_id)\
                .count()
            
            # 成功数
            success = session.query(PublishTask)\
                .filter_by(account_id=account_id, status='success')\
                .count()
            
            # 失败数
            failed = session.query(PublishTask)\
                .filter_by(account_id=account_id, status='failed')\
                .count()
            
            # 待发布数
            pending = session.query(PublishTask)\
                .filter_by(account_id=account_id, status='pending')\
                .count()
            
            return {
                'account_id': account_id,
                'total_publish': total,
                'success': success,
                'failed': failed,
                'pending': pending,
                'success_rate': (success / total * 100) if total > 0 else 0
            }


# 全局服务实例
account_service = AccountService()

def get_account_service() -> AccountService:
    """获取账号服务实例"""
    return account_service