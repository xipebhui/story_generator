#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文本处理工具类
用于处理结构化文本的解析和生成
"""

import re
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)

class TextProcessor:
    """处理结构化文本的工具类"""
    
    SECTION_DIVIDER = "=" * 50
    
    @staticmethod
    def create_section(title: str, content: str) -> str:
        """
        创建带分隔符的文本段
        
        Args:
            title: 段落标题
            content: 段落内容
            
        Returns:
            格式化的文本段
        """
        return f"{TextProcessor.SECTION_DIVIDER}\n{title}\n{TextProcessor.SECTION_DIVIDER}\n{content}\n"
    
    @staticmethod
    def extract_section(text: str, section_name: str) -> Optional[str]:
        """
        从文本中提取指定部分
        
        Args:
            text: 完整文本
            section_name: 要提取的部分名称
            
        Returns:
            提取的内容，如果未找到返回None
        """
        # 构建开始标记
        start_marker = f"{TextProcessor.SECTION_DIVIDER}\n{section_name}\n{TextProcessor.SECTION_DIVIDER}"
        
        if start_marker not in text:
            return None
        
        # 找到开始位置
        start_idx = text.find(start_marker) + len(start_marker)
        
        # 找下一个分隔符或文本结尾
        next_divider_idx = text.find(TextProcessor.SECTION_DIVIDER, start_idx)
        
        if next_divider_idx == -1:
            # 没有找到下一个分隔符，提取到文本结尾
            return text[start_idx:].strip()
        else:
            # 提取到下一个分隔符之前
            return text[start_idx:next_divider_idx].strip()
    
    @staticmethod
    def parse_story_dna(dna_text: str) -> Dict[str, Any]:
        """
        解析故事DNA文本
        
        Args:
            dna_text: DNA文本内容
            
        Returns:
            解析后的字典
        """
        result = {}
        
        # 提取文本分析部分 (English: Text Analysis)
        text_analysis = TextProcessor.extract_section(dna_text, "Text Analysis")
        if text_analysis:
            analysis = {}
            for line in text_analysis.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    analysis[key.strip()] = value.strip()
            result['text_analysis'] = analysis
        
        # 提取故事DNA部分 (English: Story DNA)
        story_dna = TextProcessor.extract_section(dna_text, "Story DNA")
        if story_dna:
            result['story_dna'] = story_dna
        
        return result
    
    @staticmethod
    def parse_framework_segments(framework_text: str) -> List[Dict[str, Any]]:
        """
        解析30个片段的框架规划
        
        Args:
            framework_text: 框架文本
            
        Returns:
            片段列表
        """
        segments = []
        
        # 使用正则表达式提取片段信息
        # 匹配模式：Segment N: Title (X words)
        pattern = r"Segment (\d+): (.+?) \((\d+) words\)"
        matches = re.findall(pattern, framework_text)
        
        for match in matches:
            segment_id = int(match[0])
            title = match[1].strip()
            length = int(match[2])
            
            # 提取该片段的详细信息
            segment_pattern = rf"Segment {segment_id}: {re.escape(title)} \({length} words\)\n- Content: (.+?)\n- Focus: (.+?)\n- Connection: (.+?)(?:\n|$)"
            detail_match = re.search(segment_pattern, framework_text, re.DOTALL)
            
            if detail_match:
                segments.append({
                    "id": segment_id,
                    "title": title,
                    "length": length,
                    "content": detail_match.group(1).strip(),
                    "focus": detail_match.group(2).strip(),
                    "connection": detail_match.group(3).strip()
                })
            else:
                # 如果没有找到详细信息，只添加基本信息
                segments.append({
                    "id": segment_id,
                    "title": title,
                    "length": length
                })
        
        return segments
    
    @staticmethod
    def parse_chapter_structure(framework_text: str) -> Dict[str, List[int]]:
        """
        解析章节结构
        
        Args:
            framework_text: 框架文本
            
        Returns:
            章节到片段ID的映射
        """
        chapters = {}
        
        # 匹配章节标题 - English format
        # 【Chapter One: Beginning】(Segments 1-4, Total 3,100 words)
        chapter_pattern = r"【Chapter (.+?): (.+?)】\(Segments (\d+)-(\d+), Total [\d,]+ words\)"
        matches = re.findall(chapter_pattern, framework_text)
        
        for match in matches:
            chapter_num = match[0]  # One, Two, Three, etc.
            chapter_name = match[1]  # Beginning, Development, etc.
            start_segment = int(match[2])
            end_segment = int(match[3])
            
            chapters[chapter_name] = list(range(start_segment, end_segment + 1))
        
        return chapters
    
    @staticmethod
    def build_segment_input(
        segment_number: int,
        segment_info: Dict[str, Any],
        previous_segment: Optional[str] = None
    ) -> str:
        """
        构建片段生成的输入文本
        
        Args:
            segment_number: 片段编号
            segment_info: 片段信息
            previous_segment: 上一段内容
            
        Returns:
            格式化的输入文本
        """
        sections = []
        
        # Current Task
        task_content = f"""Segment Number: {segment_number} of 30
