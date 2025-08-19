#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
具体的Pipeline步骤实现
每个步骤都是独立的，可以灵活组合
"""

from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from pipeline_architecture import (
    PipelineStep, PipelineContext, StepResult,
    ProcessingStrategy, PromptFormattingStrategy
)
from youtube_client import YouTubeAPIClient
from gemini_client import GeminiClient
from text_processor import TextProcessor

logger = logging.getLogger(__name__)


# ============= 数据获取步骤 =============

class FetchYouTubeDataStep(PipelineStep):
    """获取YouTube数据的步骤"""
    
    def __init__(self, youtube_client: YouTubeAPIClient):
        super().__init__("fetch_youtube_data")
        self.youtube_client = youtube_client
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行数据获取"""
        try:
            # 检查缓存
            cached_data = self.load_cache(context)
            if cached_data:
                context.update(
                    video_info=cached_data.get('video_info', {}),
                    comments=cached_data.get('comments', []),
                    subtitles=cached_data.get('subtitles', '')
                )
                return StepResult(success=True, data=cached_data)
            
            # 获取视频信息
            video_details = self.youtube_client.get_video_details([context.video_id])
            if video_details and video_details.get('items'):
                video_info = video_details['items'][0]
                context.video_info = {
                    'title': video_info['snippet']['title'],
                    'description': video_info['snippet']['description'],
                    'channel_title': video_info['snippet']['channelTitle']
                }
            
            # 获取评论
            comments_data = self.youtube_client.get_video_comments(
                context.video_id, max_results=5
            )
            if comments_data and comments_data.get('items'):
                comments = []
                for item in comments_data['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'text': snippet['textDisplay'],
                        'likes': snippet['likeCount'],
                        'author': snippet['authorDisplayName']
                    })
                context.comments = sorted(
                    comments, key=lambda x: x['likes'], reverse=True
                )[:5]
            
            # 获取字幕
            result = self.youtube_client.get_video_transcript(context.video_id)
            if result:
                _, subtitle_text = result
                context.subtitles = subtitle_text
            
            # 保存缓存
            data = {
                'video_info': context.video_info,
                'comments': context.comments,
                'subtitles': context.subtitles
            }
            self.save_cache(context, data)
            
            return StepResult(success=True, data=data)
            
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return bool(context.video_id)


# ============= DNA提取步骤 =============

class ExtractDNAStep(PipelineStep):
    """提取故事DNA的步骤"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("extract_dna")
        self.gemini_client = gemini_client
        self.text_processor = TextProcessor()
        self.formatting_strategy = PromptFormattingStrategy("structured")
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行DNA提取"""
        try:
            # 检查缓存
            cached_dna = self.load_cache(context)
            if cached_dna:
                context.story_dna = cached_dna.get('dna', '')
                context.metadata['text_analysis'] = cached_dna.get('analysis', {})
                return StepResult(success=True, data=cached_dna)
            
            # 获取提示词模板
            if not self.prompt_manager:
                return StepResult(success=False, error="Prompt manager not set")
            
            # 构建提示词输入
            prompt_input = self.prompt_manager.get_prompt(
                'dna_extractor',
                story_text=context.subtitles
            )
            
            # 调用AI
            response = self.gemini_client.generate_content(prompt_input)
            
            if response:
                # 解析响应
                dna_data = self.text_processor.parse_story_dna(response)
                
                context.story_dna = response
                context.metadata['text_analysis'] = dna_data.get('text_analysis', {})
                
                # 保存缓存
                cache_data = {
                    'dna': response,
                    'analysis': dna_data.get('text_analysis', {})
                }
                self.save_cache(context, cache_data)
                
                return StepResult(success=True, data=dna_data)
            else:
                return StepResult(success=False, error="Empty AI response")
                
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return bool(context.subtitles)


# ============= 框架生成步骤 =============

