#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pipeline Context V3 - 专门为V3流程设计的数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class PipelineContextV3:
    """V3 Pipeline上下文 - 贯穿整个流程的数据载体"""
    
    # ========== 基础信息 ==========
    video_id: str
    creator_name: str
    
    # ========== 原始数据 ==========
    video_info: Dict[str, Any] = field(default_factory=dict)
    comments: List[Dict] = field(default_factory=list)
    subtitles: str = ""
    
    # ========== V3框架输出 ==========
    framework_v3_raw: str = ""           # 原始AI响应
    framework_v3_json: Dict = field(default_factory=dict)  # 解析后的JSON
    
    # ========== 解析后的结构信息 ==========
    segment_count: int = 0                # 从JSON解析出的segment数量
    segment_tasks: List[Dict] = field(default_factory=list)  # 每个segment的任务信息
    
    # ========== 生成的内容 ==========
    story_header: str = ""                # 独立生成的开头
    segments: List[str] = field(default_factory=list)  # 所有segment
    merged_story: str = ""                # 拼接后的原始故事
    polished_story: str = ""              # 润色后的故事
    final_story: str = ""                 # 最终英文故事
    summary_cn: str = ""                  # 中文总结
    youtube_metadata: Dict = field(default_factory=dict)  # YouTube发布元数据
    
    # ========== 元数据 ==========
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # ========== 缓存管理 ==========
    cache_dir: Optional[Path] = None
    save_intermediate: bool = True        # 是否保存中间结果
    
    def get(self, key: str, default=None):
        """获取上下文数据"""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        setattr(self, key, value)
    
    def update(self, **kwargs):
        """批量更新上下文"""
        for key, value in kwargs.items():
            self.set(key, value)
    
    def add_error(self, error: str):
        """添加错误信息"""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0
    
    def get_segment_task(self, index: int) -> Optional[Dict]:
        """获取指定索引的segment任务"""
        if 0 <= index < len(self.segment_tasks):
            return self.segment_tasks[index]
        return None
    
    def get_previous_text(self, segment_index: int, max_chars: int = 200) -> str:
        """获取前一个segment的结尾文本"""
        if segment_index == 0:
            # 第一个segment，使用header的结尾
            if self.story_header:
                return self.story_header[-max_chars:] if len(self.story_header) > max_chars else self.story_header
            return ""
        elif segment_index <= len(self.segments):
            # 使用前一个segment的结尾
            prev_segment = self.segments[segment_index - 1]
            return prev_segment[-max_chars:] if len(prev_segment) > max_chars else prev_segment
        return ""
    
    def to_dict(self) -> Dict:
        """转换为字典，用于保存"""
        return {
            'video_id': self.video_id,
            'creator_name': self.creator_name,
            'segment_count': self.segment_count,
            'total_length': len(self.final_story),
            'errors': self.errors,
            'metadata': self.metadata
        }