Segment Title: {segment_info.get('title', '')}
Chapter: {segment_info.get('chapter', '')}
Target Length: {segment_info.get('length', 1000)} words
Content Focus: {segment_info.get('focus', '')}"""
        sections.append(TextProcessor.create_section("Current Task", task_content))
        
        # Previous Segment
        if previous_segment:
            sections.append(TextProcessor.create_section("Previous Segment", previous_segment))
        else:
            sections.append(TextProcessor.create_section("Previous Segment", "[Segment 1, no previous content]"))
        
        # Segment Plan
        plan_content = f"""- Content: {segment_info.get('content', '')}
- Focus: {segment_info.get('focus', '')}
- Connection: {segment_info.get('connection', '')}"""
        sections.append(TextProcessor.create_section("Segment Plan (from framework)", plan_content))
        
        # Continuation Requirements
        requirements = f"""Based on global directives (Story DNA and complete framework), continue with segment {segment_number}.
Ensure:
1. Natural connection with previous segment
2. Complete this segment's focus task
3. Word count within ±10% of {segment_info.get('length', 1000)} words
4. Reserve development space for next segment
5. **WRITE IN ENGLISH**"""
        sections.append(TextProcessor.create_section("Continuation Requirements", requirements))
        
        return ''.join(sections)
    
    @staticmethod
    def extract_segments_from_full_story(story_text: str) -> List[str]:
        """
        从完整故事中提取各个片段
        
        Args:
            story_text: 完整故事文本
            
        Returns:
            片段列表
        """
        # 如果故事中有明确的片段分隔符
        if "片段" in story_text:
            segments = []
            pattern = r"片段\d+[：:].+?\n(.*?)(?=片段\d+[：:]|$)"
            matches = re.findall(pattern, story_text, re.DOTALL)
            for match in matches:
                segments.append(match.strip())
            return segments
        
        # 否则按段落分割（简单处理）
        paragraphs = story_text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def merge_segments(segments: List[str]) -> str:
        """
        合并片段成完整故事
        
        Args:
            segments: 片段列表
            
        Returns:
            完整故事文本
        """
        # 简单地用双换行连接各片段
        return '\n\n'.join(segments)
    
    @staticmethod
    def format_polish_input(framework: str, draft: str) -> str:
        """
        格式化润色阶段的输入
        
        Args:
            framework: 改编框架
            draft: 故事草稿
            
        Returns:
            格式化的输入文本
        """
        sections = []
        
        sections.append(TextProcessor.create_section("Adaptation Framework", framework))
        sections.append(TextProcessor.create_section("Story Draft (30 segments concatenated)", draft))
        
        requirements = """- Target Length: 30,000 words (approximately 30 minutes reading)
- Key Optimizations:
  * Smooth transitions between segments
  * Unify language style throughout
  * Enhance emotional impact at key moments
  * Ensure rhythm variation
- Special Attention:
  * Check character consistency
  * Ensure plot logic coherence
  * Optimize dialogue naturalness
- **OUTPUT IN ENGLISH**"""
        sections.append(TextProcessor.create_section("Polish Requirements", requirements))
        
        return ''.join(sections)
    
    @staticmethod
    def parse_polish_output(polish_text: str) -> Dict[str, str]:
        """
        解析润色输出
        
        Args:
            polish_text: 润色输出文本
            
        Returns:
            包含报告和润色后文本的字典
        """
        result = {}
        
        # 提取编辑报告 (English: Editorial Report)
        report = TextProcessor.extract_section(polish_text, "Editorial Report")
        if report:
            result['report'] = report
        
        # 提取润色后全文 (English: Polished Full Text)
        polished_story = TextProcessor.extract_section(polish_text, "Polished Full Text")
        if polished_story:
            result['story'] = polished_story
        
        return result