#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一视频获取Pipeline阶段
使用UnifiedVideoFetcher服务获取视频
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from services.unified_video_fetcher import UnifiedVideoFetcher

logger = logging.getLogger(__name__)


async def unified_video_fetch_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    统一视频获取阶段
    支持YouTube和抖音平台，根据创作者数量智能选择获取策略
    
    Args:
        context: 执行上下文，包含：
            - params: 执行参数
                - creator_list: 创作者ID列表
                - platform: 平台（youtube/douyin），默认youtube
                - account_id: 账号ID
                - fetch_config: 获取配置（可选）
                    - max_videos: 每个创作者获取的最大视频数
                    - days_back: 获取多少天内的视频（仅单创作者模式）
            - _context: Pipeline上下文对象（可选）
    
    Returns:
        执行结果字典：
            - success: 是否成功
            - data: 视频信息（如果成功）
            - error: 错误信息（如果失败）
    """
    stage_name = 'unified_video_fetch'
    
    try:
        # 获取参数
        params = context.get('params', {})
        creator_list = params.get('creator_list', [])
        platform = params.get('platform', 'youtube')
        account_id = params.get('account_id')
        fetch_config = params.get('fetch_config', {})
        
        # 参数验证
        if not creator_list:
            return {
                'success': False,
                'error': 'creator_list is required'
            }
        
        if not account_id:
            return {
                'success': False,
                'error': 'account_id is required'
            }
        
        logger.info(f"[{stage_name}] Starting unified fetch for {len(creator_list)} creators on {platform}")
        logger.info(f"[{stage_name}] Creators: {creator_list}")
        
        # 根据平台设置API配置
        if platform == "douyin":
            # 抖音配置
            douyin_api_url = fetch_config.get('douyin_api_url', 'http://localhost:51084')
            fetcher = UnifiedVideoFetcher(douyin_api_url=douyin_api_url)
        else:
            # YouTube配置
            youtube_api_key = fetch_config.get('youtube_api_key')
            fetcher = UnifiedVideoFetcher(youtube_api_key=youtube_api_key)
        
        # 获取视频
        video = await fetcher.fetch_and_get_latest_video(
            creator_list=creator_list,
            platform=platform,
            config=fetch_config
        )
        
        if video:
            logger.info(f"[{stage_name}] Found video: {video['video_id']} from {video['creator_id']}")
            
            # 更新context的params，供后续阶段使用
            if '_context' in context:
                pipeline_context = context['_context']
                pipeline_context.params['video_id'] = video['video_id']
                pipeline_context.params['creator_id'] = video['creator_id']
                pipeline_context.params['platform'] = video['platform']
                
                # 保存视频信息到输出
                pipeline_context.set_stage_output(stage_name, video)
            
            # 返回成功结果
            return {
                'success': True,
                'data': {
                    'video_id': video['video_id'],
                    'creator_id': video['creator_id'],
                    'platform': video['platform'],
                    'video_url': video.get('video_url'),
                    'cover_url': video.get('cover_url'),
                    'title': video.get('title'),
                    'description': video.get('description'),
                    'published_at': video.get('published_at'),
                    'from_database': video.get('from_database', False)
                }
            }
        else:
            logger.info(f"[{stage_name}] No unprocessed videos found")
            return {
                'success': False,
                'error': 'No unprocessed videos found for the given creators'
            }
            
    except Exception as e:
        logger.error(f"[{stage_name}] Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def mark_video_status_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    标记视频处理状态阶段
    在Pipeline完成后标记视频为已完成或失败
    
    Args:
        context: 执行上下文，包含：
            - params: 执行参数
                - platform: 平台
                - creator_id: 创作者ID
                - video_id: 视频ID
                - status: 状态（completed/failed）
                - error_msg: 错误信息（当status=failed时）
    
    Returns:
        执行结果字典
    """
    stage_name = 'mark_video_status'
    
    try:
        params = context.get('params', {})
        platform = params.get('platform')
        creator_id = params.get('creator_id')
        video_id = params.get('video_id')
        status = params.get('status', 'completed')
        error_msg = params.get('error_msg', '')
        
        # 参数验证
        if not all([platform, creator_id, video_id]):
            return {
                'success': False,
                'error': 'platform, creator_id and video_id are required'
            }
        
        logger.info(f"[{stage_name}] Marking video {video_id} as {status}")
        
        # 创建fetcher实例
        fetcher = UnifiedVideoFetcher()
        
        # 根据状态标记视频
        if status == 'completed':
            await fetcher.mark_video_completed(platform, creator_id, video_id)
        elif status == 'failed':
            await fetcher.mark_video_failed(platform, creator_id, video_id, error_msg)
        else:
            return {
                'success': False,
                'error': f'Invalid status: {status}'
            }
        
        return {
            'success': True,
            'data': {
                'video_id': video_id,
                'status': status
            }
        }
        
    except Exception as e:
        logger.error(f"[{stage_name}] Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }