#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理状态跟踪模型
用于记录视频在各个处理阶段的状态
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class Platform(enum.Enum):
    """视频平台枚举"""
    YOUTUBE = "youtube"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"
    BILIBILI = "bilibili"


class ProcessingStage(enum.Enum):
    """处理阶段枚举"""
    FETCHED = "fetched"              # 已获取视频信息
    STORY_GENERATED = "story_generated"  # 已生成故事
    TTS_GENERATED = "tts_generated"      # 已生成语音
    DRAFT_CREATED = "draft_created"      # 已创建草稿
    VIDEO_EXPORTED = "video_exported"    # 已导出视频
    PUBLISHED = "published"              # 已发布
    FAILED = "failed"                    # 处理失败


class VideoProcessingStatus(Base):
    """视频处理状态表"""
    __tablename__ = 'video_processing_status'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 视频标识
    platform = Column(Enum(Platform), nullable=False, index=True)
    creator_id = Column(String(255), nullable=False, index=True)
    video_id = Column(String(255), nullable=False, index=True)
    
    # 视频信息
    channel_id = Column(String(255))
    channel_title = Column(String(500))
    video_title = Column(Text)
    video_url = Column(String(500))
    published_at = Column(DateTime)
    
    # 处理状态
    processing_stage = Column(Enum(ProcessingStage), default=ProcessingStage.FETCHED, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    is_failed = Column(Boolean, default=False, nullable=False)
    
    # 处理账号
    account_id = Column(String(255), index=True)  # 执行处理的账号ID
    
    # 失败信息
    failure_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # 文件路径（可选）
    story_path = Column(String(500))
    audio_path = Column(String(500))
    draft_path = Column(String(500))
    video_path = Column(String(500))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    
    # 复合唯一索引，确保同一平台、创作者、视频只有一条记录
    __table_args__ = (
        Index('idx_unique_video', 'platform', 'creator_id', 'video_id', unique=True),
        Index('idx_status_query', 'platform', 'is_completed', 'is_failed'),
        Index('idx_processing_stage', 'processing_stage', 'is_completed'),
    )
    
    def __repr__(self):
        return f"<VideoProcessingStatus(platform={self.platform}, creator={self.creator_id}, video={self.video_id}, stage={self.processing_stage})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'platform': self.platform.value if self.platform else None,
            'creator_id': self.creator_id,
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'channel_title': self.channel_title,
            'video_title': self.video_title,
            'video_url': self.video_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'processing_stage': self.processing_stage.value if self.processing_stage else None,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'account_id': self.account_id,
            'failure_reason': self.failure_reason,
            'retry_count': self.retry_count,
            'story_path': self.story_path,
            'audio_path': self.audio_path,
            'draft_path': self.draft_path,
            'video_path': self.video_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }