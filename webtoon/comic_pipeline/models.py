#!/usr/bin/env python3
"""
数据模型定义
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class SceneType(Enum):
    """场景类型"""
    ACTION = "action"          # 动作场景
    DIALOG = "dialog"          # 对话场景
    TRANSITION = "transition"  # 过渡场景
    CLIMAX = "climax"          # 高潮场景
    STATIC = "static"          # 静态场景


class EmotionTone(Enum):
    """情绪基调"""
    TENSE = "紧张"
    RELAXED = "轻松"
    EXCITING = "激动"
    SAD = "悲伤"
    MYSTERIOUS = "神秘"
    HUMOROUS = "幽默"
    NEUTRAL = "平静"


@dataclass
class ComicImage:
    """漫画图片信息"""
    path: str                  # 图片路径
    index: int                 # 图片索引（在章节中的位置）
    chapter: str               # 所属章节
    filename: str              # 文件名
    
    @property
    def full_path(self) -> Path:
        """获取完整路径"""
        return Path(self.path)
    
    def __str__(self) -> str:
        return f"ComicImage(ch={self.chapter}, idx={self.index}, file={self.filename})"


@dataclass
class ImageAnalysis:
    """图片分析结果"""
    image: ComicImage          # 对应的图片
    description: str           # 画面描述
    scene_type: SceneType      # 场景类型
    emotion: EmotionTone       # 情绪基调
    characters: List[str]      # 出现的角色
    action: str                # 主要动作/事件
    dialog: Optional[str] = None  # 对话内容（如果有）
    objects: List[str] = field(default_factory=list)  # 重要物品
    
    def get_suggested_duration(self) -> tuple:
        """根据场景类型获取建议时长范围（秒）"""
        duration_map = {
            SceneType.ACTION: (3, 5),
            SceneType.DIALOG: (5, 8),
            SceneType.TRANSITION: (2, 3),
            SceneType.CLIMAX: (8, 10),
            SceneType.STATIC: (3, 4)
        }
        return duration_map.get(self.scene_type, (3, 5))
    
    def get_suggested_word_count(self) -> tuple:
        """根据场景类型获取建议字数范围"""
        word_count_map = {
            SceneType.ACTION: (30, 40),
            SceneType.DIALOG: (50, 70),
            SceneType.TRANSITION: (20, 30),
            SceneType.CLIMAX: (60, 80),
            SceneType.STATIC: (25, 35)
        }
        return word_count_map.get(self.scene_type, (30, 50))


@dataclass
class NarrationContext:
    """解说上下文信息"""
    previous_narrations: List[str] = field(default_factory=list)  # 前面的解说文案
    story_outline: str = ""        # 整体故事大纲
    current_emotion: EmotionTone = EmotionTone.NEUTRAL  # 当前情绪基调
    key_characters: List[str] = field(default_factory=list)  # 主要角色
    story_progress: float = 0.0    # 故事进度（0-1）
    
    def add_narration(self, text: str):
        """添加新的解说到历史"""
        self.previous_narrations.append(text)
        # 只保留最近5条
        if len(self.previous_narrations) > 5:
            self.previous_narrations = self.previous_narrations[-5:]
    
    def get_recent_context(self, n: int = 3) -> str:
        """获取最近的n条解说作为上下文"""
        recent = self.previous_narrations[-n:] if len(self.previous_narrations) >= n else self.previous_narrations
        return " ".join(recent)


@dataclass
class NarrationSegment:
    """解说片段"""
    image: ComicImage          # 对应的图片
    text: str                  # 解说文案
    duration: float            # 实际时长（秒）
    audio_file: Optional[str] = None  # 音频文件路径
    subtitle_file: Optional[str] = None  # 字幕文件路径
    start_time: float = 0.0    # 在完整音频中的起始时间
    end_time: float = 0.0      # 在完整音频中的结束时间
    word_count: int = 0        # 字数
    
    def __post_init__(self):
        """初始化后处理"""
        if self.word_count == 0:
            self.word_count = len(self.text.replace(" ", ""))
        if self.end_time == 0.0 and self.duration > 0:
            self.end_time = self.start_time + self.duration


@dataclass
class ComicChapter:
    """漫画章节信息"""
    title: str                 # 章节标题
    index: int                 # 章节索引
    images: List[ComicImage]   # 包含的图片
    total_images: int          # 图片总数
    
    @property
    def directory(self) -> str:
        """获取章节目录名"""
        return f"{self.index:03d}_{self.title}"


@dataclass
class PipelineResult:
    """Pipeline执行结果"""
    success: bool              # 是否成功
    comic_dir: str             # 漫画目录
    segments: List[NarrationSegment]  # 所有解说片段
    total_duration: float      # 总时长
    audio_file: Optional[str] = None  # 合并的音频文件
    draft_path: Optional[str] = None  # 剪映草稿路径
    error_message: Optional[str] = None  # 错误信息
    stats: Dict[str, Any] = field(default_factory=dict)  # 统计信息
    
    def get_summary(self) -> str:
        """获取执行摘要"""
        if not self.success:
            return f"Pipeline执行失败: {self.error_message}"
        
        summary = [
            f"Pipeline执行成功！",
            f"处理章节: {self.comic_dir}",
            f"生成片段: {len(self.segments)}个",
            f"总时长: {self.total_duration:.1f}秒",
        ]
        
        if self.audio_file:
            summary.append(f"音频文件: {self.audio_file}")
        if self.draft_path:
            summary.append(f"剪映草稿: {self.draft_path}")
        
        if self.stats:
            summary.append("\n统计信息:")
            for key, value in self.stats.items():
                summary.append(f"  {key}: {value}")
        
        return "\n".join(summary)


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    images: List[ComicImage]
    analyses: List[ImageAnalysis]
    story_outline: str         # 故事大纲
    main_characters: List[str] # 主要角色
    overall_tone: EmotionTone  # 整体基调
    
    def get_analysis_by_index(self, index: int) -> Optional[ImageAnalysis]:
        """根据索引获取分析结果"""
        for analysis in self.analyses:
            if analysis.image.index == index:
                return analysis
        return None