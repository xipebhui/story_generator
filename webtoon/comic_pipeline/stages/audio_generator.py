#!/usr/bin/env python3
"""
音频生成阶段
"""

import os
import asyncio
from typing import List, Optional, Tuple
from pathlib import Path
import logging
import edge_tts
from pydub import AudioSegment

from ..models import NarrationSegment, ComicImage
from ..config import ComicPipelineConfig

logger = logging.getLogger(__name__)


class AudioGenerator:
    """音频生成器"""
    
    def __init__(self, config: ComicPipelineConfig):
        self.config = config
        
    async def generate_single_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        生成单段音频
        
        Returns:
            (音频文件路径, 时长秒数)
        """
        logger.info(f"生成音频: {len(text)}字")
        
        # 选择声音
        voice = voice or self.config.tts.voice
        
        # 创建TTS通信对象
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=self.config.tts.rate,
            pitch=self.config.tts.pitch,
            volume=self.config.tts.volume
        )
        
        # 生成音频和字幕
        subtitle_path = output_path.replace('.mp3', '.vtt')
        await communicate.save(output_path)
        
        # 获取音频时长
        duration = self._get_audio_duration(output_path)
        
        logger.info(f"音频生成完成: {Path(output_path).name} ({duration:.2f}秒)")
        
        return output_path, duration
    
    def generate_single_audio_sync(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> Tuple[str, float]:
        """同步版本的音频生成"""
        return asyncio.run(self.generate_single_audio(text, output_path, voice))
    
    async def generate_batch_audio(
        self,
        texts: List[str],
        output_dir: str,
        prefix: str = "segment"
    ) -> List[Tuple[str, float]]:
        """
        批量生成音频（每段独立）
        
        Returns:
            [(音频文件路径, 时长), ...]
        """
        logger.info(f"批量生成 {len(texts)} 段音频")
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        results = []
        for i, text in enumerate(texts):
            output_path = os.path.join(output_dir, f"{prefix}_{i:03d}.mp3")
            
            # 检查缓存
            if self.config.pipeline.cache_enabled and os.path.exists(output_path):
                duration = self._get_audio_duration(output_path)
                logger.info(f"使用缓存音频: {Path(output_path).name}")
                results.append((output_path, duration))
                continue
            
            # 生成新音频
            audio_path, duration = await self.generate_single_audio(
                text=text,
                output_path=output_path
            )
            results.append((audio_path, duration))
            
            # 短暂延迟，避免请求过快
            await asyncio.sleep(0.5)
        
        return results
    
    def generate_batch_audio_sync(
        self,
        texts: List[str],
        output_dir: str,
        prefix: str = "segment"
    ) -> List[Tuple[str, float]]:
        """同步版本的批量音频生成"""
        return asyncio.run(self.generate_batch_audio(texts, output_dir, prefix))
    
    def merge_audio_files(
        self,
        audio_files: List[str],
        output_path: str,
        gap_ms: int = 500
    ) -> str:
        """
        合并多个音频文件
        
        Args:
            audio_files: 音频文件路径列表
            output_path: 输出文件路径
            gap_ms: 音频间隔（毫秒）
            
        Returns:
            合并后的音频文件路径
        """
        logger.info(f"合并 {len(audio_files)} 个音频文件")
        
        # 创建静音间隔
        silence = AudioSegment.silent(duration=gap_ms)
        
        # 合并音频
        combined = AudioSegment.empty()
        for i, audio_file in enumerate(audio_files):
            audio = AudioSegment.from_mp3(audio_file)
            combined += audio
            
            # 添加间隔（最后一个不加）
            if i < len(audio_files) - 1:
                combined += silence
        
        # 导出合并后的音频
        combined.export(output_path, format="mp3")
        
        total_duration = len(combined) / 1000.0  # 转换为秒
        logger.info(f"音频合并完成: {Path(output_path).name} ({total_duration:.2f}秒)")
        
        return output_path
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0
    
    def create_segments_with_audio(
        self,
        images: List[ComicImage],
        narrations: List[str],
        audio_results: List[Tuple[str, float]]
    ) -> List[NarrationSegment]:
        """
        创建包含音频信息的片段列表
        
        Args:
            images: 图片列表
            narrations: 文案列表
            audio_results: [(音频路径, 时长), ...]
            
        Returns:
            NarrationSegment列表
        """
        segments = []
        current_time = 0.0
        
        for i, (image, narration, (audio_path, duration)) in enumerate(
            zip(images, narrations, audio_results)
        ):
            segment = NarrationSegment(
                image=image,
                text=narration,
                duration=duration,
                audio_file=audio_path,
                start_time=current_time,
                end_time=current_time + duration,
                word_count=len(narration)
            )
            segments.append(segment)
            current_time += duration
        
        logger.info(f"创建了 {len(segments)} 个片段，总时长 {current_time:.2f}秒")
        
        return segments
    
    def adjust_audio_speed(
        self,
        audio_path: str,
        target_duration: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        调整音频速度以匹配目标时长
        
        Args:
            audio_path: 原音频路径
            target_duration: 目标时长（秒）
            output_path: 输出路径（可选）
            
        Returns:
            调整后的音频路径
        """
        audio = AudioSegment.from_mp3(audio_path)
        current_duration = len(audio) / 1000.0
        
        # 计算速度因子
        speed_factor = current_duration / target_duration
        
        # 限制速度调整范围（0.8x - 1.2x）
        speed_factor = max(0.8, min(1.2, speed_factor))
        
        # 调整速度
        if speed_factor != 1.0:
            # 使用frame_rate调整速度
            audio = audio._spawn(
                audio.raw_data,
                overrides={
                    "frame_rate": int(audio.frame_rate * speed_factor)
                }
            ).set_frame_rate(audio.frame_rate)
        
        # 保存
        if not output_path:
            output_path = audio_path.replace('.mp3', '_adjusted.mp3')
        
        audio.export(output_path, format="mp3")
        
        return output_path