#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具
"""

import logging
import os
import sys
import platform
from datetime import datetime
import config

def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    
    # 如果已经有处理器了，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建控制台处理器，Windows需要特殊处理
    if platform.system() == 'Windows':
        # Windows下强制使用UTF-8编码的流
        import codecs
        # 重新配置stdout和stderr使用UTF-8
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建文件处理器
    log_filename = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(config.LOG_DIR, log_filename)
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger