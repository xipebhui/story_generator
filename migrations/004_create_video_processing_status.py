#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建视频处理状态表的迁移脚本
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import enum


class Platform(enum.Enum):
    """视频平台枚举"""
    YOUTUBE = "youtube"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"
    BILIBILI = "bilibili"


class ProcessingStage(enum.Enum):
    """处理阶段枚举"""
    FETCHED = "fetched"
    STORY_GENERATED = "story_generated"
    TTS_GENERATED = "tts_generated"
    DRAFT_CREATED = "draft_created"
    VIDEO_EXPORTED = "video_exported"
    PUBLISHED = "published"
    FAILED = "failed"


def upgrade():
    """创建video_processing_status表"""
    op.create_table(
        'video_processing_status',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        
        # 视频标识
        sa.Column('platform', sa.Enum(Platform), nullable=False),
        sa.Column('creator_id', sa.String(255), nullable=False),
        sa.Column('video_id', sa.String(255), nullable=False),
        
        # 视频信息
        sa.Column('channel_id', sa.String(255)),
        sa.Column('channel_title', sa.String(500)),
        sa.Column('video_title', sa.Text()),
        sa.Column('video_url', sa.String(500)),
        sa.Column('published_at', sa.DateTime()),
        
        # 处理状态
        sa.Column('processing_stage', sa.Enum(ProcessingStage), 
                  server_default='fetched', nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_failed', sa.Boolean(), nullable=False, default=False),
        
        # 处理账号
        sa.Column('account_id', sa.String(255)),
        
        # 失败信息
        sa.Column('failure_reason', sa.Text()),
        sa.Column('retry_count', sa.Integer(), default=0),
        
        # 文件路径
        sa.Column('story_path', sa.String(500)),
        sa.Column('audio_path', sa.String(500)),
        sa.Column('draft_path', sa.String(500)),
        sa.Column('video_path', sa.String(500)),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                  server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.current_timestamp(),
                  onupdate=sa.func.current_timestamp()),
        sa.Column('completed_at', sa.DateTime()),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_unique_video', 'video_processing_status', 
                    ['platform', 'creator_id', 'video_id'], unique=True)
    op.create_index('idx_status_query', 'video_processing_status',
                    ['platform', 'is_completed', 'is_failed'])
    op.create_index('idx_processing_stage', 'video_processing_status',
                    ['processing_stage', 'is_completed'])
    op.create_index('idx_creator', 'video_processing_status', ['creator_id'])
    op.create_index('idx_account', 'video_processing_status', ['account_id'])
    op.create_index('idx_video', 'video_processing_status', ['video_id'])


def downgrade():
    """删除video_processing_status表"""
    op.drop_table('video_processing_status')