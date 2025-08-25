#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline数据模型定义
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class Gender(Enum):
    """性别枚举"""
    FEMALE = 0
    MALE = 1


class StageStatus(Enum):
    """阶段执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineRequest(BaseModel):
    """Pipeline执行请求"""
    video_id: str = Field(..., description="YouTube视频ID")
    creator_id: str = Field(..., description="创作者ID")
    gender: Gender = Field(Gender.FEMALE, description="语音性别")
    duration: int = Field(120, ge=30, le=600, description="每张图片展示时长(秒)")
    image_dir: Optional[str] = Field(None, description="图库目录路径")
    export_video: bool = Field(False, description="是否导出视频文件")
    enable_subtitle: bool = Field(False, description="是否启用字幕（默认禁用，用于调试）")
    
    @validator('video_id')
    def validate_video_id(cls, v):
        """验证视频ID格式"""
        if not v or len(v) < 6:
            raise ValueError("无效的视频ID")
        return v
    
    @validator('creator_id')
    def validate_creator_id(cls, v):
        """验证创作者ID"""
        if not v or not v.strip():
            raise ValueError("创作者ID不能为空")
        return v.strip()
    
    class Config:
        use_enum_values = True


class StageResult(BaseModel):
    """阶段执行结果"""
    name: str = Field(..., description="阶段名称")
    status: StageStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长(秒)")
    output: Optional[str] = Field(None, description="输出信息")
    error: Optional[str] = Field(None, description="错误信息")
    output_files: Optional[List[str]] = Field(default_factory=list, description="输出文件路径列表")


class ContentReport(BaseModel):
    """内容生成报告"""
    video_title: Optional[str] = Field(None, description="视频标题")
    video_url: Optional[str] = Field(None, description="视频链接")
    story_summary: Optional[str] = Field(None, description="故事摘要")
    character_count: Optional[int] = Field(None, description="字符数")
    paragraph_count: Optional[int] = Field(None, description="段落数")
    keywords: Optional[List[str]] = Field(default_factory=list, description="关键词列表")
    themes: Optional[List[str]] = Field(default_factory=list, description="主题列表")


class YouTubeSuggestions(BaseModel):
    """YouTube优化建议"""
    title_suggestions: Optional[List[str]] = Field(default_factory=list, description="标题建议")
    description_template: Optional[str] = Field(None, description="描述模板")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签建议")
    thumbnail_ideas: Optional[List[str]] = Field(default_factory=list, description="缩略图创意")
    seo_keywords: Optional[List[str]] = Field(default_factory=list, description="SEO关键词")


class PipelineResponse(BaseModel):
    """Pipeline执行响应"""
    status: TaskStatus = Field(..., description="任务状态")
    task_id: Optional[str] = Field(None, description="任务ID")
    video_id: str = Field(..., description="视频ID")
    creator_id: str = Field(..., description="创作者ID")
    
    # 输出文件路径
    video_path: Optional[str] = Field(None, description="最终视频文件路径")
    video_url: Optional[str] = Field(None, description="视频访问URL")
    preview_url: Optional[str] = Field(None, description="30秒预览视频URL")
    draft_path: Optional[str] = Field(None, description="剪映草稿文件路径")
    audio_path: Optional[str] = Field(None, description="音频文件路径")
    story_path: Optional[str] = Field(None, description="故事文本路径")
    
    # 报告和建议
    content_report: Optional[ContentReport] = Field(None, description="内容报告")
    youtube_suggestions: Optional[YouTubeSuggestions] = Field(None, description="YouTube建议")
    report_file_paths: Optional[Dict[str, str]] = Field(default_factory=dict, description="报告文件路径")
    
    # 执行详情
    stages: List[StageResult] = Field(default_factory=list, description="阶段执行结果")
    total_duration: Optional[float] = Field(None, description="总执行时长(秒)")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: Optional[float] = Field(None, ge=0, le=100, description="进度百分比")
    current_stage: Optional[str] = Field(None, description="当前执行阶段")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[PipelineResponse] = Field(None, description="执行结果(完成时)")
