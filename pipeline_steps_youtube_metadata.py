#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Metadata Generation Step
生成双语版本的YouTube发布建议
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path

from pipeline_architecture import PipelineStep, StepResult
from pipeline_context_v3 import PipelineContextV3
from gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class GenerateYouTubeMetadataStep(PipelineStep):
    """生成YouTube发布元数据（双语版本）"""
    
    def __init__(self, gemini_client: GeminiClient):
        super().__init__("generate_youtube_metadata")
        self.gemini_client = gemini_client
    
    def execute(self, context: PipelineContextV3) -> StepResult:
        """生成YouTube元数据"""
        try:
            logger.info("🎬 生成YouTube发布建议...")
            
            # 检查缓存
            if context.cache_dir:
                cached_metadata = self._load_cached_metadata(context)
                if cached_metadata:
                    context.youtube_metadata = cached_metadata
                    logger.info("✅ 从缓存加载YouTube元数据")
                    return StepResult(success=True, data=cached_metadata)
            
            # 准备输入数据
            input_data = self._prepare_input(context)
            
            # 生成元数据
            metadata = self._generate_metadata(input_data)
            
            if metadata:
                context.youtube_metadata = metadata
                
                # 保存结果
                if context.save_intermediate and context.cache_dir:
                    self._save_metadata(context, metadata)
                
                logger.info("✅ YouTube元数据生成成功")
                return StepResult(success=True, data=metadata)
            else:
                logger.warning("⚠️ YouTube元数据生成失败")
                return StepResult(success=True)  # 不影响主流程
                
        except json.JSONDecodeError as je:
            logger.warning(f"YouTube metadata JSON parsing failed: {je}")
            logger.debug(f"Error details - msg: {je.msg}, pos: {je.pos}, doc: {je.doc[:100] if je.doc else 'None'}")
            return StepResult(success=True)  # 非关键步骤，继续执行
        except Exception as e:
            logger.warning(f"YouTube metadata generation failed: {e}")
            logger.debug(f"Error type: {type(e).__name__}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return StepResult(success=True)  # 非关键步骤，继续执行
    
    def _prepare_input(self, context: PipelineContextV3) -> Dict:
        """准备输入数据"""
        # 从framework中提取关键信息
        framework_data = context.framework_v3_json
        
        # 提取故事信息
        story_info = {
            'title': framework_data.get('adaptationAnalysis', {}).get('newStoryTitle', ''),
            'core_concept': framework_data.get('adaptationAnalysis', {}).get('coreConcept', ''),
            'characters': framework_data.get('adaptationAnalysis', {}).get('mainCharacters', []),
            'hook': framework_data.get('adaptationAnalysis', {}).get('openingReplicationStrategy', {})
        }
        
        # 提取前1000字用于分析
        story_excerpt = context.final_story[:1000] if context.final_story else ""
        
        return {
            'video_info': context.video_info,
            'story_info': story_info,
            'story_excerpt': story_excerpt,
            'segment_count': context.segment_count
        }
    
    def _generate_metadata(self, input_data: Dict) -> Dict:
        """调用AI生成元数据"""
        
        prompt = """You are a YouTube content optimization expert. Generate comprehensive YouTube publishing metadata in both Chinese and English.

Based on the story information provided, create:

1. **Video Titles** (3 versions each in CN and EN)
   - Hook-based title (using numbers or shocking facts)
   - Question-based title (arousing curiosity)
   - Benefit-based title (what viewers will gain)

2. **Video Description** (CN and EN)
   - First 125 characters must be extremely compelling (shown in search)
   - Include story synopsis (2-3 sentences)
   - Add 3-5 discussion questions
   - Include relevant timestamps placeholder

3. **Tags** (Mixed CN and EN)
   - 10-15 highly relevant tags
   - Mix of broad and specific terms
   - Include trending related tags

4. **Thumbnail Elements**
   - Main visual focus description
   - Text overlay suggestions (CN and EN versions)
   - Color scheme recommendation
   - Emotion/expression guidance

5. **Publishing Strategy**
   - Best time to publish (with timezone)
   - Target audience demographics
   - Engagement tactics (first 48 hours)
   - Community post ideas

Please output in the following JSON format:
```json
{{
  "titles": {{
    "chinese": ["标题1", "标题2", "标题3"],
    "english": ["Title 1", "Title 2", "Title 3"]
  }},
  "descriptions": {{
    "chinese": "中文描述...",
    "english": "English description..."
  }},
  "tags": {{
    "chinese": ["标签1", "标签2", ...],
    "english": ["tag1", "tag2", ...],
    "mixed": ["混合标签", "mixed tags", ...]
  }},
  "thumbnail": {{
    "visual_focus": "Description of main visual element",
    "text_overlay": {{
      "chinese": "中文文字",
      "english": "English text"
    }},
    "color_scheme": "Color recommendations",
    "emotion": "Facial expression/emotion guidance"
  }},
  "strategy": {{
    "publish_time": "Best time with timezone",
    "target_audience": "Demographics description",
    "first_48_hours": ["Tactic 1", "Tactic 2", ...],
    "community_posts": ["Post idea 1", "Post idea 2", ...]
  }}
}}
```

Story Information:
- Title: {title}
- Core Concept: {core_concept}
- Segment Count: {segment_count}
- Original Video Title: {original_title}

Story Excerpt (first 1000 chars):
{story_excerpt}
""".format(
            title=input_data['story_info']['title'],
            core_concept=input_data['story_info']['core_concept'],
            segment_count=input_data['segment_count'],
            original_title=input_data['video_info'].get('title', 'N/A'),
            story_excerpt=input_data['story_excerpt']
        )
        
        try:
            response = self.gemini_client.generate_content(prompt)
            
            if response:
                # 解析JSON响应
                import re
                
                # 先尝试提取markdown代码块中的JSON
                json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    try:
                        metadata = json.loads(json_match.group(1))
                        return metadata
                    except json.JSONDecodeError as je:
                        logger.warning(f"Failed to parse JSON from code block: {je}")
                        logger.debug(f"JSON content that failed: {json_match.group(1)[:200]}...")
                
                # 如果没有代码块，尝试直接解析整个响应
                try:
                    # 清理响应，去除可能的前后空白和非JSON内容
                    cleaned_response = response.strip()
                    
                    # 检查是否缺少开头的大括号
                    if not cleaned_response.startswith('{') and '"titles"' in cleaned_response[:50]:
                        # 尝试修复缺少开头大括号的情况
                        cleaned_response = '{' + cleaned_response
                        logger.debug("Added missing opening brace to JSON response")
                    
                    # 尝试找到JSON的开始和结束
                    if cleaned_response.startswith('{'):
                        # 找到最后一个匹配的}
                        brace_count = 0
                        json_end = -1
                        for i, char in enumerate(cleaned_response):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            json_str = cleaned_response[:json_end]
                            metadata = json.loads(json_str)
                            return metadata
                        elif json_end == -1 and brace_count > 0:
                            # 缺少结束括号，尝试添加
                            cleaned_response += '}' * brace_count
                            logger.debug(f"Added {brace_count} missing closing braces")
                            metadata = json.loads(cleaned_response)
                            return metadata
                    
                    # 最后尝试直接解析
                    metadata = json.loads(cleaned_response)
                    return metadata
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse YouTube metadata JSON: {je}")
                    logger.debug(f"Response preview: {response[:500]}...")
                    return self._generate_fallback_metadata(input_data)
            else:
                logger.warning("No response from AI")
                return self._generate_fallback_metadata(input_data)
            
        except Exception as e:
            logger.warning(f"AI generation failed: {e}")
            return self._generate_fallback_metadata(input_data)
    
    def _generate_fallback_metadata(self, input_data: Dict) -> Dict:
        """生成备用元数据"""
        story_title = input_data['story_info'].get('title', 'Amazing Story')
        
        return {
            "titles": {
                "chinese": [
                    f"【震撼】{story_title} - 你绝对想不到的结局",
                    f"这个故事改变了100万人的人生观",
                    f"看完这个，你会重新思考一切"
                ],
                "english": [
                    f"{story_title} - The Ending Will Shock You",
                    "This Story Changed Everything I Believed",
                    "Watch This Before It's Too Late"
                ]
            },
            "descriptions": {
                "chinese": f"这个故事会彻底改变你的认知... 基于真实事件改编，{input_data['segment_count']}个章节带你经历一段难忘的旅程。",
                "english": f"This story will completely change your perspective... Based on true events, {input_data['segment_count']} chapters take you on an unforgettable journey."
            },
            "tags": {
                "chinese": ["故事", "真实改编", "感人", "励志"],
                "english": ["story", "true story", "emotional", "inspiring"],
                "mixed": ["YouTube故事", "viral story", "必看", "must watch"]
            },
            "thumbnail": {
                "visual_focus": "Emotional character close-up with dramatic lighting",
                "text_overlay": {
                    "chinese": "改变一生的30分钟",
                    "english": "30 Minutes That Changed Everything"
                },
                "color_scheme": "High contrast with warm/cool temperature split",
                "emotion": "Shocked or deeply moved expression"
            },
            "strategy": {
                "publish_time": "Tuesday-Thursday, 2-4 PM EST",
                "target_audience": "18-35 years old, interested in storytelling and life experiences",
                "first_48_hours": [
                    "Pin a comment asking for reactions",
                    "Create a community poll about the ending",
                    "Share behind-the-scenes in community tab"
                ],
                "community_posts": [
                    "Poll: What would you have done in this situation?",
                    "Share your own similar experience in comments"
                ]
            }
        }
    
    def _load_cached_metadata(self, context: PipelineContextV3) -> Dict:
        """加载缓存的元数据"""
        try:
            cache_file = context.cache_dir / "final" / "youtube_metadata.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached metadata: {e}")
        return None
    
    def _save_metadata(self, context: PipelineContextV3, metadata: Dict):
        """保存元数据"""
        try:
            final_dir = context.cache_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存JSON格式
            json_file = final_dir / "youtube_metadata.json"
            logger.debug(f"保存YouTube元数据到: {json_file}")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 保存人类可读的格式
            readable_content = self._format_readable_metadata(metadata)
            md_file = final_dir / "youtube_metadata.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(readable_content)
            
            logger.info(f"💾 YouTube元数据已保存: {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to save YouTube metadata: {e}")
            logger.exception("详细错误:")
    
    def _format_readable_metadata(self, metadata: Dict) -> str:
        """格式化为可读的Markdown"""
        
        content = """# YouTube发布建议 / YouTube Publishing Guide

## 📝 标题建议 / Title Suggestions

### 中文标题
"""
        
        for i, title in enumerate(metadata.get('titles', {}).get('chinese', []), 1):
            content += f"{i}. {title}\n"
        
        content += "\n### English Titles\n"
        for i, title in enumerate(metadata.get('titles', {}).get('english', []), 1):
            content += f"{i}. {title}\n"
        
        content += f"""

## 📄 视频描述 / Video Description

### 中文描述
{metadata.get('descriptions', {}).get('chinese', 'N/A')}

### English Description
{metadata.get('descriptions', {}).get('english', 'N/A')}

## 🏷️ 标签 / Tags

### 中文标签
{', '.join(metadata.get('tags', {}).get('chinese', []))}

### English Tags
{', '.join(metadata.get('tags', {}).get('english', []))}

### 混合标签 / Mixed Tags
{', '.join(metadata.get('tags', {}).get('mixed', []))}

## 🎨 缩略图设计 / Thumbnail Design

**视觉焦点 / Visual Focus:**
{metadata.get('thumbnail', {}).get('visual_focus', 'N/A')}

**文字叠加 / Text Overlay:**
- 中文: {metadata.get('thumbnail', {}).get('text_overlay', {}).get('chinese', 'N/A')}
- English: {metadata.get('thumbnail', {}).get('text_overlay', {}).get('english', 'N/A')}

**配色方案 / Color Scheme:**
{metadata.get('thumbnail', {}).get('color_scheme', 'N/A')}

**表情/情绪 / Emotion:**
{metadata.get('thumbnail', {}).get('emotion', 'N/A')}

## 📊 发布策略 / Publishing Strategy

**最佳发布时间 / Best Time to Publish:**
{metadata.get('strategy', {}).get('publish_time', 'N/A')}

**目标受众 / Target Audience:**
{metadata.get('strategy', {}).get('target_audience', 'N/A')}

**前48小时策略 / First 48 Hours:**
"""
        
        for tactic in metadata.get('strategy', {}).get('first_48_hours', []):
            content += f"- {tactic}\n"
        
        content += "\n**社区帖子创意 / Community Post Ideas:**\n"
        for idea in metadata.get('strategy', {}).get('community_posts', []):
            content += f"- {idea}\n"
        
        content += "\n---\n*Generated by V3 Pipeline*"
        
        return content