#!/usr/bin/env python3
"""
文案生成阶段
"""

import json
import random
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from ..models import (
    ImageAnalysis, NarrationSegment, NarrationContext,
    ComicImage, EmotionTone
)
from ..config import ComicPipelineConfig

# 添加项目根目录到Python路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class NarrationGenerator:
    """解说文案生成器"""
    
    def __init__(self, config: ComicPipelineConfig, gemini_client: Optional[GeminiClient] = None):
        self.config = config
        self.gemini_client = gemini_client or self._init_gemini_client()
        self.context = NarrationContext()
        
    def _init_gemini_client(self) -> GeminiClient:
        """初始化Gemini客户端 - 使用环境变量中的NewAPI配置"""
        # GeminiClient会从环境变量自动读取NEWAPI_API_KEY
        return GeminiClient()
    
    def generate_for_single_image(
        self,
        analysis: ImageAnalysis,
        story_progress: float = 0.0,
        force_word_count: Optional[int] = None
    ) -> str:
        """为单张图片生成解说文案"""
        logger.info(f"生成文案: 图片 {analysis.image.index}")
        
        # 首先尝试从缓存加载
        if self.config.pipeline.cache_enabled:
            cached_narration = self._load_cached_narration(analysis.image)
            if cached_narration:
                logger.info(f"  ✓ 使用缓存的文案: 图片 {analysis.image.index}")
                # 更新上下文（即使使用缓存也要保持上下文）
                self.context.add_narration(cached_narration)
                self.context.current_emotion = analysis.emotion
                self.context.story_progress = story_progress
                return cached_narration
        
        # 确定目标字数
        if force_word_count:
            target_word_count = force_word_count
        else:
            min_words, max_words = analysis.get_suggested_word_count()
            target_word_count = random.randint(min_words, max_words)
        
        # 准备提示词
        prompt = self._prepare_narration_prompt(
            analysis=analysis,
            target_word_count=target_word_count,
            story_progress=story_progress
        )
        
        # 生成文案
        try:
            narration = self.gemini_client.generate_content(prompt)
            
            # 清理文案
            narration = self._clean_narration(narration)
            
            # 更新上下文
            self.context.add_narration(narration)
            self.context.current_emotion = analysis.emotion
            self.context.story_progress = story_progress
            
            # 缓存结果
            if self.config.pipeline.cache_enabled:
                self._cache_narration(analysis.image, narration)
                logger.info(f"  ✓ 已缓存文案: 图片 {analysis.image.index}")
            
            return narration
            
        except Exception as e:
            logger.error(f"生成文案失败: {e}")
            return self._generate_fallback_narration(analysis, target_word_count)
    
    def generate_batch_narrations(
        self,
        analyses: List[ImageAnalysis],
        story_outline: str = ""
    ) -> List[str]:
        """批量生成连贯的解说文案"""
        logger.info(f"批量生成 {len(analyses)} 段文案")
        
        # 设置故事大纲
        self.context.story_outline = story_outline
        
        narrations = []
        total_images = len(analyses)
        
        for i, analysis in enumerate(analyses):
            # 计算故事进度
            progress = (i + 1) / total_images * 100
            
            # 生成文案
            narration = self.generate_for_single_image(
                analysis=analysis,
                story_progress=progress
            )
            
            narrations.append(narration)
            
            # 日志进度
            logger.info(f"进度: {i+1}/{total_images} - {len(narration)}字")
        
        return narrations
    
    def _prepare_narration_prompt(
        self,
        analysis: ImageAnalysis,
        target_word_count: int,
        story_progress: float
    ) -> str:
        """准备生成提示词"""
        # 加载提示词模板
        prompt_path = self.config.get_prompt_path("narration_generator")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            prompt_template = self._get_default_narration_prompt()
        
        # 准备变量
        variables = {
            "{image_description}": analysis.description,
            "{scene_type}": analysis.scene_type.value,
            "{emotion_tone}": analysis.emotion.value,
            "{previous_narration}": self.context.get_recent_context(2),
            "{story_progress}": f"{story_progress:.1f}",
            "{target_word_count}": str(target_word_count),
            "{narration_style}": self.config.narration.narration_style,
            "{transition_words}": "、".join(
                random.sample(self.config.narration.transition_words, 3)
            )
        }
        
        # 替换变量
        prompt = prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(key, value)
        
        return prompt
    
    def _clean_narration(self, text: str) -> str:
        """清理生成的文案"""
        # 移除可能的标记
        text = text.strip()
        
        # 移除可能的引号
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        # 移除多余的空格
        text = ' '.join(text.split())
        
        return text
    
    def _generate_fallback_narration(
        self,
        analysis: ImageAnalysis,
        target_word_count: int
    ) -> str:
        """生成备用文案"""
        # 根据场景类型生成模板文案
        templates = {
            'action': [
                f"激烈的战斗正在进行，{analysis.action}。",
                f"场面瞬间变得紧张起来，{analysis.action}。"
            ],
            'dialog': [
                f"角色们正在进行重要的对话，气氛{analysis.emotion.value}。",
                f"话语间透露出{analysis.emotion.value}的情绪。"
            ],
            'transition': [
                f"场景转换到了新的地方。",
                f"故事进入了新的阶段。"
            ],
            'climax': [
                f"故事达到了高潮，{analysis.action}。",
                f"关键时刻到来了，气氛极度{analysis.emotion.value}。"
            ],
            'static': [
                f"画面展示了{analysis.description[:20]}...。",
                f"此时的场景显得{analysis.emotion.value}。"
            ]
        }
        
        scene_type = analysis.scene_type.value
        template_list = templates.get(scene_type, templates['static'])
        narration = random.choice(template_list)
        
        # 如果有角色，加入角色描述
        if analysis.characters:
            characters_str = "、".join(analysis.characters[:2])
            narration += f"{characters_str}的表情令人印象深刻。"
        
        # 补充到目标字数
        while len(narration) < target_word_count * 0.8:
            padding = random.choice([
                "场面令人印象深刻。",
                "这一幕充满了张力。",
                "故事正在向前推进。",
                "观众的心被紧紧抓住。"
            ])
            narration += padding
        
        return narration[:target_word_count + 10]  # 允许略微超出
    
    def _cache_narration(self, image: ComicImage, narration: str):
        """缓存生成的文案"""
        if not self.config.pipeline.cache_enabled:
            return
        
        cache_path = self.config.get_cache_path(
            "narrations",
            f"{image.chapter}_{image.index:03d}.txt"
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(narration)
    
    def _load_cached_narration(self, image: ComicImage) -> Optional[str]:
        """加载缓存的文案"""
        if not self.config.pipeline.cache_enabled:
            return None
        
        cache_path = self.config.get_cache_path(
            "narrations",
            f"{image.chapter}_{image.index:03d}.txt"
        )
        
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return None
    
    def _get_default_narration_prompt(self) -> str:
        """获取默认生成提示词"""
        return """
请为这个漫画场景生成解说词。

场景描述：{image_description}
情绪基调：{emotion_tone}
目标字数：{target_word_count}

要求：
1. 生动描述画面
2. 符合情绪基调
3. 自然流畅

请直接输出解说词。
"""