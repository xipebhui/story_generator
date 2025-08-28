#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区配置模块
设置系统时区为东八区（UTC+8）
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

# 定义东八区时区
UTC_8 = timezone(timedelta(hours=8))
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_now() -> datetime:
    """
    获取当前北京时间（东八区）
    返回带时区信息的datetime对象
    """
    return datetime.now(BEIJING_TZ)

def get_utc8_now() -> datetime:
    """
    获取当前UTC+8时间
    返回带时区信息的datetime对象
    """
    return datetime.now(UTC_8)

def to_beijing_time(dt: Optional[datetime]) -> Optional[datetime]:
    """
    转换datetime对象到北京时间
    
    Args:
        dt: datetime对象（可能没有时区信息）
    
    Returns:
        带北京时区的datetime对象
    """
    if dt is None:
        return None
    
    # 如果已经有时区信息，转换到北京时区
    if dt.tzinfo is not None:
        return dt.astimezone(BEIJING_TZ)
    
    # 如果没有时区信息，假设是北京时间
    return BEIJING_TZ.localize(dt)

def format_beijing_time(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化datetime为北京时间字符串
    
    Args:
        dt: datetime对象
        fmt: 格式化字符串
    
    Returns:
        格式化的时间字符串，带时区标记
    """
    if dt is None:
        return ""
    
    beijing_dt = to_beijing_time(dt)
    return f"{beijing_dt.strftime(fmt)} (UTC+8)"

def get_sqlite_timezone_sql() -> str:
    """
    获取SQLite设置时区的SQL语句
    注意：SQLite本身不支持时区，但可以通过这种方式调整时间
    """
    # SQLite使用UTC时间，我们需要在应用层处理时区
    return """
    -- SQLite doesn't have timezone support
    -- We handle timezone conversion in application layer
    -- All timestamps are stored as UTC and converted to Beijing time when displayed
    """