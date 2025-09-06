#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理状态管理服务
提供视频处理状态的增删改查功能
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session

from models.video_processing import (
    VideoProcessingStatus, 
    Platform, 
    ProcessingStage
)

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """视频处理状态管理服务"""
    
    def __init__(self, db_session: Session):
        """
        初始化服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def create_or_update_video(
        self,
        platform: str,
        creator_id: str,
        video_id: str,
        **kwargs
    ) -> VideoProcessingStatus:
        """
        创建或更新视频记录
        
        Args:
            platform: 平台名称
            creator_id: 创作者ID
            video_id: 视频ID
            **kwargs: 其他字段
        
        Returns:
            VideoProcessingStatus: 视频处理状态对象
        """
        try:
            # 查找已存在的记录
            video_status = self.db.query(VideoProcessingStatus).filter(
                and_(
                    VideoProcessingStatus.platform == Platform(platform),
                    VideoProcessingStatus.creator_id == creator_id,
                    VideoProcessingStatus.video_id == video_id
                )
            ).first()
            
            if video_status:
                # 更新现有记录
                for key, value in kwargs.items():
                    if hasattr(video_status, key):
                        if key == 'processing_stage' and isinstance(value, str):
                            value = ProcessingStage(value)
                        elif key == 'published_at' and isinstance(value, str):
                            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        setattr(video_status, key, value)
                
                video_status.updated_at = datetime.utcnow()
                logger.info(f"Updated video status: {platform}/{creator_id}/{video_id}")
            else:
                # 创建新记录
                if 'processing_stage' in kwargs and isinstance(kwargs['processing_stage'], str):
                    kwargs['processing_stage'] = ProcessingStage(kwargs['processing_stage'])
                if 'published_at' in kwargs and isinstance(kwargs['published_at'], str):
                    kwargs['published_at'] = datetime.fromisoformat(kwargs['published_at'].replace('Z', '+00:00'))
                
                video_status = VideoProcessingStatus(
                    platform=Platform(platform),
                    creator_id=creator_id,
                    video_id=video_id,
                    **kwargs
                )
                self.db.add(video_status)
                logger.info(f"Created new video status: {platform}/{creator_id}/{video_id}")
            
            self.db.commit()
            return video_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating video status: {e}")
            raise
    
    def get_video_status(
        self, 
        platform: str, 
        creator_id: str, 
        video_id: str
    ) -> Optional[VideoProcessingStatus]:
        """
        获取视频处理状态
        
        Args:
            platform: 平台名称
            creator_id: 创作者ID
            video_id: 视频ID
        
        Returns:
            VideoProcessingStatus: 视频处理状态对象，如果不存在则返回None
        """
        try:
            return self.db.query(VideoProcessingStatus).filter(
                and_(
                    VideoProcessingStatus.platform == Platform(platform),
                    VideoProcessingStatus.creator_id == creator_id,
                    VideoProcessingStatus.video_id == video_id
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting video status: {e}")
            return None
    
    def get_unprocessed_videos(
        self,
        platform: str,
        creator_list: List[str],
        limit: int = 100
    ) -> List[VideoProcessingStatus]:
        """
        获取未完成处理的视频列表
        
        Args:
            platform: 平台名称
            creator_list: 创作者ID列表
            limit: 最大返回数量
        
        Returns:
            List[VideoProcessingStatus]: 未处理的视频列表
        """
        try:
            query = self.db.query(VideoProcessingStatus).filter(
                and_(
                    VideoProcessingStatus.platform == Platform(platform),
                    VideoProcessingStatus.creator_id.in_(creator_list),
                    VideoProcessingStatus.is_completed == False,
                    or_(
                        VideoProcessingStatus.is_failed == False,
                        VideoProcessingStatus.retry_count < 3  # 失败但重试次数少于3次的也可以获取
                    )
                )
            )
            
            # 按发布时间降序排序，获取最新的
            query = query.order_by(desc(VideoProcessingStatus.published_at))
            
            return query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting unprocessed videos: {e}")
            return []
    
    def get_latest_unprocessed_video(
        self,
        platform: str,
        creator_list: List[str]
    ) -> Optional[VideoProcessingStatus]:
        """
        获取最新的未处理视频
        
        Args:
            platform: 平台名称
            creator_list: 创作者ID列表
        
        Returns:
            VideoProcessingStatus: 最新的未处理视频，如果没有则返回None
        """
        videos = self.get_unprocessed_videos(platform, creator_list, limit=1)
        return videos[0] if videos else None
    
    def update_processing_stage(
        self,
        video_status: VideoProcessingStatus,
        stage: str,
        **kwargs
    ) -> VideoProcessingStatus:
        """
        更新视频处理阶段
        
        Args:
            video_status: 视频状态对象
            stage: 新的处理阶段
            **kwargs: 其他要更新的字段
        
        Returns:
            VideoProcessingStatus: 更新后的状态对象
        """
        try:
            video_status.processing_stage = ProcessingStage(stage)
            video_status.updated_at = datetime.utcnow()
            
            # 如果是完成状态，设置完成标志
            if stage == ProcessingStage.PUBLISHED.value:
                video_status.is_completed = True
                video_status.completed_at = datetime.utcnow()
            
            # 更新其他字段
            for key, value in kwargs.items():
                if hasattr(video_status, key):
                    setattr(video_status, key, value)
            
            self.db.commit()
            logger.info(f"Updated processing stage to {stage} for video {video_status.video_id}")
            return video_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating processing stage: {e}")
            raise
    
    def mark_as_failed(
        self,
        video_status: VideoProcessingStatus,
        reason: str
    ) -> VideoProcessingStatus:
        """
        标记视频处理失败
        
        Args:
            video_status: 视频状态对象
            reason: 失败原因
        
        Returns:
            VideoProcessingStatus: 更新后的状态对象
        """
        try:
            video_status.is_failed = True
            video_status.failure_reason = reason
            video_status.retry_count += 1
            video_status.processing_stage = ProcessingStage.FAILED
            video_status.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Marked video {video_status.video_id} as failed: {reason}")
            return video_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking video as failed: {e}")
            raise
    
    def reset_failed_video(
        self,
        video_status: VideoProcessingStatus
    ) -> VideoProcessingStatus:
        """
        重置失败的视频，以便重试
        
        Args:
            video_status: 视频状态对象
        
        Returns:
            VideoProcessingStatus: 重置后的状态对象
        """
        try:
            video_status.is_failed = False
            video_status.failure_reason = None
            # 根据已完成的阶段重置到合适的状态
            if video_status.video_path:
                video_status.processing_stage = ProcessingStage.VIDEO_EXPORTED
            elif video_status.draft_path:
                video_status.processing_stage = ProcessingStage.DRAFT_CREATED
            elif video_status.audio_path:
                video_status.processing_stage = ProcessingStage.TTS_GENERATED
            elif video_status.story_path:
                video_status.processing_stage = ProcessingStage.STORY_GENERATED
            else:
                video_status.processing_stage = ProcessingStage.FETCHED
            
            video_status.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Reset failed video {video_status.video_id} to stage {video_status.processing_stage}")
            return video_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting failed video: {e}")
            raise
    
    def get_processing_stats(
        self,
        platform: Optional[str] = None,
        creator_id: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Args:
            platform: 平台名称（可选）
            creator_id: 创作者ID（可选）
            account_id: 账号ID（可选）
        
        Returns:
            dict: 统计信息
        """
        try:
            query = self.db.query(VideoProcessingStatus)
            
            if platform:
                query = query.filter(VideoProcessingStatus.platform == Platform(platform))
            if creator_id:
                query = query.filter(VideoProcessingStatus.creator_id == creator_id)
            if account_id:
                query = query.filter(VideoProcessingStatus.account_id == account_id)
            
            total = query.count()
            completed = query.filter(VideoProcessingStatus.is_completed == True).count()
            failed = query.filter(VideoProcessingStatus.is_failed == True).count()
            in_progress = total - completed - failed
            
            # 按阶段统计
            stage_counts = {}
            for stage in ProcessingStage:
                count = query.filter(VideoProcessingStatus.processing_stage == stage).count()
                stage_counts[stage.value] = count
            
            return {
                'total': total,
                'completed': completed,
                'failed': failed,
                'in_progress': in_progress,
                'stage_counts': stage_counts,
                'success_rate': (completed / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}