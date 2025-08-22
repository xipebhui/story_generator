#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pipeline Steps V3 - 新版本的Pipeline步骤实现
严格模式：任何失败都会导致Pipeline终止
"""

import json
import re
import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from pipeline_architecture import PipelineStep, StepResult
from pipeline_context_v3 import PipelineContextV3
from youtube_client import YouTubeAPIClient
from gemini_client import GeminiClient
from text_processor import TextProcessor
import traceback

logger = logging.getLogger(__name__)


# ============= 数据获取步骤 =============

class FetchYouTubeDataV3Step(PipelineStep):
    """获取YouTube数据 - V3版本"""
    
    def __init__(self, youtube_client: YouTubeAPIClient):
        super().__init__("fetch_youtube_data_v3")
        self.youtube_client = youtube_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """执行数据获取"""
        try:
            # 检查缓存
            if context.cache_dir:
                cached_data = self._load_cached_data(context)
                if cached_data:
                    context.update(**cached_data)
                    logger.info(f"✅ 从缓存加载YouTube数据")
                    return StepResult(success=True, data=cached_data)
            
            # 获取视频信息
            logger.info(f"📊 获取视频信息: {context.video_id}")
            video_details = self.youtube_client.get_video_details([context.video_id])
            if not video_details or not video_details.get('items'):
                raise Exception(f"Failed to fetch video details for {context.video_id}")
            
            video_info = video_details['items'][0]
            context.video_info = {
                'title': video_info['snippet']['title'],
                'description': video_info['snippet']['description'],
                'channel_title': video_info['snippet']['channelTitle']
            }
            
            # 获取评论
            logger.info("💬 获取热门评论")
            comments_data = self.youtube_client.get_video_comments(
                context.video_id, max_results=10
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
            
            # 获取字幕（必须成功）
            logger.info("📝 获取视频字幕")
            subtitle_path = self.youtube_client.get_video_transcript(context.video_id)
            if not subtitle_path:
                raise Exception(f"Failed to fetch transcript for {context.video_id} - TERMINATING")
            
            # 读取字幕文件内容
            import os
            absolute_path = os.path.abspath(subtitle_path)
            with open(absolute_path, 'r', encoding='utf-8') as f:
                subtitle_text = f.read()
            context.subtitles = subtitle_text
            
            # 保存缓存
            if context.save_intermediate and context.cache_dir:
                self._save_cached_data(context)
            
            logger.info(f"✅ YouTube数据获取成功")
            return StepResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to fetch YouTube data: {e}"
            logger.error(f"❌ {error_msg}")
            context.add_error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _load_cached_data(self, context: PipelineContextV3) -> Optional[Dict]:
        """加载缓存数据"""
        try:
            cache_dir = context.cache_dir / "raw"
            
            data = {}
            
            # 加载视频信息
            video_file = cache_dir / "video_info.json"
            if video_file.exists():
                with open(video_file, 'r', encoding='utf-8') as f:
                    data['video_info'] = json.load(f)
            
            # 加载评论
            comments_file = cache_dir / "comments.json"
            if comments_file.exists():
                with open(comments_file, 'r', encoding='utf-8') as f:
                    data['comments'] = json.load(f)
            
            # 加载字幕
            subtitle_file = cache_dir / "subtitle.txt"
            if subtitle_file.exists():
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    data['subtitles'] = f.read()
            
            # 只有所有必需数据都存在才返回缓存
            if data.get('subtitles'):
                return data
                
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    def _save_cached_data(self, context: PipelineContextV3):
        """保存缓存数据"""
        try:
            cache_dir = context.cache_dir / "raw"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存视频信息
            with open(cache_dir / "video_info.json", 'w', encoding='utf-8') as f:
                json.dump(context.video_info, f, ensure_ascii=False, indent=2)
            
            # 保存评论
            with open(cache_dir / "comments.json", 'w', encoding='utf-8') as f:
                json.dump(context.comments, f, ensure_ascii=False, indent=2)
            
            # 保存字幕
            with open(cache_dir / "subtitle.txt", 'w', encoding='utf-8') as f:
                f.write(context.subtitles)
                
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")


# ============= Framework V3 生成步骤 =============

class GenerateFrameworkV3Step(PipelineStep):
    """使用framework_generatorv3.md生成JSON框架"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_framework_v3")
        self.gemini_client = gemini_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """生成V3框架"""
        try:
            # 检查缓存
            if context.cache_dir:
                cached_framework = self._load_cached_framework(context)
                if cached_framework:
                    context.framework_v3_raw = cached_framework['raw']
                    context.framework_v3_json = cached_framework['json']
                    logger.info("✅ 从缓存加载Framework V3")
                    return StepResult(success=True, data=cached_framework)
            
            # 构建输入
            input_data = self._build_input(context)
            
            # 获取提示词
            if not self.prompt_manager:
                raise Exception("Prompt manager not set - TERMINATING")
            
            prompt = self.prompt_manager.get_prompt('framework_generatorv3')
            full_prompt = prompt + "\n" + input_data
            
            logger.info("🤖 调用AI生成Framework V3...")
            response = self.gemini_client.generate_content(full_prompt)
            
            if not response:
                raise Exception("Framework V3 generation failed - empty response - TERMINATING")
            
            context.framework_v3_raw = response
            
            # 解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise Exception("Failed to extract JSON from response - TERMINATING")
            
            try:
                context.framework_v3_json = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON: {e} - TERMINATING")
            
            # 验证JSON结构
            if 'storyBlueprint' not in context.framework_v3_json:
                raise Exception("Invalid JSON structure: missing storyBlueprint - TERMINATING")
            
            # 保存缓存
            if context.save_intermediate and context.cache_dir:
                self._save_cached_framework(context)
            
            logger.info(f"✅ Framework V3生成成功")
            return StepResult(success=True)
            
        except Exception as e:
            error_msg = f"Framework V3 generation failed: {e}"
            traceback.print_exc()
            logger.error(f"❌ {error_msg}")
            context.add_error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _build_input(self, context: PipelineContextV3) -> str:
        """构建输入格式"""
        comments_text = "\n".join([c['text'] for c in context.comments[:5]])
        
        return f"""[START_OF_INPUT_DATA]
Original Title
{context.video_info.get('title', 'N/A')}

Original Reference Word Count
{len(context.subtitles)}

Hot Comments
{comments_text}

Original Story Text
{context.subtitles}
[END_OF_INPUT_DATA]"""
    
    def _load_cached_framework(self, context: PipelineContextV3) -> Optional[Dict]:
        """加载缓存的框架"""
        try:
            cache_file = context.cache_dir / "processing" / "framework_v3.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
        except Exception as e:
            logger.warning(f"Failed to load cached framework: {e}")
        return None
    
    def _save_cached_framework(self, context: PipelineContextV3):
        """保存框架缓存"""
        try:
            cache_dir = context.cache_dir / "processing"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                'raw': context.framework_v3_raw,
                'json': context.framework_v3_json
            }
            
            with open(cache_dir / "framework_v3.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save framework cache: {e}")


