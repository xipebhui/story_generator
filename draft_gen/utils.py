#!/usr/bin/env python3
"""
工具函数模块 - 处理跨平台兼容性
"""

import sys
import platform


def safe_print(message: str, file=None):
    """
    安全打印函数，处理 Windows 环境下的编码问题
    
    Args:
        message: 要打印的消息
        file: 输出文件对象（默认为 stdout）
    """
    if file is None:
        file = sys.stdout
    
    # Windows 环境特殊处理
    if platform.system() == 'Windows':
        # 替换常见的 emoji 字符
        replacements = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            'ℹ️': '[INFO]',
            '📊': '[STATS]',
            '🎬': '[VIDEO]',
            '🎵': '[AUDIO]',
            '📝': '[TEXT]',
            '→': '->',
            '✨': '[*]',
            '🔧': '[CONFIG]',
            '⭐': '[STAR]',
            '🚀': '[START]',
            '📋': '[LIST]',
            '📺': '[MEDIA]',
            '🔍': '[SEARCH]',
            '💡': '[IDEA]',
            '🎯': '[TARGET]',
            '📦': '[PACKAGE]',
            '🔄': '[SYNC]',
            '✓': '[v]',
            '✗': '[x]',
            '•': '*',
            '◆': '*',
            '▶': '>',
            '◀': '<',
        }
        
        for emoji, replacement in replacements.items():
            message = message.replace(emoji, replacement)
    
    # 尝试打印
    try:
        print(message, file=file)
    except UnicodeEncodeError:
        # 如果还是失败，使用 ascii 编码
        message_ascii = message.encode('ascii', 'replace').decode('ascii')
        print(message_ascii, file=file)


def setup_console_encoding():
    """
    设置控制台编码为 UTF-8（仅 Windows）
    """
    if platform.system() == 'Windows':
        import os
        # 设置控制台代码页为 UTF-8
        os.system('chcp 65001 > nul 2>&1')
        
        # 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # 尝试重新配置 stdout 和 stderr
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass