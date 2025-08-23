#!/usr/bin/env python3
"""
配置加载器
自动加载.env文件中的环境变量
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    加载.env文件到环境变量
    
    Args:
        env_path: .env文件路径，如果不指定则查找项目根目录的.env文件
    """
    try:
        # 如果没有指定路径，查找项目根目录的.env文件
        if env_path is None:
            # 查找当前文件所在目录的.env文件
            current_dir = Path(__file__).parent
            env_path = current_dir / '.env'
            
            # 如果当前目录没有，向上查找
            if not env_path.exists():
                for parent in current_dir.parents:
                    potential_env = parent / '.env'
                    if potential_env.exists():
                        env_path = potential_env
                        break
        else:
            env_path = Path(env_path)
        
        # 检查文件是否存在
        if not env_path.exists():
            logger.warning(f".env文件不存在: {env_path}")
            return
        
        # 读取并加载环境变量
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 跳过注释和空行
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除值两端的引号（如果有）
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # 设置环境变量（只有当变量不存在时才设置，避免覆盖已有的环境变量）
                    if key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"加载环境变量: {key}")
        
        logger.info(f"成功加载.env文件: {env_path}")
        
    except Exception as e:
        logger.error(f"加载.env文件失败: {e}")


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    获取配置值
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        配置值或默认值
    """
    return os.environ.get(key, default)


def get_int_config(key: str, default: int = 0) -> int:
    """
    获取整数配置值
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        整数配置值或默认值
    """
    value = os.environ.get(key)
    if value:
        try:
            return int(value)
        except ValueError:
            logger.warning(f"配置项 {key} 的值 '{value}' 不是有效的整数，使用默认值 {default}")
    return default


def get_bool_config(key: str, default: bool = False) -> bool:
    """
    获取布尔配置值
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        布尔配置值或默认值
    """
    value = os.environ.get(key, '').lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    elif value in ('false', '0', 'no', 'off'):
        return False
    return default


# 自动加载.env文件
load_env_file()