class GenerateFrameworkStep(PipelineStep):
    """生成故事框架的步骤"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_framework")
        self.gemini_client = gemini_client
        self.formatting_strategy = PromptFormattingStrategy("structured")
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行框架生成"""
        try:
            # 检查缓存
            cached_framework = self.load_cache(context)
            if cached_framework:
                context.framework = cached_framework.get('framework', '')
                return StepResult(success=True, data=cached_framework)
            
            # 准备输入数据
            top_comments = [c['text'] for c in context.comments[:5]]
            original_word_count = len(context.story_dna) if context.story_dna else 5000
            
            # 使用策略格式化输入
            formatted_input = self.formatting_strategy.process(
                context.story_dna,
                sections={
                    "原始故事DNA与元数据": f"""
- **原故事参考字数：** {original_word_count}
- **原始标题：** {context.video_info.get('title', 'N/A')}
- **热门评论（核心槽点来源）：**
{chr(10).join([f'  - {comment}' for comment in top_comments])}
- **故事DNA：**
{context.story_dna}
"""
                }
            )
            
            # 获取提示词并合并
            prompt = self.prompt_manager.get_prompt('framework_generator')
            full_prompt = f"{prompt}\n\n---\n\n{formatted_input}"
            
            # 调用AI
            response = self.gemini_client.generate_content(full_prompt)
            
            if response:
                context.framework = response
                
                # 保存缓存
                self.save_cache(context, {'framework': response})
                
                return StepResult(success=True, data={'framework': response})
            else:
                return StepResult(success=False, error="Empty AI response")
                
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return bool(context.story_dna) and bool(context.video_info)


# ============= 片段生成步骤 =============

class GenerateSegmentsStep(PipelineStep):
    """生成故事片段的步骤"""
    
    def __init__(self, gemini_client: GeminiClient, 
                 generation_strategy: str = "simple"):
        super().__init__("generate_segments")
        self.gemini_client = gemini_client
        self.text_processor = TextProcessor()
        self.generation_strategy = generation_strategy
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行片段生成"""
        try:
            segments = []
            
            # 解析框架信息
            framework_info = self._parse_framework(context.framework)
            
            # 逐个生成片段
            for i in range(1, context.num_segments + 1):
                segment = self._generate_segment(
                    context, i, framework_info, segments
                )
                if segment:
                    segments.append(segment)
                else:
                    logger.error(f"Failed to generate segment {i}")
            
            context.segments = segments
            
            return StepResult(
                success=len(segments) == context.num_segments,
                data={'segments': segments}
            )
            
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def _generate_segment(self, context: PipelineContext, 
                         segment_num: int, 
                         framework_info: Dict,
                         previous_segments: List[str]) -> Optional[str]:
        """生成单个片段"""
        try:
            # 检查缓存
            cache_key = f"segment_{segment_num:02d}"
            if context.cache_dir:
                cache_file = context.cache_dir / "segments" / f"{cache_key}.txt"
                if cache_file.exists():
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
            
            # 准备输入
            segment_input = self._build_segment_input(
                context, segment_num, framework_info, previous_segments
            )
            
            # 调用AI生成
            response = self.gemini_client.generate_content(segment_input)
            
            if response:
                # 保存缓存
                if context.cache_dir:
                    cache_file = context.cache_dir / "segments" / f"{cache_key}.txt"
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(response)
                
                return response
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating segment {segment_num}: {e}")
            return None
    
    def _build_segment_input(self, context: PipelineContext,
                            segment_num: int,
                            framework_info: Dict,
                            previous_segments: List[str]) -> str:
        """构建片段生成的输入"""
        # 获取片段提示词模板
        segment_prompt = self.prompt_manager.get_prompt('segment_generator')
        
        # 获取前文内容
        previous_text = ""
        if previous_segments:
            previous_text = previous_segments[-1][-500:]  # 最后500字
        
        # 获取当前片段任务
        segment_task = framework_info.get('segments', {}).get(
            segment_num, 
            {'task': f'Generate segment {segment_num}'}
        )
        
        # 格式化输入
        formatted_input = f"""{segment_prompt}

