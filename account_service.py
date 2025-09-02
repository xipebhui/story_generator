#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理服务
负责YouTube账号的初始化和管理
"""

import os
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# YTEngine服务配置 - 与upload服务共用
YTENGINE_HOST = os.environ.get('YTENGINE_HOST', 'http://localhost:51077')

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
        # 不再需要数据库管理器，使用与upload服务相同的host
        self._account_api_url = f"{YTENGINE_HOST}/api/accounts"
        self._cache = None  # 可以添加缓存机制
        self._cache_time = None
        logger.info(f"账号服务初始化，使用API: {self._account_api_url}")
    
    def initialize_accounts(self, force: bool = False) -> int:
        """
        初始化账号数据 - 现在只是预加载账号缓存
        
        Args:
            force: 是否强制刷新缓存
        
        Returns:
            获取到的账号数量
        """
        try:
            accounts = self.get_all_accounts(active_only=False)
            logger.info(f"账号初始化完成，获取到 {len(accounts)} 个账号")
            return len(accounts)
        except Exception as e:
            logger.error(f"初始化账号失败: {e}")
            return 0
    
    def get_all_accounts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有账号 - 从远程API获取
        
        Args:
            active_only: 是否只返回活跃账号
        
        Returns:
            账号列表
        """
        try:
            # 调用新的API接口
            response = requests.get(self._account_api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('success', False):
                logger.error(f"获取账号失败: {data}")
                return []
            
            accounts = data.get('accounts', [])
            
            # 转换字段名以适配现有系统
            converted_accounts = []
            for acc in accounts:
                # 只处理活跃账号或者返回所有账号
                if active_only and acc.get('status') != 'active':
                    continue
                
                converted_account = {
                    'account_id': acc.get('id', ''),
                    'account_name': acc.get('displayName', acc.get('channelName', '')),
                    'profile_id': acc.get('profileId', ''),
                    'window_number': '',  # 新接口没有这个字段
                    'description': acc.get('remark', ''),
                    'is_active': acc.get('status') == 'active',
                    'channel_url': acc.get('channelUrl', ''),
                    'email': acc.get('email', ''),
                    'daily_quota': acc.get('dailyQuota', 50),
                    'today_uploaded': acc.get('todayUploaded', 0),
                    'total_uploaded': acc.get('totalUploaded', 0),
                    'success_count': acc.get('successCount', 0),
                    'failed_count': acc.get('failedCount', 0),
                    'created_at': acc.get('createdAt', ''),
                    'updated_at': acc.get('updatedAt', '')
                }
                converted_accounts.append(converted_account)
            
            logger.info(f"成功获取 {len(converted_accounts)} 个账号")
            return converted_accounts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"调用账号API失败: {e}")
            # 发生错误时返回空列表或者可以考虑使用缓存的数据
            return []
        except Exception as e:
            logger.error(f"处理账号数据失败: {e}")
            return []
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取账号信息 - 从远程API获取
        
        Args:
            account_id: 账号ID
        
        Returns:
            账号信息字典，不存在返回None
        """
        try:
            # 获取所有账号，然后过滤出指定ID的账号
            all_accounts = self.get_all_accounts(active_only=False)
            
            for account in all_accounts:
                if account.get('account_id') == account_id:
                    return account
            
            logger.warning(f"账号不存在: {account_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取账号信息失败: {e}")
            return None
    
    def get_account_by_name(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取账号信息 - 从远程API获取
        
        Args:
            account_name: 账号名称
        
        Returns:
            账号信息字典，不存在返回None
        """
        try:
            # 获取所有账号，然后过滤出指定名称的账号
            all_accounts = self.get_all_accounts(active_only=False)
            
            for account in all_accounts:
                if account.get('account_name') == account_name:
                    return account
            
            logger.warning(f"账号不存在: {account_name}")
            return None
            
        except Exception as e:
            logger.error(f"获取账号信息失败: {e}")
            return None
    
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
        更新账号状态 - 此功能需要远程API支持
        
        Args:
            account_id: 账号ID
            is_active: 是否激活
        
        Returns:
            更新是否成功
        """
        logger.warning(f"账号状态更新功能暂不支持（需要远程API支持）: {account_id}")
        # 如果远程API支持更新，可以在这里实现
        # 目前返回False表示不支持
        return False
    
    def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        创建新账号 - 此功能需要远程API支持
        
        Args:
            account_data: 账号数据，包含:
                - account_id: 账号ID（必需）
                - account_name: 账号名称（必需）
                - profile_id: 比特浏览器Profile ID（必需）
                - window_number: 窗口序号（可选）
                - description: 描述信息（可选）
                - is_active: 是否激活（默认True）
        
        Returns:
            创建成功返回账号信息，失败返回None
        """
        logger.warning("账号创建功能暂不支持（需要远程API支持）")
        # 如果远程API支持创建，可以在这里实现
        # 目前返回None表示不支持
        return None
    
    def delete_account(self, account_id: str) -> bool:
        """
        删除账号 - 此功能需要远程API支持
        
        Args:
            account_id: 账号ID
        
        Returns:
            删除成功返回True，失败返回False
        """
        logger.warning(f"账号删除功能暂不支持（需要远程API支持）: {account_id}")
        # 如果远程API支持删除，可以在这里实现
        # 目前返回False表示不支持
        return False
    
    def get_account_statistics(self, account_id: str) -> Dict[str, Any]:
        """
        获取账号统计信息 - 从远程API获取的账号数据中提取
        
        Args:
            account_id: 账号ID
        
        Returns:
            统计信息字典
        """
        try:
            # 获取账号信息
            account = self.get_account_by_id(account_id)
            
            if not account:
                return {
                    'account_id': account_id,
                    'total_publish': 0,
                    'success': 0,
                    'failed': 0,
                    'pending': 0,
                    'success_rate': 0
                }
            
            # 从账号信息中提取统计数据
            total = account.get('total_uploaded', 0)
            success = account.get('success_count', 0)
            failed = account.get('failed_count', 0)
            
            return {
                'account_id': account_id,
                'total_publish': total,
                'success': success,
                'failed': failed,
                'pending': 0,  # 新API没有pending信息
                'success_rate': (success / total * 100) if total > 0 else 0,
                'daily_quota': account.get('daily_quota', 50),
                'today_uploaded': account.get('today_uploaded', 0)
            }
            
        except Exception as e:
            logger.error(f"获取账号统计信息失败: {e}")
            return {
                'account_id': account_id,
                'total_publish': 0,
                'success': 0,
                'failed': 0,
                'pending': 0,
                'success_rate': 0
            }


# 全局服务实例
account_service = AccountService()

def get_account_service() -> AccountService:
    """获取账号服务实例"""
    return account_service