#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows编码处理工具模块
提供统一的Windows控制台编码修复方案
"""

import os
import sys
import platform
import logging


def setup_windows_console_encoding():
    """
    设置Windows控制台编码为UTF-8
    注意：不再修改sys.stdout/stderr，由logging模块处理编码
    """
    if platform.system() != 'Windows':
        return
    
    try:
        # 设置控制台代码页为UTF-8 (65001)
        os.system('chcp 65001 > nul 2>&1')
        
        # 设置Python的IO编码环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'
        
    except Exception as e:
        # 如果设置失败，至少尝试设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'


def configure_logging_for_windows(logger_instance=None):
    """
    配置日志处理器以支持Windows UTF-8输出
    注意：现在主要通过FileHandler的encoding参数处理
    
    Args:
        logger_instance: 要配置的logger实例，如果为None则配置root logger
    """
    if platform.system() != 'Windows':
        return
    
    # 设置环境变量，确保Python使用UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'


def get_subprocess_encoding_env():
    """
    获取用于subprocess的环境变量，确保子进程使用UTF-8编码
    
    Returns:
        dict: 包含正确编码设置的环境变量字典
    """
    env = os.environ.copy()
    
    if platform.system() == 'Windows':
        # 设置Python子进程使用UTF-8编码
        env['PYTHONIOENCODING'] = 'utf-8'
        # 设置系统默认编码
        env['PYTHONUTF8'] = '1'
        # 设置语言环境
        env['LANG'] = 'en_US.UTF-8'
    
    return env


def safe_print(message: str, file=None):
    """
    安全打印函数，处理Windows环境下的编码问题和特殊字符
    
    Args:
        message: 要打印的消息
        file: 输出文件对象（默认为stdout）
    """
    if file is None:
        file = sys.stdout
    
    # Windows环境特殊处理
    if platform.system() == 'Windows':
        # 替换常见的emoji和特殊字符
        replacements = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '📝': '[TEXT]',
            '🔊': '[AUDIO]',
            '🎵': '[MUSIC]',
            '✨': '[*]',
            '⏱️': '[TIME]',
            '💡': '[INFO]',
            '📊': '[STATS]',
            '🔧': '[CONFIG]',
            '→': '->',
            '←': '<-',
            '↑': '^',
            '↓': 'v',
            '✓': '[v]',
            '✗': '[x]',
            '•': '*',
            '▶': '>',
            '◀': '<',
            '▲': '^',
            '▼': 'v',
            '★': '[STAR]',
            '☆': '[star]',
            '█': '#',
            '▄': '=',
            '▀': '=',
            '│': '|',
            '─': '-',
            '┌': '+',
            '┐': '+',
            '└': '+',
            '┘': '+',
            '├': '+',
            '┤': '+',
            '┬': '+',
            '┴': '+',
            '┼': '+',
        }
        
        for char, replacement in replacements.items():
            message = message.replace(char, replacement)
    
    # 尝试打印
    try:
        print(message, file=file)
    except UnicodeEncodeError:
        # 如果还是失败，移除所有非ASCII字符
        message_ascii = message.encode('ascii', 'replace').decode('ascii')
        print(message_ascii, file=file)


# 不再自动修改sys.stdout/stderr，由logging模块处理