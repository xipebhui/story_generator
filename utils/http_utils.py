#!/usr/bin/env python3
"""
HTTP工具类
"""

import requests
import json
import time
from typing import Optional
import logger

# 获取logger
log = logger.get_logger("http_utils")

def reuqset_export_video(draft_id: str, export_url: str) -> str:
    """
    请求导出视频
    
    Args:
        draft_id: 草稿ID
        export_url: 导出服务URL
        
    Returns:
        导出的视频文件路径
        
    Raises:
        Exception: 请求失败时抛出异常
    """
    log.info(f"Requesting video export for draft: {draft_id}")
    
    # 准备请求数据
    request_data = {
        "draft_id": draft_id,
        "export_format": "mp4",
        "quality": "high",
        "timestamp": int(time.time())
    }
    
    try:
        # 发送请求
        response = requests.post(
            export_url,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5分钟超时
        )
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            
            # 检查导出状态
            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    log.info(f"Video export successful: {video_path}")
                    return video_path
                else:
                    raise Exception("Export successful but no video path returned")
            else:
                error_msg = result.get("error", "Unknown error during export")
                raise Exception(f"Export failed: {error_msg}")
        else:
            raise Exception(f"HTTP error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("Export request timed out after 5 minutes")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Failed to connect to export service at {export_url}")
    except Exception as e:
        log.error(f"Export request failed: {str(e)}")
        raise