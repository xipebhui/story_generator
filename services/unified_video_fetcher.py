#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一视频获取服务
根据创作者数量智能选择获取策略
"""

import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session

from services.video_source_service import VideoSourceService
from models.video_source import VideoSource
from services.youtube_service import YouTubeService
from database import get_db_manager

logger = logging.getLogger(__name__)


class UnifiedVideoFetcher:
    """
    统一的视频获取器
    支持YouTube和抖音平台的视频获取和管理
    """
    
    def __init__(
        self,
        douyin_api_url: str = "http://localhost:51084",
        youtube_api_key: Optional[str] = None
    ):
        """
        初始化视频获取器
        
        Args:
            douyin_api_url: 抖音API服务地址
            youtube_api_key: YouTube API密钥（可选）
        """
        self.douyin_api_url = douyin_api_url
        self.youtube_api_key = youtube_api_key
        
        # 初始化数据库连接
        db = get_db_manager()
        self.engine = db.engine
        self.Session = sessionmaker(bind=self.engine)
        
        # YouTube服务（如果有API密钥）
        if youtube_api_key:
            self.youtube_service = YouTubeService(api_key=youtube_api_key)
        else:
            self.youtube_service = None
    
    async def fetch_and_get_latest_video(
        self,
        creator_list: List[str],
        platform: str = "youtube",
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的未处理视频
        
        Args:
            creator_list: 创作者ID列表
            platform: 平台（youtube/douyin）
            config: 额外配置
        
        Returns:
            最新的未处理视频信息，如果没有则返回None
        """
        logger.info(f"[FETCH] Starting fetch for {len(creator_list)} creators on {platform}")
        
        # 创建数据库会话
        db_session = self.Session()
        video_service = VideoSourceService(db_session)
        
        try:
            # 根据创作者数量决定策略
            if len(creator_list) == 1:
                # 单创作者：深度获取历史视频
                logger.info(f"[FETCH] Single creator mode: fetching historical videos")
                await self._fetch_historical_videos(
                    video_service,
                    creator_list[0],
                    platform,
                    config
                )
            else:
                # 多创作者：快速获取最新视频
                logger.info(f"[FETCH] Multiple creators mode: fetching latest videos")
                await self._fetch_latest_videos(
                    video_service,
                    creator_list,
                    platform,
                    config
                )
            
            # 从数据库获取最新的未处理视频
            video = video_service.get_latest_unprocessed_video(
                creator_ids=creator_list,
                platform=platform
            )
            
            if video:
                # 标记为处理中
                video_service.mark_as_processing(video)
                
                # 返回视频信息
                result = {
                    'platform': video.platform,
                    'creator_id': video.creator_id,
                    'video_id': video.video_id,
                    'video_url': video.video_url,
                    'cover_url': video.cover_url,
                    'title': video.title,
                    'description': video.description,
                    'published_at': video.published_at.isoformat() if video.published_at else None,
                    'from_database': True
                }
                
                logger.info(f"[FETCH] Found unprocessed video: {video.video_id}")
                return result
            else:
                logger.info(f"[FETCH] No unprocessed videos found")
                return None
                
        finally:
            db_session.close()
    
    async def _fetch_historical_videos(
        self,
        video_service: VideoSourceService,
        creator_id: str,
        platform: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        深度获取单个创作者的历史视频
        
        Args:
            video_service: 视频服务
            creator_id: 创作者ID
            platform: 平台
            config: 配置
        """
        if platform == "youtube":
            await self._fetch_youtube_historical(video_service, creator_id, config)
        elif platform == "douyin":
            await self._fetch_douyin_historical(video_service, creator_id, config)
    
    async def _fetch_latest_videos(
        self,
        video_service: VideoSourceService,
        creator_list: List[str],
        platform: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        快速获取多个创作者的最新视频
        
        Args:
            video_service: 视频服务
            creator_list: 创作者列表
            platform: 平台
            config: 配置
        """
        for creator_id in creator_list:
            if platform == "youtube":
                await self._fetch_youtube_latest(video_service, creator_id, config)
            elif platform == "douyin":
                await self._fetch_douyin_latest(video_service, creator_id, config)
    
    async def _fetch_youtube_historical(
        self,
        video_service: VideoSourceService,
        creator_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        获取YouTube创作者的历史视频（深度模式）
        """
        if not self.youtube_service:
            logger.warning("YouTube service not available (no API key)")
            return
        
        max_videos = config.get('max_videos', 50) if config else 50
        days_back = config.get('days_back', 30) if config else 30
        
        logger.info(f"[YOUTUBE] Fetching up to {max_videos} videos from {creator_id} (last {days_back} days)")
        
        # 使用YouTube API获取视频列表
        videos = await self.youtube_service.get_channel_videos(
            channel_id=creator_id,
            max_results=max_videos,
            days_back=days_back
        )
        
        # 保存到数据库
        for video_data in videos:
            try:
                video_service.add_video(
                    platform='youtube',
                    creator_id=creator_id,
                    video_id=video_data['video_id'],
                    published_at=video_data['published_at'],
                    title=video_data.get('title'),
                    description=video_data.get('description'),
                    metadata=video_data
                )
            except Exception as e:
                logger.error(f"Failed to add YouTube video {video_data['video_id']}: {e}")
    
    async def _fetch_youtube_latest(
        self,
        video_service: VideoSourceService,
        creator_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        获取YouTube创作者的最新视频（快速模式）
        """
        if not self.youtube_service:
            logger.warning("YouTube service not available (no API key)")
            return
        
        max_videos = config.get('max_videos', 5) if config else 5
        
        logger.info(f"[YOUTUBE] Fetching latest {max_videos} videos from {creator_id}")
        
        # 使用YouTube API获取最新视频
        videos = await self.youtube_service.get_channel_videos(
            channel_id=creator_id,
            max_results=max_videos
        )
        
        # 保存到数据库
        for video_data in videos:
            try:
                video_service.add_video(
                    platform='youtube',
                    creator_id=creator_id,
                    video_id=video_data['video_id'],
                    published_at=video_data['published_at'],
                    title=video_data.get('title'),
                    description=video_data.get('description'),
                    metadata=video_data
                )
            except Exception as e:
                logger.error(f"Failed to add YouTube video {video_data['video_id']}: {e}")
    
    async def _fetch_douyin_historical(
        self,
        video_service: VideoSourceService,
        creator_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        获取抖音创作者的历史视频（深度模式）
        """
        max_videos = config.get('max_videos', 50) if config else 50
        
        logger.info(f"[DOUYIN] Fetching up to {max_videos} videos from {creator_id}")
        
        async with aiohttp.ClientSession() as session:
            try:
                # 调用抖音API获取视频列表
                url = f"{self.douyin_api_url}/api/douyin/web/fetch_user_post_videos"
                params = {
                    'sec_user_id': creator_id,
                    'max_cursor': 0,
                    'count': max_videos
                }
                
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch Douyin videos: {response.status}")
                        return
                    
                    data = await response.json()
                    aweme_list = data.get('data', {}).get('aweme_list', [])
                    
                    logger.info(f"[DOUYIN] Found {len(aweme_list)} videos")
                    
                    # 保存到数据库
                    for video in aweme_list:
                        try:
                            video_info = self._extract_douyin_video_info(video)
                            if video_info:
                                video_service.add_video(
                                    platform='douyin',
                                    creator_id=creator_id,
                                    **video_info
                                )
                        except Exception as e:
                            logger.error(f"Failed to add Douyin video: {e}")
                            
            except Exception as e:
                logger.error(f"Error fetching Douyin videos for {creator_id}: {e}")
    
    async def _fetch_douyin_latest(
        self,
        video_service: VideoSourceService,
        creator_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        获取抖音创作者的最新视频（快速模式）
        """
        max_videos = config.get('max_videos', 5) if config else 5
        
        logger.info(f"[DOUYIN] Fetching latest {max_videos} videos from {creator_id}")
        
        async with aiohttp.ClientSession() as session:
            try:
                # 调用抖音API获取视频列表
                url = f"{self.douyin_api_url}/api/douyin/web/fetch_user_post_videos"
                params = {
                    'sec_user_id': creator_id,
                    'max_cursor': 0,
                    'count': max_videos
                }
                
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch Douyin videos: {response.status}")
                        return
                    
                    data = await response.json()
                    aweme_list = data.get('data', {}).get('aweme_list', [])
                    
                    logger.info(f"[DOUYIN] Found {len(aweme_list)} videos")
                    
                    # 保存到数据库
                    for video in aweme_list[:max_videos]:
                        try:
                            video_info = self._extract_douyin_video_info(video)
                            if video_info:
                                video_service.add_video(
                                    platform='douyin',
                                    creator_id=creator_id,
                                    **video_info
                                )
                        except Exception as e:
                            logger.error(f"Failed to add Douyin video: {e}")
                            
            except Exception as e:
                logger.error(f"Error fetching Douyin videos for {creator_id}: {e}")
    
    def _extract_douyin_video_info(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从抖音API响应中提取视频信息
        """
        try:
            aweme_id = video_data.get('aweme_id')
            if not aweme_id:
                return None
            
            # 提取基础信息
            video_info = {
                'video_id': aweme_id,
                'title': video_data.get('desc', ''),
                'description': video_data.get('desc', ''),
                'published_at': datetime.fromtimestamp(
                    video_data.get('create_time', 0),
                    tz=timezone.utc
                ) if video_data.get('create_time') else datetime.now(timezone.utc)
            }
            
            # 提取视频URL
            video_obj = video_data.get('video', {})
            play_addr = video_obj.get('play_addr', {})
            url_list = play_addr.get('url_list', [])
            
            if url_list:
                video_info['video_url'] = url_list[0]
            else:
                # 构造分享URL
                video_info['video_url'] = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
            
            # 提取封面URL
            cover = video_obj.get('cover', {})
            cover_url_list = cover.get('url_list', [])
            if cover_url_list:
                video_info['cover_url'] = cover_url_list[0]
            
            # 额外元数据
            video_info['metadata'] = {
                'create_time': video_data.get('create_time'),
                'statistics': video_data.get('statistics', {}),
                'author': video_data.get('author', {}).get('nickname', '')
            }
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error extracting Douyin video info: {e}")
            return None
    
    async def mark_video_completed(
        self,
        platform: str,
        creator_id: str,
        video_id: str
    ):
        """
        标记视频为已完成
        """
        db_session = self.Session()
        video_service = VideoSourceService(db_session)
        
        try:
            video = db_session.query(VideoSource).filter(
                and_(
                    VideoSource.platform == platform,
                    VideoSource.creator_id == creator_id,
                    VideoSource.video_id == video_id
                )
            ).first()
            
            if video:
                video_service.mark_as_completed(video)
                logger.info(f"[COMPLETE] Marked video as completed: {platform}/{video_id}")
            else:
                logger.warning(f"[COMPLETE] Video not found: {platform}/{video_id}")
                
        finally:
            db_session.close()
    
    async def mark_video_failed(
        self,
        platform: str,
        creator_id: str,
        video_id: str,
        error_msg: str
    ):
        """
        标记视频为失败
        """
        db_session = self.Session()
        video_service = VideoSourceService(db_session)
        
        try:
            video = db_session.query(VideoSource).filter(
                and_(
                    VideoSource.platform == platform,
                    VideoSource.creator_id == creator_id,
                    VideoSource.video_id == video_id
                )
            ).first()
            
            if video:
                video_service.mark_as_failed(video, error_msg)
                logger.info(f"[FAILED] Marked video as failed: {platform}/{video_id}")
            else:
                logger.warning(f"[FAILED] Video not found: {platform}/{video_id}")
                
        finally:
            db_session.close()