# ============= 框架解析步骤 =============

class ParseFrameworkV3Step(PipelineStep):
    """解析V3框架，提取segment信息"""
    
    def __init__(self):
        super().__init__("parse_framework_v3")
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """解析框架"""
        try:
            if not context.framework_v3_json:
                raise Exception("No framework JSON to parse - TERMINATING")
            
            # 提取storyBlueprint
            blueprint = context.framework_v3_json.get('storyBlueprint', [])
            
            if not blueprint:
                raise Exception("Empty storyBlueprint - TERMINATING")
            
            # 设置segment数量和任务
            context.segment_count = len(blueprint)
            context.segment_tasks = blueprint
            
            logger.info(f"📋 解析出 {context.segment_count} 个segments")
            
            # 保存解析结果
            if context.save_intermediate and context.cache_dir:
                self._save_parsed_info(context)
            
            return StepResult(success=True, data={
                'segment_count': context.segment_count,
                'tasks': context.segment_tasks
            })
            
        except Exception as e:
            error_msg = f"Framework parsing failed: {e}"
            logger.error(f"❌ {error_msg}")
            context.add_error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _save_parsed_info(self, context: PipelineContextV3):
        """保存解析信息"""
        try:
            cache_dir = context.cache_dir / "processing"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            info = {
                'segment_count': context.segment_count,
                'segment_tasks': context.segment_tasks
            }
            
            with open(cache_dir / "parsed_segments.json", 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save parsed info: {e}")


# ============= 开头生成步骤 =============

class GenerateStoryHeaderStep(PipelineStep):
    """生成故事开头"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_story_header")
        self.gemini_client = gemini_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """生成开头"""
        try:
            # 检查缓存
            if context.cache_dir:
                cached_header = self._load_cached_header(context)
                if cached_header:
                    context.story_header = cached_header
                    logger.info("✅ 从缓存加载故事开头")
                    return StepResult(success=True, data={'header': cached_header})
            
            # 获取提示词
            if not self.prompt_manager:
                raise Exception("Prompt manager not set - TERMINATING")
            
            # 准备输入：完整的V3 JSON
            json_input = json.dumps(context.framework_v3_json, indent=2, ensure_ascii=False)
            
            prompt = self.prompt_manager.get_prompt('story_header')
            full_prompt = prompt + "\n\n" + json_input
            
            logger.info("🎯 生成故事开头...")
            response = self.gemini_client.generate_content(full_prompt)
            
            if not response:
                raise Exception("Header generation failed - empty response - TERMINATING")
            
            context.story_header = response
            
            # 保存缓存
            if context.save_intermediate and context.cache_dir:
                self._save_cached_header(context)
            
            logger.info(f"✅ 开头生成成功，长度: {len(response)}字符")
            return StepResult(success=True)
            
        except Exception as e:
            error_msg = f"Header generation failed: {e}"
            logger.error(f"❌ {error_msg}")
            context.add_error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _load_cached_header(self, context: PipelineContextV3) -> Optional[str]:
        """加载缓存的开头"""
        try:
            cache_file = context.cache_dir / "processing" / "story_header.txt"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to load cached header: {e}")
        return None
    
    def _save_cached_header(self, context: PipelineContextV3):
        """保存开头缓存"""
        try:
            cache_dir = context.cache_dir / "processing"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            with open(cache_dir / "story_header.txt", 'w', encoding='utf-8') as f:
                f.write(context.story_header)
                
        except Exception as e:
            logger.warning(f"Failed to save header cache: {e}")


# ============= Segment生成步骤 =============

class GenerateAllSegmentsStep(PipelineStep):
    """生成所有segments"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_all_segments")
        self.gemini_client = gemini_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """生成所有segments"""
        try:
            segments = []
            segments_dir = None
            
            if context.cache_dir:
                segments_dir = context.cache_dir / "processing" / "segments"
                segments_dir.mkdir(parents=True, exist_ok=True)
            
            # 逐个生成segment
            for i in range(context.segment_count):
                logger.info(f"📝 生成Segment {i+1}/{context.segment_count}")
                
                # 检查缓存
                cached_segment = None
                if segments_dir:
                    cached_segment = self._load_cached_segment(segments_dir, i+1)
                
                if cached_segment:
                    segments.append(cached_segment)
                    logger.info(f"  ✅ 从缓存加载Segment {i+1}")
                    continue
                
                # 生成新segment
                segment = self._generate_single_segment(context, i, segments)
                
                if not segment:
                    raise Exception(f"Segment {i+1} generation failed - TERMINATING")
                
                segments.append(segment)
                
                # 保存缓存
                if segments_dir:
                    self._save_cached_segment(segments_dir, i+1, segment)
                
                logger.info(f"  ✅ Segment {i+1} 生成成功，长度: {len(segment)}字符")
            
            context.segments = segments
            logger.info(f"✅ 所有 {len(segments)} 个segments生成完成")
            
            return StepResult(success=True, data={'segments': segments})
            
        except Exception as e:
            error_msg = f"Segments generation failed: {e}"
            logger.error(f"❌ {error_msg}")
            context.add_error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _generate_single_segment(self, context: PipelineContextV3, 
                                 index: int, 
                                 previous_segments: List[str]) -> Optional[str]:
        """生成单个segment"""
        try:
            # 获取提示词
            if not self.prompt_manager:
                raise Exception("Prompt manager not set")
            
            # 获取前文（200字）
            if index == 0:
                # 第一个segment，使用header的最后200字
                previous_text = context.story_header[-200:] if context.story_header else ""
            else:
                # 使用上一个segment的最后200字
                previous_text = previous_segments[-1][-200:] if previous_segments else ""
            
            # 获取当前step信息
            current_task = context.segment_tasks[index]
            
            # 构建输入
            segment_input = self._build_segment_input(
                context.framework_v3_json,
                index + 1,  # step编号从1开始
                current_task,
                previous_text
            )
            
            # 获取segment提示词并组合
            segment_prompt = self.prompt_manager.get_prompt('segment_generator')
            full_prompt = segment_prompt + "\n\n" + segment_input
            
            # 调用AI生成
            response = self.gemini_client.generate_content(full_prompt)
            
            return response if response else None
            
        except Exception as e:
            logger.error(f"Failed to generate segment {index+1}: {e}")
            return None
    
    def _build_segment_input(self, framework_json: Dict, 
                            step_num: int, 
                            current_task: Dict,
                            previous_text: str) -> str:
        """构建segment生成的输入"""
        # 准备框架JSON
        framework_str = json.dumps(framework_json, indent=2, ensure_ascii=False)
        
        # 准备当前任务信息
        task_str = json.dumps(current_task, indent=2, ensure_ascii=False)
        
        return f"""==================================================
FRAMEWORK V3 (Complete JSON)
==================================================
{framework_str}

==================================================
CURRENT STEP NUMBER
==================================================
Step {step_num}

==================================================
CURRENT STEP TASK
==================================================
{task_str}

==================================================
PREVIOUS TEXT (Last 200 characters)
==================================================
{previous_text if previous_text else "[This is the first segment after header]"}
"""
    
    def _load_cached_segment(self, segments_dir: Path, segment_num: int) -> Optional[str]:
        """加载缓存的segment"""
        try:
            cache_file = segments_dir / f"segment_{segment_num:02d}.txt"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to load cached segment {segment_num}: {e}")
        return None
    
    def _save_cached_segment(self, segments_dir: Path, segment_num: int, content: str):
        """保存segment缓存"""
        try:
            cache_file = segments_dir / f"segment_{segment_num:02d}.txt"
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Failed to save segment {segment_num}: {e}")


