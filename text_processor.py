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
        解析框架中的片段规划（支持旧的30片段格式和新的9步格式）

        Args:
            framework_text: 框架文本

        Returns:
            片段列表
        """
        segments = []

        # 首先尝试旧格式：Segment N: Title (X words)
        pattern = r"Segment (\d+): (.+?) \((\d+) words\)"
        matches = re.findall(pattern, framework_text)

        if matches:
            # 旧格式解析
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
        else:
            # 新的9步格式解析
            # 匹配模式：**N. 步骤名称 (英文)：**
            pattern = r'\*\*(\d+)\.\s+([^(]+)\s*\([^)]+\)：\*\*([^*]*?)(?=\*\*\d+\.|$)'
            matches = re.findall(pattern, framework_text, re.DOTALL)

            for i, (step_num, step_name, content) in enumerate(matches, 1):
                step_name = step_name.strip()
                segment_info = {
                    "id": i,
                    "title": step_name,
                    "chapter": step_name
                }

                # 提取情节规划
                plot_match = re.search(r'\*\*情节规划：\*\*\s*([^\n]+(?:\n(?!\s*-\s*\*\*)[^\n]+)*)', content)
                if plot_match:
                    segment_info["content"] = plot_match.group(1).strip()
                    segment_info["focus"] = f"{step_name}的核心内容"

                # 提取节奏与字数
                rhythm_match = re.search(r'\*\*节奏与字数：\*\*\s*([^\n]+)', content)
                if rhythm_match:
                    rhythm_text = rhythm_match.group(1).strip()
                    segment_info["rhythm"] = rhythm_text

                    # 提取具体字数范围
                    word_count_match = re.search(r'(\d+)[-–](\d+)\s*字', rhythm_text)
                    if word_count_match:
                        min_words = int(word_count_match.group(1))
                        max_words = int(word_count_match.group(2))
                        segment_info["length"] = (min_words + max_words) // 2  # 取中间值作为目标
                        segment_info["word_range"] = (min_words, max_words)
                    else:
                        # 如果没有具体字数，使用默认值
                        segment_info["length"] = 2500  # 默认值

                # 设置连接说明
                if i > 1:
                    segment_info["connection"] = f"自然衔接前一部分，继续推进{step_name}"
                else:
                    segment_info["connection"] = "故事开端，快速吸引读者"

                segments.append(segment_info)

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

        # 确定字数要求
        if 'word_range' in segment_info:
            min_words, max_words = segment_info['word_range']
            word_requirement = f"严格控制在 {min_words}-{max_words} 字"
            target_length = (min_words + max_words) // 2
        else:
            target_length = segment_info.get('length', 1000)
            word_requirement = f"目标字数约 {target_length} 字"

        # Current Task
        task_content = f"""Segment Number: {segment_number} of 30
Segment Title: {segment_info.get('title', '')}
Chapter: {segment_info.get('chapter', '')}
Target Length: {target_length} words
Word Requirement: {word_requirement}
Content Focus: {segment_info.get('focus', '')}"""

        # 如果有节奏信息，添加进去
        if 'rhythm' in segment_info:
            task_content += f"\nRhythm Guidance: {segment_info['rhythm']}"

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
        if 'word_range' in segment_info:
            min_words, max_words = segment_info['word_range']
            word_count_requirement = f"Word count must be strictly within {min_words}-{max_words} words"
        else:
            word_count_requirement = f"Word count within ±10% of {target_length} words"

        requirements = f"""Based on global directives (Story DNA and complete framework), continue with segment {segment_number}.
Ensure:
1. Natural connection with previous segment
2. Complete this segment's focus task
3. {word_count_requirement}
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
    def format_polish_input(framework: str, draft: str, num_segments: int = 9) -> str:
        """
        格式化润色阶段的输入

        Args:
            framework: 改编框架
            draft: 故事草稿
            num_segments: 片段数量（默认9个）

        Returns:
            格式化的输入文本
        """
        sections = []

        sections.append(TextProcessor.create_section("Adaptation Framework", framework))

        # 计算草稿字数
        draft_word_count = len(draft)
        sections.append(TextProcessor.create_section(
            f"Story Draft ({num_segments} segments concatenated, {draft_word_count} words)", draft))

        requirements = f"""- Target Length: 30,000 words (approximately 30 minutes reading)
- Current Draft Length: {draft_word_count} words
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