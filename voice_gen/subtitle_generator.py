#!/usr/bin/env python3
"""
本地字幕生成器 - 根据文本内容生成SRT格式字幕
当TTS服务不返回字幕时，使用此模块生成字幕
"""

import re
from typing import List, Tuple, Optional
from datetime import timedelta

class SubtitleGenerator:
    """字幕生成器"""
    
    def __init__(self, words_per_minute: int = 150):
        """
        初始化字幕生成器
        
        Args:
            words_per_minute: 平均语速（每分钟单词数）
        """
        self.words_per_minute = words_per_minute
        self.words_per_second = words_per_minute / 60.0
    
    def estimate_duration(self, text: str) -> float:
        """
        估算文本朗读时长（秒）
        
        Args:
            text: 文本内容
            
        Returns:
            估算的时长（秒）
        """
        # 统计单词数
        words = len(text.split())
        
        # 基于语速计算时长
        duration = words / self.words_per_second
        
        # 添加停顿时间（句号0.5秒，逗号0.2秒）
        periods = text.count('.') + text.count('!') + text.count('?')
        commas = text.count(',') + text.count(';') + text.count(':')
        
        duration += periods * 0.5 + commas * 0.2
        
        # 最小时长1秒
        return max(1.0, duration)
    
    def split_into_subtitles(self, text: str, max_chars: int = 80, max_duration: float = 5.0) -> List[str]:
        """
        将文本分割成字幕片段
        
        Args:
            text: 原始文本
            max_chars: 每个字幕的最大字符数
            max_duration: 每个字幕的最大时长（秒）
            
        Returns:
            字幕片段列表
        """
        # 先按句子分割
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        subtitles = []
        current_subtitle = ""
        
        for sentence in sentences:
            # 如果句子本身太长，需要进一步分割
            if len(sentence) > max_chars:
                # 按逗号或分号分割
                parts = re.split(r'[,;]\s*', sentence)
                for part in parts:
                    if len(part) > max_chars:
                        # 如果还是太长，强制分割
                        words = part.split()
                        temp = ""
                        for word in words:
                            if len(temp) + len(word) + 1 <= max_chars:
                                temp = f"{temp} {word}" if temp else word
                            else:
                                if temp:
                                    subtitles.append(temp)
                                temp = word
                        if temp:
                            subtitles.append(temp)
                    else:
                        # 检查是否可以合并到当前字幕
                        if current_subtitle and len(current_subtitle) + len(part) + 1 <= max_chars:
                            current_subtitle = f"{current_subtitle}, {part}"
                        else:
                            if current_subtitle:
                                subtitles.append(current_subtitle)
                            current_subtitle = part
            else:
                # 检查是否可以合并到当前字幕
                if current_subtitle and len(current_subtitle) + len(sentence) + 1 <= max_chars:
                    current_subtitle = f"{current_subtitle} {sentence}"
                else:
                    if current_subtitle:
                        subtitles.append(current_subtitle)
                    current_subtitle = sentence
        
        # 添加最后的字幕
        if current_subtitle:
            subtitles.append(current_subtitle)
        
        return subtitles
    
    def format_time(self, seconds: float) -> str:
        """
        将秒数格式化为SRT时间格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT时间格式字符串 (HH:MM:SS,mmm)
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def generate_srt(self, text: str, start_time: float = 0.0) -> str:
        """
        生成SRT格式字幕
        
        Args:
            text: 文本内容
            start_time: 开始时间（秒）
            
        Returns:
            SRT格式的字幕字符串
        """
        # 分割文本为字幕片段
        subtitles = self.split_into_subtitles(text)
        
        srt_content = []
        current_time = start_time
        
        for i, subtitle in enumerate(subtitles, 1):
            # 估算此字幕的时长
            duration = self.estimate_duration(subtitle)
            
            # 格式化时间
            start_str = self.format_time(current_time)
            end_str = self.format_time(current_time + duration)
            
            # 添加SRT条目
            srt_content.append(f"{i}")
            srt_content.append(f"{start_str} --> {end_str}")
            srt_content.append(subtitle)
            srt_content.append("")  # 空行分隔
            
            current_time += duration
        
        return "\n".join(srt_content)
    
    def generate_srt_for_segments(self, segments: List[Tuple[str, float]], gap: float = 0.1) -> str:
        """
        为多个文本段落生成SRT字幕
        
        Args:
            segments: [(文本, 实际时长), ...] 的列表
            gap: 段落之间的间隔（秒）
            
        Returns:
            完整的SRT格式字幕字符串
        """
        srt_parts = []
        current_time = 0.0
        subtitle_index = 1
        
        for text, actual_duration in segments:
            if not text.strip():
                current_time += actual_duration + gap
                continue
            
            # 分割文本为字幕片段
            subtitles = self.split_into_subtitles(text)
            
            if not subtitles:
                current_time += actual_duration + gap
                continue
            
            # 计算每个字幕的时长
            total_estimated = sum(self.estimate_duration(s) for s in subtitles)
            
            # 调整时长以匹配实际音频时长
            if total_estimated > 0:
                scale_factor = actual_duration / total_estimated
            else:
                scale_factor = 1.0
            
            # 生成字幕
            for subtitle in subtitles:
                # 调整后的时长
                duration = self.estimate_duration(subtitle) * scale_factor
                
                # 格式化时间
                start_str = self.format_time(current_time)
                end_str = self.format_time(current_time + duration)
                
                # 添加SRT条目
                srt_parts.append(f"{subtitle_index}")
                srt_parts.append(f"{start_str} --> {end_str}")
                srt_parts.append(subtitle)
                srt_parts.append("")  # 空行分隔
                
                subtitle_index += 1
                current_time += duration
            
            # 添加段落间隔
            current_time += gap
        
        return "\n".join(srt_parts)


# 单例实例
_generator = None

def get_subtitle_generator() -> SubtitleGenerator:
    """获取字幕生成器实例（单例）"""
    global _generator
    if _generator is None:
        _generator = SubtitleGenerator()
    return _generator


if __name__ == "__main__":
    # 测试代码
    generator = SubtitleGenerator()
    
    # 测试文本
    test_text = """
    Once upon a time, in a small village nestled between rolling hills, 
    there lived a young girl named Alice. She had always been curious about 
    the mysterious forest that bordered her village. One day, she decided to 
    explore it, despite the warnings from the elders.
    """
    
    print("测试字幕生成")
    print("=" * 60)
    print("原始文本:")
    print(test_text)
    print("\n生成的SRT字幕:")
    print("=" * 60)
    
    srt = generator.generate_srt(test_text)
    print(srt)
    
    # 测试多段落
    print("\n测试多段落字幕生成")
    print("=" * 60)
    
    segments = [
        ("Hello, this is the first segment.", 3.5),
        ("And this is the second segment with more text.", 5.2),
        ("Finally, the third segment completes our test.", 4.8)
    ]
    
    srt_multi = generator.generate_srt_for_segments(segments)
    print(srt_multi)