# ============= 拼接和润色步骤 =============

class MergeAndPolishStep(PipelineStep):
    """拼接所有内容并润色"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("merge_and_polish")
        self.gemini_client = gemini_client
        self.text_processor = TextProcessor()
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """执行拼接和润色"""
        try:
            # 拼接所有内容
            logger.info("🔗 拼接故事内容...")
            merged_parts = [context.story_header] + context.segments
            context.merged_story = "\n\n".join(merged_parts)
            
            # 保存拼接结果
            if context.save_intermediate and context.cache_dir:
                cache_dir = context.cache_dir / "processing"
                cache_dir.mkdir(parents=True, exist_ok=True)
                with open(cache_dir / "merged_story.txt", 'w', encoding='utf-8') as f:
                    f.write(context.merged_story)
            
            logger.info(f"  ✅ 拼接完成，总长度: {len(context.merged_story)}字符")
            
            # 检查润色缓存
            if context.cache_dir:
                cached_polish = self._load_cached_polish(context)
                if cached_polish:
                    context.polished_story = cached_polish
                    context.final_story = cached_polish
                    logger.info("✅ 从缓存加载润色结果")
                    return StepResult(success=True)
            
            # 执行润色
            logger.info("✨ 开始润色故事...")
            
            # 获取润色提示词
            if not self.prompt_manager:
                raise Exception("Prompt manager not set - TERMINATING")
            
            # 构建润色输入
            polish_input = self.text_processor.format_polish_input(
                json.dumps(context.framework_v3_json, indent=2, ensure_ascii=False),
                context.merged_story,
                num_segments=context.segment_count
            )
            
            polish_prompt = self.prompt_manager.get_prompt('final_polisher')
            full_prompt = polish_prompt + "\n\n" + polish_input
            
            response = self.gemini_client.generate_content(full_prompt)
            
            if not response:
                # 润色失败，使用原始拼接版本
                logger.warning("⚠️ 润色失败，使用原始版本")
                context.polished_story = context.merged_story
                context.final_story = context.merged_story
            else:
                # 解析润色结果
                polish_result = self.text_processor.parse_polish_output(response)
                context.polished_story = polish_result.get('story', context.merged_story)
                context.final_story = context.polished_story
                
                # 保存编辑报告
                if 'report' in polish_result and context.cache_dir:
                    report_file = context.cache_dir / "processing" / "polish_report.txt"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        f.write(polish_result['report'])
            
            # 保存润色结果
            if context.save_intermediate and context.cache_dir:
                self._save_cached_polish(context)
            
            logger.info(f"✅ 润色完成，最终长度: {len(context.final_story)}字符")
            return StepResult(success=True)
            
        except Exception as e:
            # 润色失败不终止，使用原始版本
            logger.warning(f"Polish failed, using raw version: {e}")
            context.final_story = context.merged_story if context.merged_story else ""
            return StepResult(success=True)  # 返回成功，继续流程
    
    def _load_cached_polish(self, context: PipelineContextV3) -> Optional[str]:
        """加载缓存的润色结果"""
        try:
            cache_file = context.cache_dir / "processing" / "polished_story.txt"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to load cached polish: {e}")
        return None
    
    def _save_cached_polish(self, context: PipelineContextV3):
        """保存润色结果"""
        try:
            cache_dir = context.cache_dir / "processing"
            with open(cache_dir / "polished_story.txt", 'w', encoding='utf-8') as f:
                f.write(context.polished_story)
        except Exception as e:
            logger.warning(f"Failed to save polish cache: {e}")


# ============= 总结生成步骤 =============

class GenerateSummaryStep(PipelineStep):
    """生成中文总结"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_summary")
        self.gemini_client = gemini_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """生成总结"""
        try:
            if not context.final_story:
                logger.warning("No story to summarize")
                context.summary_cn = "无故事内容"
                return StepResult(success=True)
            
            logger.info("📝 生成中文总结...")
            
            # 简单的总结提示词
            summary_prompt = """请为以下英文故事生成一份详细的中文总结。

要求：
1. 总结故事的主要情节（500字左右）
2. 分析故事的核心主题和价值观
3. 列出主要角色及其特点
4. 评价故事的亮点和特色
5. 提供YouTube发布建议（标题、标签、封面等）

故事内容：
"""
            
            # 只使用故事的前5000字进行总结（避免token限制）
            story_excerpt = context.final_story[:5000] if len(context.final_story) > 5000 else context.final_story
            
            full_prompt = summary_prompt + story_excerpt
            
            response = self.gemini_client.generate_content(full_prompt)
            
            if response:
                context.summary_cn = response
                logger.info("✅ 中文总结生成成功")
            else:
                context.summary_cn = "总结生成失败"
                logger.warning("⚠️ 总结生成失败")
            
            # 保存总结
            if context.save_intermediate and context.cache_dir:
                self._save_summary(context)
            
            return StepResult(success=True)
            
        except Exception as e:
            # 总结失败不影响主流程
            logger.warning(f"Summary generation failed: {e}")
            context.summary_cn = f"总结生成失败: {str(e)}"
            return StepResult(success=True)
    
    def _save_summary(self, context: PipelineContextV3):
        """保存总结"""
        try:
            final_dir = context.cache_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            
            with open(final_dir / "summary_cn.txt", 'w', encoding='utf-8') as f:
                f.write(context.summary_cn)
                
        except Exception as e:
            logger.warning(f"Failed to save summary: {e}")


