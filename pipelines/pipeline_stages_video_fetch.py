#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频获取预处理阶段
用于在Pipeline开始前获取最新未处理的视频
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def fetch_latest_video_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取最新未处理的视频阶段
    
    按照优先级从creator_list中获取最新未处理的视频
    
    Args:
        context: Pipeline上下文
        config: 阶段配置，可包含:
            - days_back: 获取多少天内的视频（默认7天）
            - max_videos: 最多检查多少个视频（默认10）
    
    Returns:
        dict: 包含video_id和其他视频信息
    """
    logger.info("[FETCH_VIDEO] ======= fetch_latest_video_stage START =======")
    logger.info(f"[FETCH_VIDEO] Received context type: {type(context)}")
    logger.info(f"[FETCH_VIDEO] Received config: {config}")
    
    from pipelines.pipeline_context import PipelineContext
    
    # 获取PipelineContext实例
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        # 导入YouTube客户端
        from youtube_client import YouTubeAPIClient
        
        # 获取必需的creator_list（必选参数）
        creator_list = params.get('creator_list')
        logger.info(f"[FETCH_VIDEO] Extracted creator_list from params: {creator_list}")
        
        if not creator_list:
            raise ValueError("creator_list is required")
        
        if not isinstance(creator_list, list) or len(creator_list) == 0:
            raise ValueError("creator_list must be a non-empty list")
        
        # 配置参数
        days_back = config.get('days_back', 7)
        max_videos = config.get('max_videos', 10)
        published_after = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # 创建YouTube客户端
        client = YouTubeAPIClient()
        
        # 收集所有创作者的所有未处理视频
        all_unprocessed_videos = []
        
        # 遍历创作者列表收集所有未处理的视频
        for current_creator_id in creator_list:
            logger.info(f"Checking creator: {current_creator_id}")
            
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
            
            # 检查每个视频是否已处理，收集未处理的
            for video in latest_videos:
                video_id = video.get('video_id')
                if not video_id:
                    continue
                
                # 检查缓存是否存在
                if not _is_video_processed(ctx, video_id, current_creator_id):
                    logger.info(f"[FETCH_VIDEO] Found unprocessed video: {video_id} for creator: {current_creator_id}")
                    
                    # 将视频信息添加到列表中
                    all_unprocessed_videos.append({
                        'video_id': video_id,
                        'creator_id': current_creator_id,
                        'channel_id': channel_id,
                        'channel_title': channel_title,
                        'video_info': video,
                        'published_at': video.get('published_at', ''),
                        'title': video.get('title', ''),
                        'creator_priority': creator_list.index(current_creator_id) + 1
                    })
                else:
                    logger.info(f"Video already processed: {video_id}")
        
        # 如果找到了未处理的视频，按发布时间排序，选择最新的
        if all_unprocessed_videos:
            logger.info(f"[FETCH_VIDEO] Found {len(all_unprocessed_videos)} unprocessed videos across all creators")
            
            # 按发布时间降序排序（最新的在前）
            all_unprocessed_videos.sort(key=lambda x: x['published_at'], reverse=True)
            
            # 选择最新的视频
            newest_video = all_unprocessed_videos[0]
            logger.info(f"[FETCH_VIDEO] Selected newest video: {newest_video['video_id']} from {newest_video['creator_id']} (published: {newest_video['published_at']})")
            
            # 更新params - 设置找到的creator_id和video_id
            params['video_id'] = newest_video['video_id']
            params['creator_id'] = newest_video['creator_id']  # 设置creator_id供后续阶段使用
            params['selected_creator_id'] = newest_video['creator_id']  # 记录实际使用的creator
            params['channel_id'] = newest_video['channel_id']
            params['channel_title'] = newest_video['channel_title']
            params['video_title'] = newest_video['title']
            params['video_published_at'] = newest_video['published_at']
            
            # 如果有context对象，也更新它的params（确保同步）
            if ctx and hasattr(ctx, 'params'):
                ctx.params['video_id'] = newest_video['video_id']
                ctx.params['creator_id'] = newest_video['creator_id']  # 设置creator_id供后续阶段使用
                ctx.params['selected_creator_id'] = newest_video['creator_id']
                ctx.params['channel_id'] = newest_video['channel_id']
                ctx.params['channel_title'] = newest_video['channel_title']
                ctx.params['video_title'] = newest_video['title']
                ctx.params['video_published_at'] = newest_video['published_at']
                logger.info(f"[FETCH_VIDEO] Updated context.params with video_id={newest_video['video_id']}, creator_id={newest_video['creator_id']}")
            
            logger.info(f"[FETCH_VIDEO] ======= fetch_latest_video_stage SUCCESS =======")
            result = {
                'success': True,
                'data': {
                    'video_id': newest_video['video_id'],
                    'selected_creator_id': newest_video['creator_id'],  # 实际使用的creator
                    'channel_id': newest_video['channel_id'],
                    'channel_title': newest_video['channel_title'],
                    'video_info': newest_video['video_info'],
                    'creator_priority': newest_video['creator_priority'],  # 优先级位置
                    'total_unprocessed': len(all_unprocessed_videos)  # 总共找到的未处理视频数
                }
            }
            logger.info(f"[FETCH_VIDEO] Returning: {result}")
            return result
        
        # 如果没找到未处理的视频
        error_msg = f"No unprocessed videos found for creators: {creator_list}"
        logger.error(f"[FETCH_VIDEO] {error_msg}")
        logger.error(f"[FETCH_VIDEO] ======= fetch_latest_video_stage FAILED =======")
        return {
            'success': False,
            'error': error_msg
        }
        
    except Exception as e:
        logger.error(f"[FETCH_VIDEO] Failed to fetch latest video: {e}")
        logger.error(f"[FETCH_VIDEO] ======= fetch_latest_video_stage ERROR =======")
        return {
            'success': False,
            'error': str(e)
        }


async def _get_channel_details(client, creator_id: str) -> Optional[Tuple[str, str]]:
    """
    获取频道详情
    
    Args:
        client: YouTube API客户端
        creator_id: 创作者ID（可能是channel_id或handle）
    
    Returns:
        tuple: (channel_id, channel_title) 或 None
    """
    try:
        # 尝试作为channel_id获取
        if creator_id.startswith('UC'):
            result = client.get_channel_details(channel_ids=[creator_id])
        else:
            # 尝试作为handle获取（如@username）
            result = client.get_channel_details(handles=[creator_id])
        
        if result and result.get('items'):
            channel = result['items'][0]
            channel_id = channel['id']
            channel_title = channel['snippet']['title']
            return channel_id, channel_title
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get channel details: {e}")
        return None


async def _get_latest_videos(
    client, channel_id: str, published_after: datetime, max_videos: int = 10
) -> List[Dict[str, Any]]:
    """
    获取频道最新的视频
    
    Args:
        client: YouTube API客户端
        channel_id: 频道ID
        published_after: 获取此时间之后的视频
        max_videos: 最多获取的视频数
    
    Returns:
        list: 视频信息列表
    """
    try:
        # 使用activities API获取最新活动
        result = client.get_channel_activity(
            channel_id=channel_id,
            published_after=published_after
        )
        
        if not result or not result.get('items'):
            logger.warning(f"No activities found for channel: {channel_id}")
            return []
        
        videos = []
        video_ids = []
        
        # 从活动中提取视频ID
        for activity in result.get('items', []):
            if activity['snippet']['type'] == 'upload':
                video_id = activity['contentDetails']['upload']['videoId']
                video_ids.append(video_id)
                
                videos.append({
                    'video_id': video_id,
                    'title': activity['snippet']['title'],
                    'published_at': activity['snippet']['publishedAt']
                })
                
                if len(videos) >= max_videos:
                    break
        
        # 如果需要，获取更详细的视频信息
        if video_ids:
            video_details = client.get_video_details(video_ids)
            if video_details and video_details.get('items'):
                # 合并详细信息
                details_map = {item['id']: item for item in video_details['items']}
                for video in videos:
                    if video['video_id'] in details_map:
                        detail = details_map[video['video_id']]
                        video.update({
                            'view_count': int(detail.get('statistics', {}).get('viewCount', 0)),
                            'duration': detail['contentDetails'].get('duration'),
                            'description': detail['snippet'].get('description', '')
                        })
        
        return videos
        
    except Exception as e:
        logger.error(f"Failed to get latest videos: {e}")
        return []


def _is_video_processed(ctx, video_id: str, creator_id: str) -> bool:
    """
    检查视频是否已处理（通过缓存文件判断）
    
    Args:
        ctx: PipelineContext
        video_id: 视频ID
        creator_id: 创作者ID
    
    Returns:
        bool: 是否已处理
    """
    try:
        # 构建缓存目录路径
        cache_base = Path("output")  # 或从配置获取
        
        # 检查多个可能的缓存位置
        possible_paths = [
            # 新的缓存结构
            cache_base / f"{creator_id}_{video_id}",
            cache_base / creator_id / video_id,
            # 故事文件
            Path("story_result") / creator_id / video_id / "final" / "story.txt",
            # 音频文件（任何账号）
            cache_base / f"{creator_id}_*_{video_id}_story.mp3",
            # 草稿文件（任何账号）
            cache_base / "drafts" / f"{creator_id}_*_{video_id}_story",
            # 视频文件
            cache_base / "videos" / f"{creator_id}_{video_id}.mp4"
        ]
        
        for path in possible_paths:
            if "*" in str(path):
                # 处理通配符路径
                parent = path.parent
                pattern = path.name
                if parent.exists():
                    matches = list(parent.glob(pattern))
                    if matches:
                        logger.debug(f"Found processed cache: {matches[0]}")
                        return True
            elif path.exists():
                logger.debug(f"Found processed cache: {path}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking cache: {e}")
        return False


# 导出阶段函数
__all__ = ['fetch_latest_video_stage']