#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册抖音下载发布Pipeline
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_registry import register_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_douyin_download_publish_pipeline():
    """注册抖音下载发布Pipeline"""
    
    # Pipeline配置模式定义（初始化时的固定配置）
    config_schema = {
        "api_base_url": "string",            # 抖音API基础URL
        "max_videos_per_creator": "integer", # 默认每个创作者获取的视频数
        "download_timeout": "integer",       # 下载超时时间（秒）
        "storage_base_path": "string",       # 视频存储路径
        "cache_dir": "string"                # 缓存目录（用于去重）
    }
    
    # 注册Pipeline
    success = register_pipeline(
        pipeline_id="douyin_download_publish",
        pipeline_name="抖音视频下载发布Pipeline",
        pipeline_type="media_processing",
        pipeline_class="pipelines.douyin_download_publish_pipeline.DouyinDownloadPublishPipeline",
        config_schema=config_schema,
        supported_platforms=["youtube"],  # 发布到YouTube
        version="1.0.0",
        metadata={
            "description": "从抖音创作者ID列表获取视频，下载最新视频及封面，然后发布到YouTube",
            "author": "system",
            "stages": ["fetch_creator_videos", "download_media", "publish_to_youtube"],
            "required_params": ["creator_ids", "account_id"],  # 执行时必需的参数
            "optional_params": ["max_videos_per_creator"],     # 执行时可选的参数
            "features": [
                "批量获取创作者视频",
                "自动去重，避免重复处理",
                "自动下载视频和封面",
                "默认去水印下载",
                "集成YouTube发布服务",
                "发布成功后创建缓存标记"
            ],
            "default_config": {
                "api_base_url": "http://localhost:51084",
                "max_videos_per_creator": 1,
                "download_timeout": 300,
                "storage_base_path": "douyin_videos",
                "cache_dir": "douyin_cache"
            }
        }
    )
    
    if success:
        logger.info("✅ 成功注册抖音下载发布Pipeline")
    else:
        logger.error("❌ 注册抖音下载发布Pipeline失败")
    
    return success


if __name__ == "__main__":
    # 执行注册
    result = register_douyin_download_publish_pipeline()
    sys.exit(0 if result else 1)