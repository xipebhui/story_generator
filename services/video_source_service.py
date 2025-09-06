#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频源管理服务
统一管理来自不同平台的视频获取和状态追踪
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from models.video_source import VideoSource

logger = logging.getLogger(__name__)


class VideoSourceService:
    """视频源管理服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def add_video(
        self,
        platform: str,
        creator_id: str,
        video_id: str,
        published_at: datetime,
        video_url: Optional[str] = None,
        cover_url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VideoSource:
        """
        添加或更新视频记录
        
        Args:
            platform: 平台（youtube/douyin）
            creator_id: 创作者ID
            video_id: 视频ID
            published_at: 发布时间
            video_url: 视频URL（抖音需要）
            cover_url: 封面URL（抖音需要）
            title: 标题
            description: 描述
            metadata: 额外元数据
        
        Returns:
            VideoSource: 视频记录
        """
        try:
            # 检查是否已存在
            existing = self.db.query(VideoSource).filter(
                and_(
                    VideoSource.platform == platform,
                    VideoSource.creator_id == creator_id,
                    VideoSource.video_id == video_id
                )
            ).first()
            
            if existing:
                logger.info(f"Video already exists: {platform}/{creator_id}/{video_id}")
                # 更新信息（如果有新的）
                if video_url and not existing.video_url:
                    existing.video_url = video_url
                if cover_url and not existing.cover_url:
                    existing.cover_url = cover_url
                if title and not existing.title:
                    existing.title = title
                if description and not existing.description:
                    existing.description = description
                self.db.commit()
                return existing
            
            # 创建新记录
            video = VideoSource(
                platform=platform,
                creator_id=creator_id,
                video_id=video_id,
                video_url=video_url,
                cover_url=cover_url,
                title=title,
                description=description,
                published_at=published_at,
                metadata=json.dumps(metadata) if metadata else None
            )
            
            self.db.add(video)
            self.db.commit()
            logger.info(f"Added new video: {platform}/{creator_id}/{video_id}")
            
            return video
            
        except Exception as e:
            logger.error(f"Error adding video: {e}")
            self.db.rollback()
            raise
    
    def get_latest_unprocessed_video(
        self,
        creator_ids: Optional[List[str]] = None,
        platform: Optional[str] = None
    ) -> Optional[VideoSource]:
        """
        获取最新的未处理视频
        
        Args:
            creator_ids: 创作者ID列表（可选）
            platform: 平台过滤（可选）
        
        Returns:
            VideoSource: 最新的未处理视频，如果没有则返回None
        """
        query = self.db.query(VideoSource).filter(
            VideoSource.status == 'pending'
        )
        
        if creator_ids:
            query = query.filter(VideoSource.creator_id.in_(creator_ids))
        
        if platform:
            query = query.filter(VideoSource.platform == platform)
        
        # 按发布时间降序排序，获取最新的
        video = query.order_by(desc(VideoSource.published_at)).first()
        
        if video:
            logger.info(f"Found unprocessed video: {video.platform}/{video.creator_id}/{video.video_id}")
        else:
            logger.info("No unprocessed videos found")
        
        return video
    
    def mark_as_processing(self, video: VideoSource) -> VideoSource:
        """
        标记视频为处理中
        
        Args:
            video: 视频记录
        
        Returns:
            VideoSource: 更新后的视频记录
        """
        video.status = 'processing'
        video.processed_at = datetime.now()
        self.db.commit()
        logger.info(f"Marked video as processing: {video.video_id}")
        return video
    
    def mark_as_completed(self, video: VideoSource) -> VideoSource:
        """
        标记视频为已完成
        
        Args:
            video: 视频记录
        
        Returns:
            VideoSource: 更新后的视频记录
        """
        video.status = 'completed'
        if not video.processed_at:
            video.processed_at = datetime.now()
        self.db.commit()
        logger.info(f"Marked video as completed: {video.video_id}")
        return video
    
    def mark_as_failed(self, video: VideoSource, error_msg: str) -> VideoSource:
        """
        标记视频为失败
        
        Args:
            video: 视频记录
            error_msg: 错误信息
        
        Returns:
            VideoSource: 更新后的视频记录
        """
        video.status = 'failed'
        video.process_error = error_msg
        if not video.processed_at:
            video.processed_at = datetime.now()
        self.db.commit()
        logger.info(f"Marked video as failed: {video.video_id} - {error_msg}")
        return video
    
    def get_creator_video_count(
        self,
        creator_id: str,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        获取创作者的视频数量
        
        Args:
            creator_id: 创作者ID
            platform: 平台过滤（可选）
            status: 状态过滤（可选）
        
        Returns:
            int: 视频数量
        """
        query = self.db.query(VideoSource).filter(
            VideoSource.creator_id == creator_id
        )
        
        if platform:
            query = query.filter(VideoSource.platform == platform)
        
        if status:
            query = query.filter(VideoSource.status == status)
        
        return query.count()
    
    def get_recent_videos(
        self,
        creator_id: str,
        platform: Optional[str] = None,
        days_back: int = 7,
        limit: int = 10
    ) -> List[VideoSource]:
        """
        获取创作者最近的视频
        
        Args:
            creator_id: 创作者ID
            platform: 平台过滤（可选）
            days_back: 获取最近多少天的视频
            limit: 返回数量限制
        
        Returns:
            List[VideoSource]: 视频列表
        """
        since_date = datetime.now() - timedelta(days=days_back)
        
        query = self.db.query(VideoSource).filter(
            and_(
                VideoSource.creator_id == creator_id,
                VideoSource.published_at >= since_date
            )
        )
        
        if platform:
            query = query.filter(VideoSource.platform == platform)
        
        return query.order_by(desc(VideoSource.published_at)).limit(limit).all()
    
    def check_video_exists(
        self,
        platform: str,
        creator_id: str,
        video_id: str
    ) -> bool:
        """
        检查视频是否已存在
        
        Args:
            platform: 平台
            creator_id: 创作者ID
            video_id: 视频ID
        
        Returns:
            bool: 是否存在
        """
        exists = self.db.query(VideoSource).filter(
            and_(
                VideoSource.platform == platform,
                VideoSource.creator_id == creator_id,
                VideoSource.video_id == video_id
            )
        ).first() is not None
        
        return exists
    
    def bulk_add_videos(
        self,
        videos: List[Dict[str, Any]]
    ) -> int:
        """
        批量添加视频
        
        Args:
            videos: 视频信息列表
        
        Returns:
            int: 成功添加的数量
        """
        added_count = 0
        
        for video_data in videos:
            try:
                self.add_video(**video_data)
                added_count += 1
            except Exception as e:
                logger.error(f"Failed to add video {video_data.get('video_id')}: {e}")
                continue
        
        logger.info(f"Bulk added {added_count}/{len(videos)} videos")
        return added_count
    
    def cleanup_old_processed_videos(self, days_to_keep: int = 30) -> int:
        """
        清理旧的已处理视频
        
        Args:
            days_to_keep: 保留最近多少天的记录
        
        Returns:
            int: 删除的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted = self.db.query(VideoSource).filter(
            and_(
                VideoSource.status == 'completed',
                VideoSource.processed_at < cutoff_date
            )
        ).delete()
        
        self.db.commit()
        logger.info(f"Cleaned up {deleted} old processed videos")
        
        return deleted