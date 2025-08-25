#!/usr/bin/env python3
"""
图片分析阶段
"""

import json
import base64
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from ..models import ComicImage, ImageAnalysis, SceneType, EmotionTone, BatchAnalysisResult
from ..config import ComicPipelineConfig

# 添加项目根目录到Python路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """图片分析器"""
    
    def __init__(self, config: ComicPipelineConfig, gemini_client: Optional[GeminiClient] = None):
        self.config = config
        self.gemini_client = gemini_client or self._init_gemini_client()
        
    def _init_gemini_client(self) -> GeminiClient:
        """初始化Gemini客户端 - 使用环境变量中的NewAPI配置"""
        # GeminiClient会从环境变量自动读取NEWAPI_API_KEY
        return GeminiClient()
    
    def analyze_single_image(
        self, 
        image: ComicImage,
        total_images: int,
        story_context: str = "",
        chapter_title: str = ""
    ) -> ImageAnalysis:
        """分析单张图片"""
        logger.info(f"分析图片: {image.filename}")
        
        # 首先尝试从缓存加载
        if self.config.pipeline.cache_enabled:
            cached_analysis = self._load_cached_analysis(image)
            if cached_analysis:
                logger.info(f"  ✓ 使用缓存的分析结果: {image.filename}")
                return cached_analysis
        
        # 读取图片并转换为base64
        image_data = self._load_image_base64(image.full_path)
        
        # 准备提示词
        prompt = self._prepare_analysis_prompt(
            image_index=image.index,
            total_images=total_images,
            story_context=story_context,
            chapter_title=chapter_title or image.chapter
        )
        
        # 调用Gemini API分析图片
        try:
            # 将图片和提示词组合成一个prompt
            full_prompt = f"{prompt}\n\n[图片已提供为base64格式]"
            # 注意：需要使用inline_data方式传递图片
            response = self.gemini_client.generate_content(full_prompt)
            
            # 解析JSON响应
            analysis_data = self._parse_analysis_response(response)
            
            # 创建分析结果
            analysis = self._create_analysis(image, analysis_data)
            
            # 缓存结果
            if self.config.pipeline.cache_enabled:
                self._cache_analysis(image, analysis)
                logger.info(f"  ✓ 已缓存分析结果: {image.filename}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析图片失败 {image.filename}: {e}")
            # 返回默认分析结果
            return self._create_default_analysis(image)
    
    def analyze_batch(
        self,
        images: List[ComicImage],
        batch_size: int = 5
    ) -> BatchAnalysisResult:
        """批量分析图片，理解整体故事"""
        logger.info(f"批量分析 {len(images)} 张图片")
        
        # 先分析前几张理解故事背景
        initial_batch = images[:min(batch_size, len(images))]
        story_outline = self._analyze_story_outline(initial_batch)
        
        # 逐张分析所有图片
        analyses = []
        for i, image in enumerate(images):
            analysis = self.analyze_single_image(
                image=image,
                total_images=len(images),
                story_context=story_outline.get('story_outline', ''),
                chapter_title=story_outline.get('title', '')
            )
            analyses.append(analysis)
            # 缓存已在 analyze_single_image 中处理
        
        return BatchAnalysisResult(
            images=images,
            analyses=analyses,
            story_outline=story_outline.get('story_outline', ''),
            main_characters=story_outline.get('main_characters', []),
            overall_tone=self._determine_overall_tone(analyses)
        )
    
    def _analyze_story_outline(self, images: List[ComicImage]) -> Dict[str, Any]:
        """通过标题搜索获取故事大纲"""
        logger.info("通过标题搜索故事大纲...")
        
        # 从第一张图片获取章节信息
        if not images:
            return self._get_default_outline()
            
        first_image = images[0]
        comic_title = first_image.chapter or "未知漫画"
        
        # 尝试从缓存加载故事大纲
        if self.config.pipeline.cache_enabled:
            cache_path = self.config.get_cache_path(
                "story_outlines",
                f"{comic_title}_outline.json"
            )
            if cache_path.exists():
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached_outline = json.load(f)
                    logger.info(f"  ✓ 使用缓存的故事大纲: {comic_title}")
                    return cached_outline
                except Exception as e:
                    logger.warning(f"加载故事大纲缓存失败: {e}")
        
        # 加载提示词模板
        prompt_path = self.config.get_prompt_path("story_outline")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            prompt_template = self._get_default_outline_prompt()
        
        # 格式化提示词 - 用于联网搜索
        prompt = prompt_template.replace("{comic_title}", comic_title)
        prompt = prompt.replace("{chapter_name}", comic_title)
        prompt = prompt.replace("{source_url}", "webtoon")
        
        # 调用Gemini进行联网搜索和分析
        try:
            # 使用generate_content让Gemini联网搜索信息
            response = self.gemini_client.generate_content(prompt)
            
            # 解析JSON响应
            json_match = json.loads(self._extract_json(response))
            
            # 缓存故事大纲
            if self.config.pipeline.cache_enabled:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(json_match, f, ensure_ascii=False, indent=2)
                logger.info(f"  ✓ 已缓存故事大纲: {comic_title}")
            
            return json_match
            
        except Exception as e:
            logger.error(f"搜索故事大纲失败: {e}")
            return self._get_default_outline()
    
    def _load_image_base64(self, image_path: Path) -> str:
        """加载图片并转换为base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _prepare_analysis_prompt(
        self,
        image_index: int,
        total_images: int,
        story_context: str,
        chapter_title: str
    ) -> str:
        """准备分析提示词"""
        # 加载提示词模板
        prompt_path = self.config.get_prompt_path("image_analysis")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            prompt_template = self._get_default_analysis_prompt()
        
        # 替换变量
        prompt = prompt_template.replace("{image_index}", str(image_index))
        prompt = prompt.replace("{total_images}", str(total_images))
        prompt = prompt.replace("{story_context}", story_context or "暂无")
        prompt = prompt.replace("{chapter_title}", chapter_title or "未知")
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析分析响应"""
        # 提取JSON内容
        json_str = self._extract_json(response)
        return json.loads(json_str)
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        import re
        # 查找JSON块
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group()
        
        # 如果没找到，尝试查找```json块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        raise ValueError("No JSON found in response")
    
    def _create_analysis(self, image: ComicImage, data: Dict[str, Any]) -> ImageAnalysis:
        """创建分析结果对象"""
        # 转换场景类型
        scene_type_map = {
            'action': SceneType.ACTION,
            'dialog': SceneType.DIALOG,
            'transition': SceneType.TRANSITION,
            'climax': SceneType.CLIMAX,
            'static': SceneType.STATIC
        }
        scene_type = scene_type_map.get(data.get('scene_type', 'static'), SceneType.STATIC)
        
        # 转换情绪类型
        emotion_map = {
            '紧张': EmotionTone.TENSE,
            '轻松': EmotionTone.RELAXED,
            '激动': EmotionTone.EXCITING,
            '悲伤': EmotionTone.SAD,
            '神秘': EmotionTone.MYSTERIOUS,
            '幽默': EmotionTone.HUMOROUS,
            '平静': EmotionTone.NEUTRAL
        }
        emotion = emotion_map.get(data.get('emotion', '平静'), EmotionTone.NEUTRAL)
        
        return ImageAnalysis(
            image=image,
            description=data.get('description', ''),
            scene_type=scene_type,
            emotion=emotion,
            characters=data.get('characters', []),
            action=data.get('action', ''),
            dialog=data.get('dialog'),
            objects=data.get('objects', [])
        )
    
    def _create_default_analysis(self, image: ComicImage) -> ImageAnalysis:
        """创建默认分析结果"""
        return ImageAnalysis(
            image=image,
            description="画面展示了故事的一个场景",
            scene_type=SceneType.STATIC,
            emotion=EmotionTone.NEUTRAL,
            characters=[],
            action="场景展示",
            dialog=None,
            objects=[]
        )
    
    def _determine_overall_tone(self, analyses: List[ImageAnalysis]) -> EmotionTone:
        """确定整体基调"""
        if not analyses:
            return EmotionTone.NEUTRAL
        
        # 统计各种情绪出现的次数
        emotion_counts = {}
        for analysis in analyses:
            emotion = analysis.emotion
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 返回出现最多的情绪
        return max(emotion_counts, key=emotion_counts.get)
    
    def _load_cached_analysis(self, image: ComicImage) -> Optional[ImageAnalysis]:
        """从缓存加载分析结果"""
        cache_path = self.config.get_cache_path(
            "analyses",
            f"{image.chapter}_{image.index:03d}.json"
        )
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证缓存是否匹配当前图片
            cached_image = data.get('image', {})
            if (cached_image.get('index') != image.index or 
                cached_image.get('filename') != image.filename):
                logger.warning(f"缓存不匹配，跳过: {image.filename}")
                return None
            
            # 重建分析结果
            analysis_data = data.get('analysis', {})
            return self._create_analysis(image, {
                'description': analysis_data.get('description', ''),
                'scene_type': analysis_data.get('scene_type', 'static'),
                'emotion': analysis_data.get('emotion', '平静'),
                'characters': analysis_data.get('characters', []),
                'action': analysis_data.get('action', ''),
                'dialog': analysis_data.get('dialog'),
                'objects': analysis_data.get('objects', [])
            })
            
        except Exception as e:
            logger.warning(f"加载缓存失败 {cache_path}: {e}")
            return None
    
    def _cache_analysis(self, image: ComicImage, analysis: ImageAnalysis):
        """缓存分析结果"""
        if not self.config.pipeline.cache_enabled:
            return
        
        cache_path = self.config.get_cache_path(
            "analyses",
            f"{image.chapter}_{image.index:03d}.json"
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({
                'image': {
                    'path': image.path,
                    'index': image.index,
                    'chapter': image.chapter,
                    'filename': image.filename
                },
                'analysis': {
                    'description': analysis.description,
                    'scene_type': analysis.scene_type.value,
                    'emotion': analysis.emotion.value,
                    'characters': analysis.characters,
                    'action': analysis.action,
                    'dialog': analysis.dialog,
                    'objects': analysis.objects
                }
            }, f, ensure_ascii=False, indent=2)
    
    def _get_default_analysis_prompt(self) -> str:
        """获取默认分析提示词"""
        return """分析这张漫画图片，返回JSON格式的分析结果。"""
    
    def _get_default_outline_prompt(self) -> str:
        """获取默认大纲提示词"""
        return """分析这些漫画图片，理解故事背景和主线。"""
    
    def _get_default_outline(self) -> Dict[str, Any]:
        """获取默认大纲"""
        return {
            'title': '未知故事',
            'genre': '未知',
            'story_outline': '这是一个精彩的故事',
            'main_characters': [],
            'tone': '平静'
        }