==================================================
**最高指令：故事改编框架 V2.1 (摘要)**
==================================================
{framework_info.get('summary', '')}

==================================================
**前一段内容 (Previous Segment)**
==================================================
{previous_text if previous_text else "**This is the first segment.**"}

==================================================
**本段任务卡 (Current Segment Task Card)**
==================================================
- **段落编号：** 第 {segment_num} 段
- **任务：** {segment_task.get('task', '')}
- **字数要求：** {segment_task.get('word_count', '约1000字')}
"""
        
        return formatted_input
    
    def _parse_framework(self, framework: str) -> Dict:
        """解析框架信息"""
        # 这里简化处理，实际应该有更复杂的解析逻辑
        return {
            'summary': framework[:500],  # 取前500字作为摘要
            'segments': {}  # 实际应解析出每个片段的任务
        }
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return bool(context.framework) and bool(context.story_dna)


# ============= 润色步骤 =============

class PolishStoryStep(PipelineStep):
    """润色故事的步骤"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("polish_story")
        self.gemini_client = gemini_client
        self.text_processor = TextProcessor()
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行故事润色"""
        try:
            # 检查缓存
            cached_story = self.load_cache(context)
            if cached_story:
                context.final_story = cached_story.get('story', '')
                return StepResult(success=True, data=cached_story)
            
            # 合并片段
            draft = self.text_processor.merge_segments(context.segments)
            context.draft_story = draft
            
            # 构建润色输入
            polish_input = self.text_processor.format_polish_input(
                context.framework, 
                draft, 
                num_segments=context.num_segments
            )
            
            # 获取润色提示词
            polish_prompt = self.prompt_manager.get_prompt('final_polisher')
            full_prompt = f"{polish_prompt}\n\n---\n\n{polish_input}"
            
            # 调用AI润色
            response = self.gemini_client.generate_content(full_prompt)
            
            if response:
                # 解析输出
                polish_result = self.text_processor.parse_polish_output(response)
                final_story = polish_result.get('story', draft)
                
                context.final_story = final_story
                
                # 保存缓存
                self.save_cache(context, {'story': final_story})
                
                return StepResult(
                    success=True,
                    data={'story': final_story, 'report': polish_result.get('report', '')}
                )
            else:
                return StepResult(success=False, error="Empty AI response")
                
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return bool(context.segments) and len(context.segments) > 0


# ============= 报告生成步骤 =============

class GenerateReportStep(PipelineStep):
    """生成最终报告的步骤"""
    
    def __init__(self):
        super().__init__("generate_report")
    
    def execute(self, context: PipelineContext) -> StepResult:
        """执行报告生成"""
        try:
            report = self._generate_report(context)
            
            # 保存报告
            if context.cache_dir:
                report_file = context.cache_dir / "final" / "report.md"
                report_file.parent.mkdir(parents=True, exist_ok=True)
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
            
            return StepResult(success=True, data={'report': report})
            
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    def _generate_report(self, context: PipelineContext) -> str:
        """生成详细报告"""
        from datetime import datetime
        
        report = f"""
# YouTube故事创作报告

创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本信息
- **视频ID**：{context.video_id}
- **创作者**：{context.creator_name}
- **目标长度**：{context.target_length}字
- **片段数量**：{context.num_segments}个

## 原始数据
- **视频标题**：{context.video_info.get('title', 'N/A')}
- **频道名称**：{context.video_info.get('channel_title', 'N/A')}
- **字幕长度**：{len(context.subtitles)}字
- **评论数量**：{len(context.comments)}条

## 生成结果
- **最终故事长度**：{len(context.final_story)}字
- **实际片段数**：{len(context.segments)}个
- **平均每片段**：{len(context.final_story)//len(context.segments) if context.segments else 0}字

## 故事预览

### 开头（前200字）
```
{context.final_story[:200] if context.final_story else 'N/A'}...
```

### 结尾（后200字）
```
...{context.final_story[-200:] if context.final_story else 'N/A'}
```

---
*报告生成完毕*
"""
        return report