# ============= 最终输出步骤 =============

class SaveFinalOutputStep(PipelineStep):
    """保存最终输出文件"""
    
    def __init__(self):
        super().__init__("save_final_output")
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """保存所有最终文件"""
        try:
            if not context.cache_dir:
                logger.warning("No cache directory specified")
                return StepResult(success=True)
            
            final_dir = context.cache_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存最终故事
            with open(final_dir / "story.txt", 'w', encoding='utf-8') as f:
                f.write(context.final_story)
            
            # 保存元数据
            metadata = {
                'video_id': context.video_id,
                'creator_name': context.creator_name,
                'video_title': context.video_info.get('title', 'N/A'),
                'segment_count': context.segment_count,
                'story_length': len(context.final_story),
                'header_length': len(context.story_header),
                'errors': context.errors
            }
            
            with open(final_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 生成报告
            report = self._generate_report(context)
            with open(final_dir / "report.md", 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"✅ 所有文件已保存到: {final_dir}")
            
            return StepResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to save final output: {e}"
            logger.error(error_msg)
            return StepResult(success=False, error=error_msg)
    
    def _generate_report(self, context: PipelineContextV3) -> str:
        """生成最终报告"""
        from datetime import datetime
        
        return f"""# V3 Pipeline 执行报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本信息
- **视频ID**: {context.video_id}
- **创作者**: {context.creator_name}
- **视频标题**: {context.video_info.get('title', 'N/A')}

## 生成统计
- **Segment数量**: {context.segment_count}
- **开头长度**: {len(context.story_header)} 字符
- **原始拼接长度**: {len(context.merged_story)} 字符
- **最终故事长度**: {len(context.final_story)} 字符

## 错误记录
{chr(10).join(context.errors) if context.errors else '无错误'}

## 中文总结
{context.summary_cn}

## YouTube发布建议
{ '已生成双语版本 - 请查看youtube_metadata.md' if context.youtube_metadata else '未生成'}

## 故事预览

### 开头（前500字符）
```
{context.final_story[:500] if context.final_story else 'N/A'}
```

### 结尾（后500字符）
```
{context.final_story[-500:] if context.final_story else 'N/A'}
```

---
*报告生成完毕*
"""