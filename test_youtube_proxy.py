#!/usr/bin/env python3
"""
简单的YouTube API代理测试脚本
测试通过SOCKS5代理获取视频详情
"""

import os
import json
import logging
from dotenv import load_dotenv
from googleapiclient.discovery import build
import httplib2
import socks

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_youtube_with_proxy():
    """测试通过SOCKS5代理访问YouTube API"""
    
    # 加载环境变量
    load_dotenv()
    
    # 获取配置
    api_key = os.getenv("YOUTUBE_API_KEY")
    proxy_host = os.getenv("PROXY_HOST", "192.168.50.88")
    proxy_port = int(os.getenv("PROXY_PORT", "7897"))
    proxy_username = os.getenv("PROXY_USERNAME", "")
    proxy_password = os.getenv("PROXY_PASSWORD", "")
    
    logger.info(f"配置信息:")
    logger.info(f"  API Key: {api_key[:10]}..." if api_key else "  API Key: 未设置")
    logger.info(f"  代理地址: {proxy_host}:{proxy_port}")
    logger.info(f"  代理认证: {'是' if proxy_username else '否'}")
    
    # 测试视频ID
    test_video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    try:
        # 配置SOCKS5代理
        logger.info(f"\n正在配置SOCKS5代理...")
        
        if proxy_username and proxy_password:
            # 带认证的SOCKS5代理
            proxy_info = httplib2.ProxyInfo(
                proxy_type=socks.SOCKS5,
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                proxy_user=proxy_username,
                proxy_pass=proxy_password
            )
            logger.info(f"✅ 已配置带认证的SOCKS5代理")
        else:
            # 不带认证的SOCKS5代理
            proxy_info = httplib2.ProxyInfo(
                proxy_type=socks.SOCKS5,
                proxy_host=proxy_host,
                proxy_port=proxy_port
            )
            logger.info(f"✅ 已配置无认证的SOCKS5代理")
        
        # 创建HTTP客户端
        http = httplib2.Http(proxy_info=proxy_info)
        
        # 构建YouTube服务
        logger.info(f"\n正在连接YouTube API...")
        youtube = build(
            'youtube', 
            'v3',
            developerKey=api_key,
            http=http,
            static_discovery=False  # 避免缓存问题
        )
        
        # 请求视频详情
        logger.info(f"\n正在获取视频详情: {test_video_id}")
        request = youtube.videos().list(
            part="snippet,statistics",
            id=test_video_id
        )
        
        response = request.execute()
        
        # 解析结果
        if response and 'items' in response and len(response['items']) > 0:
            video = response['items'][0]
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            
            logger.info(f"\n✅ 成功获取视频信息!")
            logger.info(f"  标题: {snippet.get('title', 'N/A')}")
            logger.info(f"  频道: {snippet.get('channelTitle', 'N/A')}")
            logger.info(f"  发布时间: {snippet.get('publishedAt', 'N/A')}")
            logger.info(f"  观看次数: {statistics.get('viewCount', 'N/A')}")
            logger.info(f"  点赞数: {statistics.get('likeCount', 'N/A')}")
            
            # 保存完整响应
            with open('youtube_test_response.json', 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            logger.info(f"\n完整响应已保存到: youtube_test_response.json")
            
            return True
        else:
            logger.error(f"❌ 未找到视频信息")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ 请求失败!")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误信息: {str(e)}")
        
        import traceback
        logger.debug("详细错误:")
        logger.debug(traceback.format_exc())
        
        return False

def test_simple_http_proxy():
    """测试使用简单的HTTP代理（备选方案）"""
    import requests
    
    logger.info("\n" + "="*60)
    logger.info("测试HTTP代理方案（使用requests库）")
    logger.info("="*60)
    
    load_dotenv()
    
    api_key = os.getenv("YOUTUBE_API_KEY")
    proxy_host = os.getenv("PROXY_HOST", "192.168.50.88")
    proxy_port = os.getenv("PROXY_PORT", "7897")
    
    # 配置代理
    proxies = {
        'http': f'socks5://{proxy_host}:{proxy_port}',
        'https': f'socks5://{proxy_host}:{proxy_port}'
    }
    
    # YouTube API URL
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        'part': 'snippet,statistics',
        'id': 'dQw4w9WgXcQ',
        'key': api_key
    }
    
    try:
        logger.info(f"使用代理: socks5://{proxy_host}:{proxy_port}")
        logger.info(f"请求URL: {url}")
        
        response = requests.get(url, params=params, proxies=proxies, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                video = data['items'][0]
                logger.info(f"\n✅ 请求成功!")
                logger.info(f"  视频标题: {video['snippet']['title']}")
                return True
        else:
            logger.error(f"❌ 请求失败: HTTP {response.status_code}")
            logger.error(f"响应: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 请求异常: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("YouTube API SOCKS5代理测试")
    print("="*60)
    
    # 测试主方案
    success = test_youtube_with_proxy()
    
    if not success:
        print("\n尝试备选方案...")
        # 测试备选方案
        test_simple_http_proxy()
    
    print("\n测试完成!")