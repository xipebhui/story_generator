#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频获取预处理阶段（数据库版本）
使用数据库跟踪视频处理状态，支持失败重试
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def fetch_latest_video_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取最新未处理的视频阶段（使用数据库）
    
    按照发布时间从所有creator中获取最新未处理的视频
    支持失败重试和状态跟踪
    
    Args:
        context: Pipeline上下文
        config: 阶段配置，可包含:
            - days_back: 获取多少天内的视频（默认7天）
            - max_videos: 最多检查多少个视频（默认10）
            - use_database: 是否使用数据库（默认True）
    
    Returns:
        dict: 包含video_id和其他视频信息
    """
    logger.info("[FETCH_VIDEO_DB] ======= fetch_latest_video_stage (DB) START =======")
    logger.info(f"[FETCH_VIDEO_DB] Received context type: {type(context)}")
    logger.info(f"[FETCH_VIDEO_DB] Received config: {config}")
    
    from pipelines.pipeline_context import PipelineContext
    
    # 获取PipelineContext实例
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        # 导入必要的模块
        from youtube_client import YouTubeAPIClient
        from services.video_processing_service import VideoProcessingService
        from models.video_processing import Platform, ProcessingStage
        from database import get_db_url
        
        # 获取必需的creator_list（必选参数）
        creator_list = params.get('creator_list')
        logger.info(f"[FETCH_VIDEO_DB] Extracted creator_list from params: {creator_list}")
        
        if not creator_list:
            raise ValueError("creator_list is required")
        
        if not isinstance(creator_list, list) or len(creator_list) == 0:
            raise ValueError("creator_list must be a non-empty list")
        
        # 配置参数
        days_back = config.get('days_back', 7)
        max_videos = config.get('max_videos', 10)
        use_database = config.get('use_database', True)
        published_after = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # 创建YouTube客户端
        client = YouTubeAPIClient()
        
        # 如果启用数据库
        if use_database:
            # 创建数据库连接
            engine = create_engine(get_db_url())
            Session = sessionmaker(bind=engine)
            db_session = Session()
            
            try:
                service = VideoProcessingService(db_session)
                
                # 首先从数据库获取未处理的视频
                logger.info("[FETCH_VIDEO_DB] Checking database for unprocessed videos...")
                unprocessed_video = service.get_latest_unprocessed_video(
                    platform='youtube',
                    creator_list=creator_list
                )
                
                if unprocessed_video:
                    logger.info(f"[FETCH_VIDEO_DB] Found unprocessed video in DB: {unprocessed_video.video_id}")
                    
                    # 更新params
                    params['video_id'] = unprocessed_video.video_id
                    params['creator_id'] = unprocessed_video.creator_id
                    params['selected_creator_id'] = unprocessed_video.creator_id
                    params['channel_id'] = unprocessed_video.channel_id
                    params['channel_title'] = unprocessed_video.channel_title
                    params['video_title'] = unprocessed_video.video_title
                    params['video_published_at'] = unprocessed_video.published_at.isoformat() if unprocessed_video.published_at else ''
                    
                    # 同步到context
                    if ctx and hasattr(ctx, 'params'):
                        ctx.params.update(params)
                    
                    logger.info(f"[FETCH_VIDEO_DB] ======= fetch_latest_video_stage SUCCESS (from DB) =======")
                    return {
                        'success': True,
                        'data': {
                            'video_id': unprocessed_video.video_id,
                            'selected_creator_id': unprocessed_video.creator_id,
                            'channel_id': unprocessed_video.channel_id,
                            'channel_title': unprocessed_video.channel_title,
                            'video_info': unprocessed_video.to_dict(),
                            'from_database': True
                        }
                    }
                
                logger.info("[FETCH_VIDEO_DB] No unprocessed videos in DB, fetching from YouTube...")
                
                # 如果数据库中没有未处理的视频，从YouTube获取新视频
                all_videos = []
                
                for current_creator_id in creator_list:
                    logger.info(f"[FETCH_VIDEO_DB] Checking creator: {current_creator_id}")
                    
                    # 获取channel详情
                    channel_result = await _get_channel_details(client, current_creator_id)
                    if not channel_result:
                        logger.warning(f"Failed to get channel details for: {current_creator_id}")
                        continue
                    
                    channel_id, channel_title = channel_result
                    logger.info(f"Found channel: {channel_title} ({channel_id})")
                    
                    # 获取最新视频
                    latest_videos = await _get_latest_videos(
                        client, channel_id, published_after, max_videos
                    )
                    
                    if not latest_videos:
                        logger.warning(f"No recent videos found for channel: {channel_id}")
                        continue
                    
                    # 将视频信息保存到数据库
                    for video in latest_videos:
                        video_id = video.get('video_id')
                        if not video_id:
                            continue
                        
                        # 检查数据库中是否已存在
                        existing = service.get_video_status('youtube', current_creator_id, video_id)
                        if not existing:
                            # 创建新记录
                            video_status = service.create_or_update_video(
                                platform='youtube',
                                creator_id=current_creator_id,
                                video_id=video_id,
                                channel_id=channel_id,
                                channel_title=channel_title,
                                video_title=video.get('title', ''),
                                video_url=f"https://www.youtube.com/watch?v={video_id}",
                                published_at=video.get('published_at', ''),
                                processing_stage='fetched',
                                account_id=params.get('account_id')
                            )
                            logger.info(f"[FETCH_VIDEO_DB] Added new video to DB: {video_id}")
                            
                            # 添加到列表
                            all_videos.append({
                                'video_id': video_id,
                                'creator_id': current_creator_id,
                                'channel_id': channel_id,
                                'channel_title': channel_title,
                                'video_info': video,
                                'published_at': video.get('published_at', ''),
                                'title': video.get('title', '')
                            })
                        elif not existing.is_completed:
                            # 如果存在但未完成，也加入列表
                            all_videos.append({
                                'video_id': video_id,
                                'creator_id': current_creator_id,
                                'channel_id': channel_id,
                                'channel_title': channel_title,
                                'video_info': video,
                                'published_at': video.get('published_at', ''),
                                'title': video.get('title', '')
                            })
                
                if all_videos:
                    # 按发布时间排序，选择最新的
                    all_videos.sort(key=lambda x: x['published_at'], reverse=True)
                    newest_video = all_videos[0]
                    
                    logger.info(f"[FETCH_VIDEO_DB] Selected newest video: {newest_video['video_id']}")
                    
                    # 更新params
                    params['video_id'] = newest_video['video_id']
                    params['creator_id'] = newest_video['creator_id']
                    params['selected_creator_id'] = newest_video['creator_id']
                    params['channel_id'] = newest_video['channel_id']
                    params['channel_title'] = newest_video['channel_title']
                    params['video_title'] = newest_video['title']
                    params['video_published_at'] = newest_video['published_at']
                    
                    # 同步到context
                    if ctx and hasattr(ctx, 'params'):
                        ctx.params.update(params)
                    
                    logger.info(f"[FETCH_VIDEO_DB] ======= fetch_latest_video_stage SUCCESS =======")
                    return {
                        'success': True,
                        'data': {
                            'video_id': newest_video['video_id'],
                            'selected_creator_id': newest_video['creator_id'],
                            'channel_id': newest_video['channel_id'],
                            'channel_title': newest_video['channel_title'],
                            'video_info': newest_video['video_info'],
                            'from_database': False
                        }
                    }
                
            finally:
                db_session.close()
        
        else:
            # 不使用数据库，使用原有逻辑
            logger.info("[FETCH_VIDEO_DB] Database disabled, using file-based checking")
            from pipelines.pipeline_stages_video_fetch import fetch_latest_video_stage as original_fetch
            return await original_fetch(context, config)
        
        # 如果没找到未处理的视频
        error_msg = f"No unprocessed videos found for creators: {creator_list}"
        logger.error(f"[FETCH_VIDEO_DB] {error_msg}")
        logger.error(f"[FETCH_VIDEO_DB] ======= fetch_latest_video_stage FAILED =======")
        return {
            'success': False,
            'error': error_msg
        }
        
    except Exception as e:
        logger.error(f"[FETCH_VIDEO_DB] Failed to fetch latest video: {e}")
        logger.error(f"[FETCH_VIDEO_DB] ======= fetch_latest_video_stage ERROR =======")
        return {
            'success': False,
            'error': str(e)
        }


async def _get_channel_details(client, creator_id: str) -> Optional[Tuple[str, str]]:
    """获取频道详情（复用原有函数）"""
    from pipelines.pipeline_stages_video_fetch import _get_channel_details as original
    return await original(client, creator_id)


async def _get_latest_videos(
    client, channel_id: str, published_after: datetime, max_videos: int = 10
) -> List[Dict[str, Any]]:
    """获取频道最新的视频（复用原有函数）"""
    from pipelines.pipeline_stages_video_fetch import _get_latest_videos as original
    return await original(client, channel_id, published_after, max_videos)


# 导出阶段函数
__all__ = ['fetch_latest_video_stage']