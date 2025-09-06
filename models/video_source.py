#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频源追踪模型
用于记录来自不同平台的视频信息和处理状态
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class VideoSource(Base):
    """
    视频源表，记录来自YouTube和抖音的视频信息
    """
    __tablename__ = 'video_sources'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基础信息
    platform = Column(String(50), nullable=False)  # youtube, douyin
    creator_id = Column(String(255), nullable=False)  # 创作者ID
    video_id = Column(String(255), nullable=False)  # 视频ID
    
    # 视频信息（YouTube只需要基础信息，抖音需要更多）
    video_url = Column(Text)  # 视频URL（主要用于抖音）
    cover_url = Column(Text)  # 封面URL（主要用于抖音）
    title = Column(Text)  # 标题
    description = Column(Text)  # 描述
    
    # 时间信息
    published_at = Column(DateTime, nullable=False)  # 发布时间
    fetched_at = Column(DateTime, default=datetime.now)  # 获取时间
    processed_at = Column(DateTime)  # 处理时间
    
    # 状态信息
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    process_error = Column(Text)  # 处理错误信息
    
    # 额外元数据（JSON格式）
    metadata = Column(Text)  # 存储其他平台特定信息
    
    # 索引
    __table_args__ = (
        Index('idx_platform_creator', 'platform', 'creator_id'),
        Index('idx_platform_video', 'platform', 'video_id'),
        Index('idx_status_published', 'status', 'published_at'),
        Index('idx_creator_status', 'creator_id', 'status'),
        # 唯一索引，防止重复
        Index('idx_unique_video', 'platform', 'creator_id', 'video_id', unique=True),
    )
    
    def __repr__(self):
        return f"<VideoSource(platform={self.platform}, creator={self.creator_id}, video={self.video_id}, status={self.status})>"