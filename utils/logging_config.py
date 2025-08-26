#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志配置模块
提供跨平台的UTF-8日志输出支持
"""

import logging
import sys
import os
import platform
from pathlib import Path
from typing import Optional


def setup_logging(
    name: Optional[str] = None,
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    console: bool = True,
    file_log: bool = True
) -> logging.Logger:
    """
    配置日志系统，支持控制台和文件输出
    
    Args:
        name: Logger名称，None则使用root logger
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名，None则自动生成
        log_dir: 日志目录
        console: 是否输出到控制台
        file_log: 是否输出到文件
        
    Returns:
        配置好的logger实例
    """
    # 获取或创建logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    
    # 清空现有的处理器，避免重复
    logger.handlers.clear()
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建格式器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # Windows平台特殊处理：确保UTF-8输出
        if platform.system() == 'Windows':
            # 设置环境变量
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONUTF8'] = '1'
            
            # 设置控制台代码页（不影响Python内部处理）
            try:
                os.system('chcp 65001 > nul 2>&1')
            except:
                pass
        
        logger.addHandler(console_handler)
    
    # 文件处理器
    if file_log:
        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 生成日志文件名
        if not log_file:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            module_name = name or "app"
            log_file = f"{module_name}_{timestamp}.log"
        
        file_path = log_path / log_file
        
        # 创建文件处理器，始终使用UTF-8编码
        file_handler = logging.FileHandler(
            file_path, 
            mode='a', 
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
    # 防止日志向上传播到root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的logger实例
    如果不存在，则创建一个新的
    
    Args:
        name: Logger名称
        
    Returns:
        Logger实例
    """
    logger = logging.getLogger(name)
    
    # 如果logger没有处理器，配置它
    if not logger.handlers:
        # 从环境变量读取配置
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        log_dir = os.environ.get('LOG_DIR', 'logs')
        
        return setup_logging(
            name=name,
            level=log_level,
            log_dir=log_dir
        )
    
    return logger


def convert_print_to_log(message: str, level: str = "INFO") -> None:
    """
    用于替代print语句的函数
    
    Args:
        message: 要输出的消息
        level: 日志级别
    """
    logger = get_logger("console")
    log_func = getattr(logger, level.lower(), logger.info)
    
    # 移除emoji（Windows兼容性）
    if platform.system() == 'Windows':
        replacements = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '📝': '[TEXT]',
            '🔊': '[AUDIO]',
            '✨': '[*]',
            '⏱️': '[TIME]',
            '💡': '[INFO]',
            '📊': '[STATS]',
            '🔧': '[CONFIG]',
            '→': '->',
            '✓': '[v]',
            '✗': '[x]',
        }
        for emoji, replacement in replacements.items():
            message = message.replace(emoji, replacement)
    
    log_func(message)


# 为了兼容性，提供一个print替代
def safe_print(message: str, **kwargs):
    """替代print函数，使用logging输出"""
    convert_print_to_log(message)