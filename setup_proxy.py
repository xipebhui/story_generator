#!/usr/bin/env python3
"""
设置全局代理环境变量
在导入其他模块之前运行这个
"""

import os
import socket
import socks
from dotenv import load_dotenv

def setup_global_proxy():
    """设置全局SOCKS5代理"""
    
    # 加载环境变量
    load_dotenv()
    
    proxy_host = os.getenv("PROXY_HOST", "192.168.50.88")
    proxy_port = int(os.getenv("PROXY_PORT", "7897"))
    proxy_username = os.getenv("PROXY_USERNAME", "")
    proxy_password = os.getenv("PROXY_PASSWORD", "")
    
    print(f"设置全局SOCKS5代理: {proxy_host}:{proxy_port}")
    
    # 设置环境变量（给其他库使用）
    proxy_url = f"socks5://{proxy_host}:{proxy_port}"
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url
    
    # 使用 PySocks 设置默认socket
    if proxy_username and proxy_password:
        socks.set_default_proxy(
            socks.SOCKS5, 
            proxy_host, 
            proxy_port,
            username=proxy_username,
            password=proxy_password
        )
    else:
        socks.set_default_proxy(
            socks.SOCKS5, 
            proxy_host, 
            proxy_port
        )
    
    # 替换默认的socket
    socket.socket = socks.socksocket
    
    print(f"✅ 全局SOCKS5代理已设置")
    
    return proxy_host, proxy_port

if __name__ == "__main__":
    setup_global_proxy()