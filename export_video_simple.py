#!/usr/bin/env python3
"""
简化的视频导出模块
只负责调用剪映导出API
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def export_video(draft_name: str, export_url: Optional[str] = None) -> Optional[str]:
    """
    导出剪映草稿为视频
    
    Args:
        draft_name: 草稿文件夹名称
        export_url: 导出服务URL，如果不提供则从环境变量读取
        
    Returns:
        成功返回视频文件路径，失败返回None
    """
    # 获取导出服务URL
    if not export_url:
        export_url = os.getenv("EXPORT_VIDEO_URL", "http://localhost:51053")
    
    # 构建完整的API地址
    api_endpoint = f"{export_url}/api/export_draft"
    
    # 准备请求数据
    request_data = {
        "draft_name": draft_name
    }
    
    try:
        logger.info(f"正在导出草稿: {draft_name}")
        logger.info("注意：视频导出可能需要较长时间（最长30分钟），请耐心等待...")
        logger.debug(f"API地址: {api_endpoint}")
        
        # 发送请求
        response = requests.post(
            api_endpoint,
            json=request_data,
            timeout=3600  # 30分钟超时
        )
        
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                output_path = result.get("output_path")
                logger.info(f"视频导出成功: {output_path}")
                return output_path
            else:
                logger.error(f"导出失败: {result}")
                return None
        else:
            # 错误响应
            error_detail = response.json().get("detail", "Unknown error")
            logger.error(f"导出API返回错误: {error_detail}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("导出请求超时（30分钟）")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到导出服务: {api_endpoint}")
        return None
    except Exception as e:
        logger.error(f"导出过程中发生错误: {e}")
        return None


def test_export_service(export_url: Optional[str] = None) -> bool:
    """
    测试导出服务是否可用
    
    Args:
        export_url: 导出服务URL
        
    Returns:
        服务可用返回True，否则返回False
    """
    if not export_url:
        export_url = os.getenv("EXPORT_VIDEO_URL", "http://localhost:51053")
    
    test_endpoint = f"{export_url}/api/test"
    
    try:
        response = requests.get(test_endpoint, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                logger.info("导出服务测试成功")
                return True
    except Exception as e:
        logger.error(f"导出服务测试失败: {e}")
    
    return False


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python export_video_simple.py <draft_name>")
        sys.exit(1)
    
    draft_name = sys.argv[1]
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 测试服务
    if test_export_service():
        # 导出视频
        video_path = export_video(draft_name)
        if video_path:
            print(f"[OK] 视频导出成功: {video_path}")
        else:
            print(f"[ERROR] 视频导出失败")
            sys.exit(1)
    else:
        print("[ERROR] 导出服务不可用")
        sys.exit(1)