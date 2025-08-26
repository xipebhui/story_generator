#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块
提供各种实用工具函数
"""

# 导出日志配置函数
from .logging_config import (
    setup_logging,
    get_logger,
    convert_print_to_log,
    safe_print
)

# 导出Windows编码相关函数（仅用于subprocess）
from .windows_encoding import (
    get_subprocess_encoding_env
)

__all__ = [
    'setup_logging',
    'get_logger',
    'convert_print_to_log',
    'safe_print',
    'get_subprocess_encoding_env'
]