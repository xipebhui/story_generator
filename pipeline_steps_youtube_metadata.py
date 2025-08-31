#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Metadata Generation Step
生成双语版本的YouTube发布建议
"""

import json
import logging
import os
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


        meta_prompt_file = "prompts/youtube_meta_gen.md"

        with open(meta_prompt_file, "r", encoding="utf-8") as f:
           prompt_content = f.read()

        prompt = prompt_content + json.dumps(input_data, ensure_ascii=False, indent=4)

        
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
                    logger.error(f"Failed to parse YouTube metadata JSON: {je}")
                    logger.debug(f"Response preview: {response[:500]}...")
            else:
                logger.error("No response from AI")
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")

    
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
            
            logger.info(f"💾 YouTube元数据已保存: {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to save YouTube metadata: {e}")
            logger.exception("详细错误:")
