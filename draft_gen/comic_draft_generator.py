#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫画专用剪映草稿生成器
专门为漫画视频生成剪映草稿，支持音频分段对齐和Ken Burns动画效果
"""

import os
import sys
import json
import uuid
import random
import shutil
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydub import AudioSegment
from draft_gen.models.draft_models import (
    Draft, Track, Segment, VideoMaterial, AudioMaterial, Materials,
    Timerange, Clip, Transition, VideoEffect, Keyframe, CommonKeyframe
)
from draft_gen.models.draft_effects_library import (
    Transitions, VideoEffects, SpeedInfo, CanvasInfo, MaterialAnimationInfo
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AudioSegmentInfo:
    """音频片段信息"""
    index: int                # 片段索引
    audio_file: str           # 音频文件路径
    duration: float           # 时长（秒）
    start_time: float         # 在合并音频中的开始时间（秒）
    end_time: float          # 在合并音频中的结束时间（秒）
    image_file: str          # 对应的图片文件路径
    narration_text: str = "" # 解说文本（用于生成字幕）


@dataclass
class ComicDraftConfig:
    """漫画草稿配置"""
    # 画布设置
    canvas_width: int = 1080
    canvas_height: int = 1920
    fps: int = 30
    
    # 图片动画设置
    enable_ken_burns: bool = True           # 启用Ken Burns效果
    ken_burns_scale_range: Tuple[float, float] = (1.5, 2.0)  # 缩放范围
    ken_burns_move_range: Tuple[float, float] = (-0.1, 0.1)  # 移动范围（相对于画布）
    
    # 转场设置
    enable_transitions: bool = False        # 漫画通常不需要转场
    transition_duration_ms: int = 300       # 转场时长（毫秒）
    
    # 音频设置
    audio_gap_ms: int = 0                   # 音频片段间隔（毫秒）
    audio_fade_in_ms: int = 100            # 音频淡入（毫秒）
    audio_fade_out_ms: int = 100           # 音频淡出（毫秒）
    
    # 字幕设置
    enable_subtitles: bool = True          # 启用字幕
    subtitle_font_size: int = 48           # 字幕字体大小
    subtitle_margin_bottom: int = 100       # 字幕底部边距


class ComicDraftGenerator:
    """漫画专用草稿生成器"""
    
    def __init__(self, config: Optional[ComicDraftConfig] = None):
        """
        初始化漫画草稿生成器
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or ComicDraftConfig()
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        self.supported_audio_formats = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
        
    def generate_comic_draft(
        self,
        audio_segments: List[AudioSegmentInfo],
        merged_audio_path: Optional[str] = None,
        output_dir: str = "output/drafts",
        project_name: str = "comic_video",
        srt_path: Optional[str] = None
    ) -> str:
        """
        生成漫画剪映草稿
        
        Args:
            audio_segments: 音频片段信息列表（包含时间映射）
            merged_audio_path: 合并后的音频文件路径（如果没有，会自动合并）
            output_dir: 输出目录
            project_name: 项目名称
            srt_path: SRT字幕文件路径（可选）
            
        Returns:
            草稿文件夹路径
        """
        logger.info(f"开始生成漫画剪映草稿: {project_name}")
        logger.info(f"音频片段数: {len(audio_segments)}")
        
        # 创建输出目录
        output_path = Path(output_dir) / project_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 如果没有提供合并音频，自动合并
        if not merged_audio_path:
            merged_audio_path = self._merge_audio_segments(audio_segments, output_path)
        
        # 获取总时长
        total_duration_ms = self._get_audio_duration_ms(merged_audio_path)
        total_duration_us = total_duration_ms * 1000
        
        logger.info(f"总时长: {total_duration_ms/1000:.2f}秒")
        
        # 创建草稿结构
        draft = self._create_draft_structure(
            audio_segments=audio_segments,
            merged_audio_path=merged_audio_path,
            total_duration_us=total_duration_us,
            srt_path=srt_path
        )
        
        # 复制素材文件
        materials_dir = output_path / "materials"
        materials_dir.mkdir(exist_ok=True)
        
        # 复制音频文件
        audio_dst = materials_dir / Path(merged_audio_path).name
        shutil.copy2(merged_audio_path, audio_dst)
        
        # 复制图片文件
        for segment in audio_segments:
            image_src = Path(segment.image_file)
            image_dst = materials_dir / image_src.name
            if image_src.exists() and not image_dst.exists():
                shutil.copy2(image_src, image_dst)
        
        # 保存草稿文件
        draft_content_path = output_path / "draft_content.json"
        with open(draft_content_path, 'w', encoding='utf-8') as f:
            json.dump(draft.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 创建draft_meta_info.json
        meta_info = {
            "draft_id": draft.id,
            "draft_name": project_name,
            "draft_fold_path": str(output_path),
            "create_time": 0,
            "duration": total_duration_ms
        }
        
        meta_info_path = output_path / "draft_meta_info.json"
        with open(meta_info_path, 'w', encoding='utf-8') as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 漫画草稿生成完成: {output_path}")
        return str(output_path)
    
    def _create_draft_structure(
        self,
        audio_segments: List[AudioSegmentInfo],
        merged_audio_path: str,
        total_duration_us: int,
        srt_path: Optional[str] = None
    ) -> Draft:
        """创建草稿结构"""
        
        # 创建Materials
        materials = Materials(videos=[], audios=[], images=[], texts=[], stickers=[])
        
        # 添加音频素材
        audio_material = AudioMaterial(
            id=self._gen_uuid(),
            name=Path(merged_audio_path).name,
            path=f"materials/{Path(merged_audio_path).name}",
            duration=total_duration_us,
            type="audio"
        )
        materials.audios.append(audio_material)
        
        # 添加图片素材
        for segment in audio_segments:
            image_path = Path(segment.image_file)
            video_material = VideoMaterial(
                id=self._gen_uuid(),
                name=image_path.name,
                path=f"materials/{image_path.name}",
                duration=int(segment.duration * 1000000),  # 转换为微秒
                width=self.config.canvas_width,
                height=self.config.canvas_height,
                type="photo"
            )
            materials.videos.append(video_material)
        
        # 创建Tracks
        tracks = []
        
        # 视频轨道（图片）
        video_track = self._create_video_track(audio_segments, materials.videos)
        tracks.append(video_track)
        
        # 音频轨道（多段音频）
        audio_track = self._create_audio_track(audio_segments, audio_material, total_duration_us)
        tracks.append(audio_track)
        
        # 字幕轨道（如果有）
        if srt_path and Path(srt_path).exists():
            subtitle_track = self._create_subtitle_track(srt_path, total_duration_us)
            if subtitle_track:
                tracks.append(subtitle_track)
        
        # 创建Draft
        draft = Draft(
            id=self._gen_uuid(),
            name=f"漫画视频_{Path(merged_audio_path).stem}",
            tracks=tracks,
            materials=materials,
            canvas_config=CanvasInfo(
                width=self.config.canvas_width,
                height=self.config.canvas_height,
                fps=self.config.fps
            ).to_dict(),
            duration=total_duration_us
        )
        
        return draft
    
    def _create_video_track(
        self,
        audio_segments: List[AudioSegmentInfo],
        video_materials: List[VideoMaterial]
    ) -> Track:
        """创建视频轨道（图片序列）"""
        segments = []
        
        for i, (audio_seg, video_mat) in enumerate(zip(audio_segments, video_materials)):
            # 时间范围（微秒）
            start_us = int(audio_seg.start_time * 1000000)
            end_us = int(audio_seg.end_time * 1000000)
            duration_us = end_us - start_us
            
            # 创建关键帧动画（Ken Burns效果）
            keyframes = []
            if self.config.enable_ken_burns:
                keyframes = self._create_ken_burns_keyframes(duration_us, i)
            
            # 创建片段
            clip = Clip(
                id=self._gen_uuid(),
                type="video",
                material_id=video_mat.id,
                source_timerange=Timerange(start=0, duration=duration_us),
                target_timerange=Timerange(start=start_us, duration=duration_us),
                speed=1.0,
                volume=1.0,
                extra_material_refs=[]
            )
            
            # 添加动画信息
            if keyframes:
                clip.animation = MaterialAnimationInfo(
                    keyframe_list=keyframes
                ).to_dict()
            
            segment = Segment(
                id=self._gen_uuid(),
                type="video",
                clip=clip,
                common_keyframes=keyframes
            )
            
            segments.append(segment)
        
        return Track(
            id=self._gen_uuid(),
            type="video",
            segments=segments
        )
    
    def _create_audio_track(
        self,
        audio_segments: List[AudioSegmentInfo],
        audio_material: AudioMaterial,
        total_duration_us: int
    ) -> Track:
        """
        创建音频轨道
        使用单个合并音频文件，但创建多个segment来标记每个片段
        """
        segments = []
        
        for i, audio_seg in enumerate(audio_segments):
            # 时间范围（微秒）
            start_us = int(audio_seg.start_time * 1000000)
            end_us = int(audio_seg.end_time * 1000000)
            duration_us = end_us - start_us
            
            # 创建音频片段
            clip = Clip(
                id=self._gen_uuid(),
                type="audio",
                material_id=audio_material.id,
                source_timerange=Timerange(start=start_us, duration=duration_us),
                target_timerange=Timerange(start=start_us, duration=duration_us),
                speed=1.0,
                volume=1.0,
                extra_material_refs=[]
            )
            
            # 添加淡入淡出效果
            fade_in = min(self.config.audio_fade_in_ms * 1000, duration_us // 10)
            fade_out = min(self.config.audio_fade_out_ms * 1000, duration_us // 10)
            
            clip.audio_fade = {
                "fade_in": fade_in,
                "fade_out": fade_out
            }
            
            segment = Segment(
                id=self._gen_uuid(),
                type="audio",
                clip=clip
            )
            
            segments.append(segment)
        
        return Track(
            id=self._gen_uuid(),
            type="audio",
            segments=segments
        )
    
    def _create_ken_burns_keyframes(self, duration_us: int, index: int) -> List[CommonKeyframe]:
        """
        创建Ken Burns效果关键帧（随机缩放和移动）
        
        Args:
            duration_us: 片段时长（微秒）
            index: 片段索引（用于随机化）
            
        Returns:
            关键帧列表
        """
        keyframes = []
        
        # 随机选择动画类型
        animation_types = ['zoom_in', 'zoom_out', 'pan_up', 'pan_down', 'zoom_pan']
        animation_type = random.choice(animation_types)
        
        # 起始和结束缩放
        scale_min, scale_max = self.config.ken_burns_scale_range
        move_min, move_max = self.config.ken_burns_move_range
        
        if animation_type == 'zoom_in':
            # 放大效果
            start_scale = random.uniform(scale_min, scale_min + 0.3)
            end_scale = random.uniform(scale_max - 0.3, scale_max)
            start_x = random.uniform(move_min/2, move_max/2)
            start_y = random.uniform(move_min/2, move_max/2)
            end_x = start_x
            end_y = start_y
            
        elif animation_type == 'zoom_out':
            # 缩小效果
            start_scale = random.uniform(scale_max - 0.3, scale_max)
            end_scale = random.uniform(scale_min, scale_min + 0.3)
            start_x = 0
            start_y = 0
            end_x = random.uniform(move_min/2, move_max/2)
            end_y = random.uniform(move_min/2, move_max/2)
            
        elif animation_type == 'pan_up':
            # 向上平移
            scale = random.uniform(scale_min + 0.2, scale_max - 0.2)
            start_scale = end_scale = scale
            start_x = end_x = random.uniform(move_min/2, move_max/2)
            start_y = random.uniform(move_max/2, move_max)
            end_y = random.uniform(move_min, move_min/2)
            
        elif animation_type == 'pan_down':
            # 向下平移
            scale = random.uniform(scale_min + 0.2, scale_max - 0.2)
            start_scale = end_scale = scale
            start_x = end_x = random.uniform(move_min/2, move_max/2)
            start_y = random.uniform(move_min, move_min/2)
            end_y = random.uniform(move_max/2, move_max)
            
        else:  # zoom_pan
            # 缩放加平移
            start_scale = random.uniform(scale_min, scale_min + 0.4)
            end_scale = random.uniform(scale_max - 0.4, scale_max)
            start_x = random.uniform(move_min, 0)
            start_y = random.uniform(move_min, 0)
            end_x = random.uniform(0, move_max)
            end_y = random.uniform(0, move_max)
        
        # 创建起始关键帧
        start_keyframe = CommonKeyframe(
            id=self._gen_uuid(),
            time_offset=0,
            values={
                "scale": start_scale,
                "position_x": start_x,
                "position_y": start_y,
                "rotation": 0
            }
        )
        keyframes.append(start_keyframe)
        
        # 创建结束关键帧
        end_keyframe = CommonKeyframe(
            id=self._gen_uuid(),
            time_offset=duration_us,
            values={
                "scale": end_scale,
                "position_x": end_x,
                "position_y": end_y,
                "rotation": 0
            }
        )
        keyframes.append(end_keyframe)
        
        return keyframes
    
    def _create_subtitle_track(self, srt_path: str, total_duration_us: int) -> Optional[Track]:
        """创建字幕轨道"""
        # TODO: 实现字幕轨道创建
        # 这需要解析SRT文件并创建对应的文本段落
        return None
    
    def _merge_audio_segments(
        self,
        audio_segments: List[AudioSegmentInfo],
        output_dir: Path
    ) -> str:
        """合并音频片段"""
        logger.info("开始合并音频片段...")
        
        combined = AudioSegment.empty()
        
        for segment in audio_segments:
            audio = AudioSegment.from_file(segment.audio_file)
            combined += audio
            
            # 添加间隔
            if self.config.audio_gap_ms > 0:
                silence = AudioSegment.silent(duration=self.config.audio_gap_ms)
                combined += silence
        
        # 导出合并音频
        output_path = output_dir / "merged_audio.mp3"
        combined.export(output_path, format="mp3")
        
        logger.info(f"音频合并完成: {output_path}")
        return str(output_path)
    
    def _get_audio_duration_ms(self, audio_path: str) -> int:
        """获取音频时长（毫秒）"""
        audio = AudioSegment.from_file(audio_path)
        return len(audio)
    
    def _gen_uuid(self) -> str:
        """生成大写UUID"""
        return str(uuid.uuid4()).upper().replace('-', '')


def create_audio_segments_from_narration(
    narration_segments: list,
    base_audio_dir: str = "output/audio"
) -> List[AudioSegmentInfo]:
    """
    从解说片段创建音频片段信息
    
    Args:
        narration_segments: 解说片段列表（来自comic_pipeline）
        base_audio_dir: 音频文件基础目录
        
    Returns:
        音频片段信息列表
    """
    audio_segments = []
    current_time = 0.0
    
    for i, segment in enumerate(narration_segments):
        audio_info = AudioSegmentInfo(
            index=i,
            audio_file=segment.audio_file or f"{base_audio_dir}/narration_{i+1:03d}.mp3",
            duration=segment.duration,
            start_time=current_time,
            end_time=current_time + segment.duration,
            image_file=segment.image.path,
            narration_text=segment.text
        )
        audio_segments.append(audio_info)
        current_time += segment.duration
    
    return audio_segments


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description="漫画剪映草稿生成器")
    parser.add_argument("--audio-dir", required=True, help="音频文件目录")
    parser.add_argument("--image-dir", required=True, help="图片文件目录")
    parser.add_argument("--output-dir", default="output/drafts", help="输出目录")
    parser.add_argument("--project-name", default="comic_test", help="项目名称")
    
    args = parser.parse_args()
    
    # 创建测试数据
    audio_segments = []
    audio_files = sorted(Path(args.audio_dir).glob("*.mp3"))
    image_files = sorted(Path(args.image_dir).glob("*.jpg"))
    
    current_time = 0.0
    for i, (audio, image) in enumerate(zip(audio_files, image_files)):
        audio_obj = AudioSegment.from_file(audio)
        duration = len(audio_obj) / 1000.0  # 转换为秒
        
        segment = AudioSegmentInfo(
            index=i,
            audio_file=str(audio),
            duration=duration,
            start_time=current_time,
            end_time=current_time + duration,
            image_file=str(image),
            narration_text=f"测试片段 {i+1}"
        )
        audio_segments.append(segment)
        current_time += duration
    
    # 生成草稿
    generator = ComicDraftGenerator()
    draft_path = generator.generate_comic_draft(
        audio_segments=audio_segments,
        output_dir=args.output_dir,
        project_name=args.project_name
    )
    
    print(f"草稿生成完成: {draft_path}")