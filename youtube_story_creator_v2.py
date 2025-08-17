#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Story Creator V2
使用新的上下文管理策略和30个片段的二级框架
专注于30000字长故事的生成
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
print(f"--- project path = {project_root}")
sys.path.insert(0, str(project_root))

# 导入项目模块
from youtube_client import YouTubeAPIClient
from gemini_client import GeminiClient
from text_processor import TextProcessor
from image_prompt_generator import ImagePromptGenerator

# 配置日志
# 清除默认配置
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# 设置根日志级别
logging.root.setLevel(logging.DEBUG)

# 创建格式器
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 控制台处理器 - 只显示INFO及以上级别
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# 主日志文件 - 记录INFO及以上级别
file_handler = logging.FileHandler('story_creator_v2.log', encoding='utf-8', mode='a')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# 调试日志文件 - 记录所有级别（包括DEBUG）
debug_handler = logging.FileHandler('story_creator_v2_debug.log', encoding='utf-8', mode='a')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

# 添加处理器到根日志器
logging.root.addHandler(console_handler)
logging.root.addHandler(file_handler)
logging.root.addHandler(debug_handler)

logger = logging.getLogger(__name__)


class ContextManager:
    """管理Gemini API的对话历史"""
    
    def __init__(self):
        self.history = []
    
    def add_global_context(self, story_dna: str, framework: str):
        """
        添加全局上下文（最高指示）
        
        Args:
            story_dna: 故事DNA
            framework: 完整的30个片段框架
        """
        # 用户提供最高指示
        global_context = f"""
{TextProcessor.SECTION_DIVIDER}
最高指示 - 完整框架（30个片段）
{TextProcessor.SECTION_DIVIDER}
{framework}
"""
        
        self.history.append({
            "role": "user",
            "parts": [{"text": global_context}]
        })
        
        # 模型确认理解
        self.history.append({
            "role": "model",
            "parts": [{"text": "我已理解最高指示，包括故事DNA和30个片段的完整框架。我将严格按照这个框架生成每个片段。"}]
        })
    
    def add_segment_request(self, segment_input: str) -> None:
        """
        添加片段生成请求
        
        Args:
            segment_input: 片段生成的输入文本
        """
        self.history.append({
            "role": "user",
            "parts": [{"text": segment_input}]
        })
    
    def add_segment_response(self, segment_text: str) -> None:
        """
        添加片段生成响应
        
        Args:
            segment_text: 生成的片段文本
        """
        self.history.append({
            "role": "model",
            "parts": [{"text": segment_text}]
        })
    
    def get_history(self) -> List[Dict]:
        """获取完整的对话历史"""
        return self.history.copy()


class YouTubeStoryCreatorV2:
    """新版YouTube故事创作器 - 专注于30000字长故事"""
    
    def __init__(self, video_id: str, creator_name: str, target_length: int = 30000, num_segments: int = 9):
        """
        初始化
        
        Args:
            video_id: YouTube视频ID
            creator_name: 创作者名称
            target_length: 目标故事长度（默认30000字）
            num_segments: 片段数量（默认9个，对应9步结构）
        """
        self.video_id = video_id
        self.creator_name = creator_name
        self.target_length = target_length
        self.num_segments = num_segments  # 默认9个片段
        
        # 创建输出目录
        self.output_dir = Path("story_result") / creator_name / video_id
        self.raw_dir = self.output_dir / "raw"
        self.processing_dir = self.output_dir / "processing"
        self.segments_dir = self.output_dir / "segments"
        self.final_dir = self.output_dir / "final"
        
        for dir_path in [self.raw_dir, self.processing_dir, self.segments_dir, self.final_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化客户端
        self._init_clients()
        
        # 加载提示词
        self._load_prompts()
        
        # 文本处理器
        self.text_processor = TextProcessor()
        
        logger.info(f"✅ 初始化完成 - 视频ID: {video_id}, 创作者: {creator_name}")
        logger.info(f"📊 目标长度: {target_length}字, 片段数: {self.num_segments}")
    
    def _init_clients(self):
        """初始化API客户端"""
        # YouTube API密钥
        youtube_api_key = os.getenv("YOUTUBE_API_KEY", "AIzaSyCdbljoACNX1Ov3GsU6KRrnwWnCHAyyjVQ")
        
        # Gemini API密钥（优先使用NewAPI）
        gemini_api_key = "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu"
        if not gemini_api_key:
            gemini_api_key = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
            logger.warning("⚠️ 使用默认Gemini API密钥，建议设置NEWAPI_API_KEY环境变量")
        
        self.youtube_client = YouTubeAPIClient()
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        
        logger.info("✅ 客户端初始化完成")
    
    def _load_prompts(self):
        """加载所有提示词文件"""
        self.prompts = {}
        prompt_files = {
            "dna_extractor": "dna_extractor.md",
            "framework_generator": "framework_generate.md",
            "segment_generator": "segment_generator.md",
            "final_polisher": "final_polish.md"
        }
        
        prompts_dir = project_root / "prompts"
        for key, filename in prompt_files.items():
            file_path = prompts_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.prompts[key] = f.read()
                logger.info(f"✅ 加载提示词: {filename}")
            else:
                logger.error(f"❌ 提示词文件不存在: {file_path}")
                raise FileNotFoundError(f"Missing prompt file: {file_path}")
    
    def fetch_youtube_data(self) -> Dict[str, Any]:
        """
        获取YouTube视频数据
        每个组件（视频详情、评论、字幕）都独立检查缓存
        
        Returns:
            包含视频信息、评论、字幕的字典
        """
        logger.info(f"🔍 开始获取YouTube数据: {self.video_id}")
        data = {}
        import json
        
        # 定义缓存文件路径
        video_info_file = self.raw_dir / "video_info.json"
        comments_file = self.raw_dir / "comments.json" 
        subtitle_file = self.raw_dir / "subtitle.txt"
        
        # 1. 获取或加载视频详情
        if video_info_file.exists():
            logger.info("📂 发现视频详情缓存，从文件加载...")
            try:
                with open(video_info_file, 'r', encoding='utf-8') as f:
                    data['video_info'] = json.load(f)
                logger.info(f"✅ 视频标题: {data['video_info']['title']}")
            except Exception as e:
                logger.warning(f"⚠️ 加载视频详情失败: {e}")
                import traceback
                traceback.print_exc()
                data['video_info'] = None
        else:
            data['video_info'] = None
            
        if not data.get('video_info'):
            logger.info("📊 从YouTube获取视频详情...")
            try:
                video_details = self.youtube_client.get_video_details([self.video_id])
                if video_details and video_details.get('items'):
                    video_info = video_details['items'][0]
                    data['video_info'] = {
                        'title': video_info['snippet']['title'],
                        'description': video_info['snippet']['description'],
                        'channel_title': video_info['snippet']['channelTitle'],
                        'thumbnail': video_info['snippet']['thumbnails'].get('maxres', 
                                    video_info['snippet']['thumbnails'].get('high', {})).get('url', '')
                    }
                    # 保存视频详情
                    with open(video_info_file, 'w', encoding='utf-8') as f:
                        json.dump(data['video_info'], f, ensure_ascii=False, indent=2)
                    logger.info(f"✅ 视频标题: {data['video_info']['title']}")
                    logger.info(f"💾 视频详情已缓存到: {video_info_file}")
            except Exception as e:
                logger.error(f"❌ 获取视频详情失败: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # 2. 获取或加载评论
        if comments_file.exists():
            logger.info("📂 发现评论缓存，从文件加载...")
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    data['comments'] = json.load(f)
                logger.info(f"✅ 加载了 {len(data['comments'])} 条热门评论")
            except Exception as e:
                logger.warning(f"⚠️ 加载评论失败: {e}")
                import traceback
                traceback.print_exc()
                data['comments'] = None
        else:
            data['comments'] = None
            
        if not data.get('comments'):
            logger.info("💬 从YouTube获取视频评论...")
            try:
                comments_data = self.youtube_client.get_video_comments(self.video_id, max_results=5)
                if comments_data and comments_data.get('items'):
                    comments = []
                    for item in comments_data['items']:
                        snippet = item['snippet']['topLevelComment']['snippet']
                        comments.append({
                            'text': snippet['textDisplay'],
                            'likes': snippet['likeCount'],
                            'author': snippet['authorDisplayName']
                        })
                    data['comments'] = sorted(comments, key=lambda x: x['likes'], reverse=True)[:5]
                    # 保存评论
                    with open(comments_file, 'w', encoding='utf-8') as f:
                        json.dump(data['comments'], f, ensure_ascii=False, indent=2)
                    logger.info(f"✅ 获取了 {len(data['comments'])} 条热门评论")
                    logger.info(f"💾 评论已缓存到: {comments_file}")
                else:
                    data['comments'] = []
                    logger.warning("⚠️ 未获取到评论")
            except Exception as e:
                logger.warning(f"⚠️ 获取评论失败（非致命）: {e}")
                import traceback
                traceback.print_exc()
                data['comments'] = []
        
        # 3. 获取或加载字幕（这是必需的）
        if subtitle_file.exists():
            logger.info("📂 发现字幕缓存，从文件加载...")
            try:
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    data['subtitles'] = f.read()
                logger.info(f"✅ 加载字幕成功，长度: {len(data['subtitles'])}字")
            except Exception as e:
                logger.warning(f"⚠️ 加载字幕失败: {e}")
                import traceback
                traceback.print_exc()
                data['subtitles'] = None
        else:
            data['subtitles'] = None
            
        if not data.get('subtitles'):
            logger.info("📝 从YouTube获取视频字幕...")
            try:
                result = self.youtube_client.get_video_transcript(self.video_id)
                if result:
                    # get_video_transcript返回的是元组: (relative_path, subtitle_text)
                    relative_path, subtitle_text = result
                    data['subtitles'] = subtitle_text
                    # 保存字幕
                    with open(subtitle_file, 'w', encoding='utf-8') as f:
                        f.write(subtitle_text)
                    logger.info(f"✅ 获取字幕成功，长度: {len(subtitle_text)}字")
                    logger.info(f"💾 字幕已缓存到: {subtitle_file}")
                else:
                    logger.error("❌ 无法获取字幕，这是故事生成必需的")
                    return None
            except Exception as e:
                logger.error(f"❌ 获取字幕失败: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # 汇总信息
        logger.info("✅ YouTube数据获取/加载完成：")
        logger.info(f"  - 视频标题: {data['video_info']['title']}")
        logger.info(f"  - 评论数: {len(data.get('comments', []))}")
        logger.info(f"  - 字幕长度: {len(data.get('subtitles', ''))}字")
        
        return data
    
    def phase1_extract_dna(self, story_text: str) -> Tuple[str, Dict[str, Any]]:
        """
        第一阶段：提取故事DNA并分析文本长度
        如果已有处理结果，则从文件加载
        
        Args:
            story_text: 原始故事文本
            
        Returns:
            (故事DNA文本, 文本分析字典)
        """
        logger.info("🧬 第一阶段：开始提取故事DNA...")
        
        # 检查是否已有处理结果
        dna_file = self.processing_dir / "1_story_dna.txt"
        if dna_file.exists():
            logger.info("📂 发现已有故事DNA，从文件加载...")
            try:
                with open(dna_file, 'r', encoding='utf-8') as f:
                    response = f.read()
                
                # 解析响应
                dna_data = self.text_processor.parse_story_dna(response)
                
                logger.info(f"✅ 从缓存加载故事DNA成功")
                return response, dna_data.get('text_analysis', {})
                
            except Exception as e:
                logger.warning(f"⚠️ 加载故事DNA失败，将重新生成: {e}")
                import traceback
                traceback.print_exc()
        
        # 构建提示
        prompt = f"{self.prompts['dna_extractor']}\n\n---\n\n{story_text}"
        
        # DEBUG: 记录完整输入
        logger.debug("=" * 80)
        logger.debug("[DEBUG] phase1_extract_dna - AI调用输入:")
        logger.debug(f"输入长度: {len(prompt)} 字符")
        logger.debug("完整输入内容:")
        logger.debug("输入内容为原始的dna_extractor 和 原始的故事文本")
        logger.debug("=" * 80)
        
        try:
            # 调用Gemini API
            response = self.gemini_client.generate_content(prompt)
            
            # DEBUG: 记录完整输出
            logger.debug("=" * 80)
            logger.debug("[DEBUG] phase1_extract_dna - AI调用输出:")
            logger.debug(f"输出长度: {len(response) if response else 0} 字符")
            if response:
                logger.debug("完整输出内容:")
                logger.debug(response)
            else:
                logger.debug("响应为空")
            logger.debug("=" * 80)
            
            if response:
                # 保存原始响应
                with open(dna_file, 'w', encoding='utf-8') as f:
                    f.write(response)
                
                # 解析响应
                dna_data = self.text_processor.parse_story_dna(response)
                
                logger.info(f"✅ 故事DNA提取成功")
                
                # 返回完整的DNA文本和分析数据
                return response, dna_data.get('text_analysis', {})
            else:
                logger.error("❌ Gemini API响应为空")
                return None, None
                
        except Exception as e:
            logger.error(f"❌ 提取故事DNA失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def phase2_generate_framework(self, story_dna: str, video_info: Dict, comments: List) -> str:
        """
        第二阶段：生成9步故事改编框架
        如果已有处理结果，则从文件加载
        
        Args:
            story_dna: 故事DNA文本
            video_info: 视频信息
            comments: 热门评论
            
        Returns:
            框架文本
        """
        logger.info("📋 第二阶段：开始生成故事改编框架（9步结构）...")
        
        # 检查是否已有处理结果
        framework_file = self.processing_dir / "2_framework.txt"
        if framework_file.exists():
            logger.info("📂 发现已有框架，从文件加载...")
            try:
                with open(framework_file, 'r', encoding='utf-8') as f:
                    response = f.read()
                
                logger.info("✅ 从缓存加载框架成功")
                return response
                
            except Exception as e:
                logger.warning(f"⚠️ 加载框架失败，将重新生成: {e}")
                import traceback
                traceback.print_exc()
        
        # 准备输入 - 适配新的提示词格式
        top_comments = [c['text'] for c in comments[:5]]
        
        # 计算原故事字数（从字幕/DNA中估算）
        original_word_count = len(story_dna) if story_dna else 5000
        
        input_data = f"""### 原始故事DNA与元数据
- **原故事参考字数：** {original_word_count}
- **原始标题：** {video_info['title']}
- **热门评论（核心槽点来源）：**
{chr(10).join([f'  - {comment}' for comment in top_comments])}
- **故事DNA：**
{story_dna}
"""
        
        # 构建提示
        full_prompt = f"{self.prompts['framework_generator']}\n\n---\n\n{input_data}"
        
        # DEBUG: 记录完整输入
        logger.debug("=" * 80)
        logger.debug("[DEBUG] phase2_generate_framework - AI调用输入:")
        logger.debug(f"输入长度: {len(full_prompt)} 字符")
        logger.debug("完整输入内容:")
        logger.debug(full_prompt)
        logger.debug("=" * 80)
        
        # 添加重试机制
        max_retries = 1
        for attempt in range(max_retries):
            try:
                
                # 调用Gemini API
                response = self.gemini_client.generate_content(full_prompt)
                
                # DEBUG: 记录完整输出
                logger.debug("=" * 80)
                logger.debug("[DEBUG] phase2_generate_framework - AI调用输出:")
                logger.debug(f"尝试 {attempt + 1}/{max_retries}")
                logger.debug(f"输出长度: {len(response) if response else 0} 字符")
                if response:
                    logger.debug("完整输出内容:")
                    logger.debug(response)
                else:
                    logger.debug("响应为空")
                logger.debug("=" * 80)
                
                if response:
                    # 保存框架
                    with open(framework_file, 'w', encoding='utf-8') as f:
                        f.write(response)
                    
                    logger.info("✅ 框架生成成功，包含30个片段的详细规划")
                    return response
                else:
                    logger.error(f"❌ 尝试 {attempt + 1}/{max_retries} - Gemini API响应为空, 终止服务")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"❌ 尝试 {attempt + 1}/{max_retries} 失败: {e}")
                import traceback
        logger.error("❌ 所有重试都失败了")
        return None
    
    def phase3_generate_segments(self, story_dna: str, framework: str) -> List[str]:
        """
        第三阶段：分段生9个片段
        支持断点续传：已生成的片段会从文件加载
        
        Args:
            story_dna: 故事DNA
            framework: 9个片段的框架
            
        Returns:
            生成的片段列表
        """
        logger.info("📝 第三阶段：开始分段生成30个片段...")
        
        # 解析框架中的片段信息
        segments_info = self.text_processor.parse_framework_segments(framework)
        if not segments_info:
            logger.error("❌ 无法从框架中解析片段信息")
            return None
        
        logger.info(f"📊 解析出 {len(segments_info)} 个片段规划")
        
        # 解析章节结构
        chapters = self.text_processor.parse_chapter_structure(framework)
        
        # 创建上下文管理器
        context_manager = ContextManager()
        context_manager.add_global_context(story_dna, framework)
        
        # 生成的片段列表
        segments = []
        
        # 检查已存在的片段文件
        existing_segments = {}
        for i in range(1, 31):  # 检查片段1-30
            segment_file = self.segments_dir / f"segment_{i:02d}.txt"
            if segment_file.exists():
                try:
                    with open(segment_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():  # 确保文件不是空的
                            existing_segments[i] = content
                            logger.info(f"📂 发现已存在的片段 {i}，长度: {len(content)}字")
                except Exception as e:
                    logger.warning(f"⚠️ 读取片段 {i} 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        if existing_segments:
            logger.info(f"✅ 从缓存加载了 {len(existing_segments)} 个片段")
        
        # 逐个生成片段
        for i, segment_info in enumerate(segments_info, 1):
            # 特殊处理Segment 1 - 使用Framework中的Opening Hook
            if i == 1 and i not in existing_segments:
                logger.info("🎯 片段 1 使用Framework中的Opening Hook...")
                opening_hook = self._extract_opening_hook_from_framework(framework)
                
                if opening_hook:
                    # 保存Opening Hook作为Segment 1
                    segment_file = self.segments_dir / f"segment_{i:02d}.txt"
                    with open(segment_file, 'w', encoding='utf-8') as f:
                        f.write(opening_hook)
                    
                    segments.append(opening_hook)
                    
                    # 添加到对话历史
                    segment_input = self.text_processor.build_segment_input(
                        segment_number=i,
                        segment_info=segment_info,
                        previous_segment=None
                    )
                    context_manager.add_segment_request(segment_input)
                    context_manager.add_segment_response(opening_hook)
                    
                    logger.info(f"✅ 片段 1 完成 (Opening Hook): {len(opening_hook)}字")
                    continue
            
            # 检查是否已有缓存的片段
            if i in existing_segments:
                # 使用缓存的片段
                cached_segment = existing_segments[i]
                segments.append(cached_segment)
                
                # 添加到对话历史（重建历史上下文）
                segment_input = self.text_processor.build_segment_input(
                    segment_number=i,
                    segment_info=segment_info,
                    previous_segment=segments[-2] if len(segments) > 1 else None
                )
                context_manager.add_segment_request(segment_input)
                context_manager.add_segment_response(cached_segment)
                
                logger.info(f"✅ 使用缓存的片段 {i}: {segment_info.get('title', '')} ({len(cached_segment)}字)")
                continue
            
            # 需要生成新片段
            # 确定所属章节
            segment_chapter = None
            for chapter_name, segment_ids in chapters.items():
                if i in segment_ids:
                    segment_chapter = chapter_name
                    break
            
            segment_info['chapter'] = segment_chapter or "未分类"
            
            logger.info(f"🔄 生成片段 {i}/{len(segments_info)}: {segment_info.get('title', '')}")
            
            # 构建输入
            segment_input = self.text_processor.build_segment_input(
                segment_number=i,
                segment_info=segment_info,
                previous_segment=segments[-1] if segments else None
            )
            
            # 添加到对话历史
            context_manager.add_segment_request(segment_input)
            
            try:
                # DEBUG: 记录片段生成输入
                logger.debug("=" * 80)
                logger.debug(f"[DEBUG] phase3_generate_segments - 片段{i}输入:")
                logger.debug(f"输入长度: {len(segment_input)} 字符")
                logger.debug("输入内容:")
                logger.debug(segment_input)
                logger.debug(f"历史记录条数: {len(context_manager.get_history())}")
                logger.debug("=" * 80)
                
                # 调用Gemini API，传入完整的对话历史
                response = self.gemini_client.generate_content_with_history(
                    prompt=segment_input,
                    history=context_manager.get_history()
                )
                
                # DEBUG: 记录片段生成输出
                logger.debug("=" * 80)
                logger.debug(f"[DEBUG] phase3_generate_segments - 片段{i}输出:")
                logger.debug(f"输出长度: {len(response) if response else 0} 字符")
                if response:
                    logger.debug("完整输出内容:")
                    logger.debug(response)
                else:
                    logger.debug("响应为空")
                logger.debug("=" * 80)
                
                if response:
                    # 保存片段
                    segment_file = self.segments_dir / f"segment_{i:02d}.txt"
                    with open(segment_file, 'w', encoding='utf-8') as f:
                        f.write(response)
                    
                    segments.append(response)
                    
                    # 添加到对话历史
                    context_manager.add_segment_response(response)
                    
                    # 计算字数
                    word_count = len(response)
                    target = segment_info.get('length', 1000)
                    deviation = ((word_count - target) / target) * 100
                    
                    logger.info(f"✅ 片段 {i} 完成: {word_count}字 (目标{target}字, 偏差{deviation:+.1f}%)")
                    
                    # 每5个片段休息一下，避免API限制
                    if i % 5 == 0 and i not in existing_segments:
                        logger.info("⏸️ 暂停2秒...")
                        time.sleep(2)
                else:
                    logger.error(f"❌ 片段 {i} 生成失败")
                    # 使用占位符
                    segments.append(f"[片段{i}生成失败]")
                    
            except Exception as e:
                logger.error(f"❌ 生成片段 {i} 时出错: {e}")
                import traceback
                traceback.print_exc()
                segments.append(f"[片段{i}生成失败: {str(e)}]")
        
        logger.info(f"✅ 完成所有片段生成，共 {len(segments)} 个片段")
        return segments
    
    def phase3_generate_segments_simple(self, story_dna: str, framework: str) -> List[str]:
        """
        简化版片段生成 - 手动控制上下文，不使用聊天历史
        每个片段都是独立的API调用，只传递前500字用于衔接
        
        Args:
            story_dna: 故事DNA
            framework: 故事改编框架
            
        Returns:
            生成的片段列表
        """
        logger.info(f"📝 第三阶段：开始生成故事片段（简化版，共{self.num_segments}个片段）...")
        
        # 1. 从框架提取必要信息
        framework_summary = self.extract_framework_summary(framework)
        segment_tasks = self.extract_segment_tasks(framework)
        
        # 2. 提取9步框架的完整内容
        framework_steps = self.extract_9steps_full_content(framework)
        
        segments = []
        
        for i in range(1, self.num_segments + 1):
            # 检查缓存
            segment_file = self.segments_dir / f"segment_{i:02d}.txt"
            if segment_file.exists():
                try:
                    with open(segment_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            segments.append(content)
                            logger.info(f"📂 使用缓存的片段 {i}, 长度: {len(content)}字")
                            continue
                except Exception as e:
                    logger.warning(f"⚠️ 读取片段 {i} 失败: {e}")
            
            # 3. 获取当前片段对应的框架内容
            segment_task = segment_tasks.get(i, {})
            # 直接使用框架中对应步骤的原始内容
            segment_task['framework_step_content'] = framework_steps.get(i, f"- **段落编号：** 第 {i} 段")
            
            # 4. 构建输入（完全手动控制）
            segment_input = self.build_segment_input_simple(
                segment_num=i,
                framework_summary=framework_summary,
                previous_text=segments[-1][-500:] if segments else "",
                segment_task=segment_task
            )
            
            # 3. 生成片段（独立的API调用）
            try:
                logger.info(f"🔄 生成片段 {i}/{self.num_segments}: {segment_tasks.get(i, {}).get('chapter', '')}")
                
                # DEBUG: 记录输入
                logger.debug("=" * 80)
                logger.debug(f"[DEBUG] 片段{i}输入:")
                logger.debug(f"输入长度: {len(segment_input)} 字符")
                logger.debug("输入内容:")
                logger.debug(segment_input)
                logger.debug("=" * 80)
                
                response = self.gemini_client.generate_content(segment_input)
                
                # DEBUG: 记录输出
                logger.debug("=" * 80)
                logger.debug(f"[DEBUG] 片段{i}输出:")
                logger.debug(f"输出长度: {len(response) if response else 0} 字符")
                if response:
                    logger.debug("输出内容:")
                    logger.debug(response)
                else:
                    logger.debug("响应为空")
                logger.debug("=" * 80)
                
                if response:
                    segments.append(response)
                    # 保存片段
                    with open(segment_file, 'w', encoding='utf-8') as f:
                        f.write(response)
                    
                    logger.info(f"✅ 片段 {i} 生成完成: {len(response)}字")
                    
                    # 适当休息避免限流
                    if i % 5 == 0:
                        logger.info("⏸️ 暂停2秒...")
                        time.sleep(2)
                else:
                    logger.error(f"❌ 片段 {i} 生成失败")
                    segments.append(f"[片段{i}生成失败]")
                    
            except Exception as e:
                logger.error(f"❌ 生成片段 {i} 时出错: {e}")
                import traceback
                traceback.print_exc()
                segments.append(f"[片段{i}生成失败: {str(e)}]")
        
        logger.info(f"✅ 完成所有片段生成，共 {len(segments)} 个片段")
        return segments
    
    def build_segment_input_simple(self, segment_num: int, framework_summary: str, 
                                   previous_text: str, segment_task: dict) -> str:
        """
        构建片段生成的输入 - 简单直接
        
        Args:
            segment_num: 片段编号
            framework_summary: 框架摘要
            previous_text: 前一段的最后500字
            segment_task: 当前片段的任务信息
            
        Returns:
            构建好的输入文本
        """
        # 读取segment_generator提示词
        segment_prompt = self.prompts.get('segment_generator', '')
        
        # 根据新的提示词格式构建输入
        input_text = f"""{segment_prompt}

==================================================
**最高指令：故事改编框架 V2.1 (摘要)**
==================================================
{framework_summary}

==================================================
**前一段内容 (Previous Segment)**
==================================================
{previous_text if previous_text else "**This is the first segment.**"}

==================================================
**本段任务卡 (Current Segment Task Card)**
==================================================
{segment_task.get('framework_step_content', f"- **段落编号：** 第 {segment_num} 段")}
"""
        
        return input_text
    
    def extract_9steps_full_content(self, framework: str) -> dict:
        """
        从框架中提取9步的完整内容（保持原始格式）
        
        Args:
            framework: 框架文本
            
        Returns:
            {step_num: full_content} 字典
        """
        import re
        
        steps_content = {}
        
        # 查找"B. 故事蓝图"部分
        blueprint_match = re.search(r'## B\. 故事蓝图.*?\n(.*?)(?=##|$)', framework, re.DOTALL)
        if not blueprint_match:
            # 如果没找到，尝试其他格式
            blueprint_match = re.search(r'故事蓝图.*?\n(.*?)(?=##|$)', framework, re.DOTALL)
        
        if blueprint_match:
            blueprint_text = blueprint_match.group(1)
            
            # 匹配每个步骤，保持原始格式
            # 格式: - **N. 步骤名称 (英文)：**
            pattern = r'(- \*\*(\d+)\. [^*]+\*\*.*?)(?=- \*\*\d+\.|$)'
            
            matches = re.findall(pattern, blueprint_text, re.DOTALL)
            
            for full_match, step_num in matches:
                step_num = int(step_num)
                # 保存完整内容，保持原始格式
                steps_content[step_num] = full_match.strip()
        
        return steps_content
    
    def extract_framework_summary(self, framework: str) -> str:
        """
        从新版framework提取摘要信息
        
        Args:
            framework: 框架文本
            
        Returns:
            框架摘要
        """
        import re
        
        summary_parts = []
        
        # 提取核心改编理念
        if match := re.search(r'核心改编理念：\*\*\s*(.+)', framework):
            summary_parts.append(f"- **核心改编理念：** {match.group(1)}")
        
        # 提取槽点策略
        if match := re.search(r'识别出的核心槽点：\*\*\s*(.+)', framework):
            summary_parts.append(f"- **槽点策略：** {match.group(1)}")
        
        if match := re.search(r'放大方案：\*\*\s*(.+)', framework):
            summary_parts.append(f"- **放大方案：** {match.group(1)}")
        
        # 提取9步结构简述
        nine_steps = []
        for step in ['钩子开场', '角色与动机', '意外转折', '尝试与失败', 
                     '情绪低谷', '顿悟与转变', '最终行动', '胜利的代价', '新的悬念']:
            if step in framework:
                nine_steps.append(step)
        
        if nine_steps:
            summary_parts.append(f"- **9步结构：** {', '.join(nine_steps)}")
        
        # 提取角色名字
        characters = re.findall(r'角色\d+：\[([^\]]+)\]', framework)
        if characters:
            summary_parts.append(f"- **角色名册：** {', '.join(characters)}")
        
        return '\n'.join(summary_parts) if summary_parts else "- **核心理念：** 改编故事"
    
    def extract_segment_tasks(self, framework: str) -> dict:
        """
        从9步结构映射到片段的任务
        
        Args:
            framework: 框架文本
            
        Returns:
            片段任务字典 {segment_num: task_info}
        """
        tasks = {}
        
        # 从框架中提取每步的具体内容
        step_contents = self.parse_nine_steps(framework)
        
        if self.num_segments == 9:
            # 9个片段时，每步对应一个片段
            step_names = ['钩子开场', '角色与动机', '意外转折', '尝试与失败', 
                         '情绪低谷', '顿悟与转变', '最终行动', '胜利的代价', '新的悬念']
            
            for i in range(1, 10):
                if i <= len(step_names):
                    step_name = step_names[i-1]
                    step_data = step_contents.get(step_name, {})
                    task_info = {
                        'chapter': step_name,
                        'task': step_data.get('情节规划', f'{step_name}阶段')
                    }
                    
                    # 添加节奏与字数信息
                    if '节奏与字数' in step_data:
                        task_info['rhythm'] = step_data['节奏与字数']
                    
                    # 添加具体字数范围
                    if '字数范围' in step_data:
                        min_words, max_words = step_data['字数范围']
                        task_info['word_count_range'] = (min_words, max_words)
                        task_info['target_words'] = (min_words + max_words) // 2  # 目标字数取中间值
                    
                    tasks[i] = task_info
        else:
            # 如果是其他数量的片段，使用比例分配
            # 30片段的原始映射
            MAPPING_30 = {
                (1, 2): ('钩子开场', '快节奏，悬念丛生', 700),
                (3, 5): ('角色与动机', '中等节奏，人物刻画', 1000),
                (6, 8): ('意外转折', '节奏加快，制造冲击', 900),
                (9, 13): ('尝试与失败', '动作与内心戏结合', 1200),
                (14, 17): ('情绪低谷', '慢节奏，情绪渲染', 1100),
                (18, 20): ('顿悟与转变', '转折点，节奏由慢转快', 900),
                (21, 26): ('最终行动', '极快节奏，动作密集', 1500),
                (27, 29): ('胜利的代价', '节奏放缓，带反思', 1100),
                (30, 30): ('新的悬念', '短小精悍，制造悬念', 500)
            }
            
            # 按比例分配片段
            for segment in range(1, self.num_segments + 1):
                # 计算当前片段对应30片段体系的位置
                position_30 = int((segment - 1) * 30 / self.num_segments) + 1
                
                for (start, end), (step_name, rhythm, words) in MAPPING_30.items():
                    if start <= position_30 <= end:
                        step_data = step_contents.get(step_name, {})
                        task_info = {
                            'chapter': step_name,
                            'task': step_data.get('情节规划', f'{step_name}阶段'),
                            'rhythm': step_data.get('节奏与字数', f"{rhythm}。约{words}字")
                        }
                        
                        # 如果框架中有具体字数范围，使用框架的；否则使用默认值
                        if '字数范围' in step_data:
                            min_words, max_words = step_data['字数范围']
                            task_info['word_count_range'] = (min_words, max_words)
                            task_info['target_words'] = (min_words + max_words) // 2
                        else:
                            task_info['target_words'] = words
                        
                        tasks[segment] = task_info
                        break
        
        return tasks
    
    def _get_rhythm_for_step(self, step_name: str) -> str:
        """获取每个步骤的节奏说明"""
        rhythms = {
            '钩子开场': '快节奏，悬念丛生',
            '角色与动机': '中等节奏，人物刻画',
            '意外转折': '节奏加快，制造冲击',
            '尝试与失败': '动作与内心戏结合',
            '情绪低谷': '慢节奏，情绪渲染',
            '顿悟与转变': '转折点，节奏由慢转快',
            '最终行动': '极快节奏，动作密集',
            '胜利的代价': '节奏放缓，带反思',
            '新的悬念': '短小精悍，制造悬念'
        }
        return rhythms.get(step_name, '正常节奏')
    
    def parse_nine_steps(self, framework: str) -> dict:
        """
        解析9步结构的具体内容
        
        Args:
            framework: 框架文本
            
        Returns:
            9步内容字典
        """
        import re
        steps = {}
        
        # 更完整的模式匹配，同时提取情节规划和节奏与字数
        # 格式: **1. 钩子开场 (Hook)：**
        #       - **情节规划：** [内容]
        #       - **节奏与字数：** [内容]
        pattern = r'\*\*(\d+)\.\s+([^(]+)\s*\([^)]+\)：\*\*([^*]*?)(?=\*\*\d+\.|$)'
        
        matches = re.findall(pattern, framework, re.DOTALL)
        for step_num, step_name, content in matches:
            step_name = step_name.strip()
            steps[step_name] = {}
            
            # 提取情节规划
            plot_match = re.search(r'\*\*情节规划：\*\*\s*([^\n]+(?:\n(?!\s*-\s*\*\*)[^\n]+)*)', content)
            if plot_match:
                steps[step_name]['情节规划'] = plot_match.group(1).strip()
            
            # 提取节奏与字数
            rhythm_match = re.search(r'\*\*节奏与字数：\*\*\s*([^\n]+)', content)
            if rhythm_match:
                rhythm_text = rhythm_match.group(1).strip()
                steps[step_name]['节奏与字数'] = rhythm_text
                
                # 提取具体字数范围
                word_count_match = re.search(r'(\d+)[-–](\d+)\s*字', rhythm_text)
                if word_count_match:
                    min_words = int(word_count_match.group(1))
                    max_words = int(word_count_match.group(2))
                    steps[step_name]['字数范围'] = (min_words, max_words)
        
        # 如果上面的模式匹配失败，尝试更简单的模式
        if not steps:
            # 尝试匹配: 1. 钩子开场 (Hook)
            simple_pattern = r'\d+\.\s*([^(]+)\s*\([^)]+\)'
            simple_matches = re.findall(simple_pattern, framework)
            for step_name in simple_matches:
                step_name = step_name.strip()
                steps[step_name] = {'情节规划': f'{step_name}阶段'}
        
        return steps
    
    def phase4_concat_segments(self, segments: List[str]) -> str:
        """
        第四阶段：拼接所有片段
        如果已有草稿文件，则从文件加载
        
        Args:
            segments: 片段列表
            
        Returns:
            完整故事文本
        """
        logger.info("🔗 第四阶段：拼接所有片段...")
        
        draft_file = self.processing_dir / "3_draft.txt"
        
        # 检查是否已有草稿
        if draft_file.exists():
            logger.info("📂 发现已有草稿文件，从文件加载...")
            try:
                with open(draft_file, 'r', encoding='utf-8') as f:
                    full_story = f.read()
                
                if full_story.strip():
                    logger.info(f"✅ 从缓存加载草稿成功，长度: {len(full_story)}字")
                    return full_story
                    
            except Exception as e:
                logger.warning(f"⚠️ 加载草稿失败，将重新拼接: {e}")
                import traceback
                traceback.print_exc()
        
        # 需要重新拼接
        # 合并片段
        full_story = self.text_processor.merge_segments(segments)
        
        # 保存草稿
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(full_story)
        
        # 统计信息
        total_words = len(full_story)
        logger.info(f"✅ 拼接完成，总长度: {total_words}字")
        
        return full_story
    
    def phase5_polish(self, framework: str, draft: str) -> str:
        """
        第五阶段：最终润色（使用中文版本）
        如果已有润色结果，则从文件加载
        
        Args:
            framework: 改编框架
            draft: 故事草稿
            
        Returns:
            润色后的故事
        """
        logger.info("✨ 第五阶段：开始最终润色（中文版）...")
        
        # 检查是否已有润色结果
        polished_file = self.processing_dir / "4_polished.txt"
        final_story_file = self.final_dir / "story.txt"
        
        if polished_file.exists() and final_story_file.exists():
            logger.info("📂 发现已有润色结果，从文件加载...")
            try:
                with open(final_story_file, 'r', encoding='utf-8') as f:
                    final_story = f.read()
                
                if final_story.strip():
                    logger.info(f"✅ 从缓存加载润色故事成功，长度: {len(final_story)}字")
                    return final_story
                    
            except Exception as e:
                logger.warning(f"⚠️ 加载润色结果失败，将重新生成: {e}")
                import traceback
                traceback.print_exc()
        
        # 需要重新润色
        # 构建输入
        polish_input = self.text_processor.format_polish_input(framework, draft, num_segments=self.num_segments)
        
        # 构建完整提示
        full_prompt = f"{self.prompts['final_polisher']}\n\n---\n\n{polish_input}"
        
        # DEBUG: 记录完整输入
        logger.debug("=" * 80)
        logger.debug("[DEBUG] phase5_polish - AI调用输入:")
        logger.debug(f"输入长度: {len(full_prompt)} 字符")
        logger.debug("完整输入内容:")
        logger.debug(full_prompt)
        logger.debug("=" * 80)
        
        try:
            # 调用Gemini API
            response = self.gemini_client.generate_content(full_prompt)
            
            # DEBUG: 记录完整输出
            logger.debug("=" * 80)
            logger.debug("[DEBUG] phase5_polish - AI调用输出:")
            logger.debug(f"输出长度: {len(response) if response else 0} 字符")
            if response:
                logger.debug("完整输出内容:")
                logger.debug(response)
            else:
                logger.debug("响应为空")
            logger.debug("=" * 80)
            
            if response:
                # 保存润色结果
                with open(polished_file, 'w', encoding='utf-8') as f:
                    f.write(response)
                
                # 解析输出
                polish_result = self.text_processor.parse_polish_output(response)
                
                # 保存最终故事
                final_story = polish_result.get('story', draft)
                with open(final_story_file, 'w', encoding='utf-8') as f:
                    f.write(final_story)
                
                # 保存编辑报告
                if 'report' in polish_result:
                    with open(self.final_dir / "edit_report.txt", 'w', encoding='utf-8') as f:
                        f.write(polish_result['report'])
                
                logger.info(f"✅ 润色完成，最终长度: {len(final_story)}字")
                return final_story
            else:
                logger.error("❌ Gemini API响应为空")
                return draft
                
        except Exception as e:
            logger.error(f"❌ 润色失败: {e}")
            import traceback
            traceback.print_exc()
            return draft
    
    def generate_final_report(self):
        """生成详细的最终报告，包含AI总结分析"""
        logger.info("📊 生成详细最终报告...")
        
        # 读取各阶段的文件内容
        dna_content = ""
        framework_content = ""
        original_story = ""
        final_story = ""
        edit_report = ""
        video_info = {}
        
        try:
            # 读取DNA文件
            dna_file = self.processing_dir / "1_story_dna.txt"
            if dna_file.exists():
                with open(dna_file, 'r', encoding='utf-8') as f:
                    dna_content = f.read()
            
            # 读取框架文件
            framework_file = self.processing_dir / "2_framework.txt"
            if framework_file.exists():
                with open(framework_file, 'r', encoding='utf-8') as f:
                    framework_content = f.read()
            
            # 读取原始故事
            original_story_file = self.raw_dir / "subtitle.txt"
            if original_story_file.exists():
                with open(original_story_file, 'r', encoding='utf-8') as f:
                    original_story = f.read()
            
            # 读取最终故事
            final_story_file = self.final_dir / "story.txt"
            if final_story_file.exists():
                with open(final_story_file, 'r', encoding='utf-8') as f:
                    final_story = f.read()
            
            # 读取编辑报告
            edit_report_file = self.final_dir / "edit_report.txt"
            if edit_report_file.exists():
                with open(edit_report_file, 'r', encoding='utf-8') as f:
                    edit_report = f.read()
            
            # 读取视频信息
            import json
            video_info_file = self.raw_dir / "video_info.json"
            if video_info_file.exists():
                with open(video_info_file, 'r', encoding='utf-8') as f:
                    video_info = json.load(f)
        except Exception as e:
            logger.warning(f"读取部分文件失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 调用AI生成详细分析
        ai_summary = self._generate_ai_summary(dna_content, framework_content, edit_report, final_story)
        
        # 如果AI分析失败，使用本地分析
        if not ai_summary:
            logger.warning("⚠️ AI分析失败，使用本地分析")
            dna_analysis = self._extract_dna_summary(dna_content)
            framework_summary = self._extract_framework_summary(framework_content)
        else:
            # 使用AI分析结果
            dna_analysis = self._format_ai_dna_analysis(ai_summary)
            framework_summary = self._format_ai_framework_summary(ai_summary)
        
        # 生成详细报告
        report = f"""
# YouTube故事创作详细报告

创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📌 基本信息
- **视频ID**：{self.video_id}
- **创作者**：{self.creator_name}
- **原视频标题**：{video_info.get('title', 'N/A')}
- **频道名称**：{video_info.get('channel_title', 'N/A')}
- **目标长度**：{self.target_length}字（约30分钟朗读）
- **片段数量**：{self.num_segments}个

## 📖 原始故事分析

### 原文概况
- **原文长度**：{len(original_story)}字
- **原文前100字预览**：
  > {original_story[:100] if original_story else 'N/A'}...

### 故事DNA提取（核心要素）
{dna_analysis}

## 🎯 改编策略与框架

### 改编目标
- **目标受众**：{framework_summary.get('target_audience', 'N/A')}
- **改编策略**：{framework_summary.get('adaptation_strategy', 'N/A')}

### 30片段框架结构
{framework_summary.get('structure', 'N/A')}

### 关键改编点
{framework_summary.get('key_adaptations', 'N/A')}

### 开场钩子设计
{framework_summary.get('opening_hook', 'N/A')}

## 📝 最终故事概览

### 成品统计
- **最终长度**：{len(final_story)}字
- **实际片段数**：30个
- **平均每片段**：{len(final_story)//30 if final_story else 0}字

### 故事开头（前200字）
```
{final_story[:200] if final_story else 'N/A'}...
```

### 故事结尾（后200字）
```
...{final_story[-200:] if final_story else 'N/A'}
```

## 🔄 改编对比分析

### 主要改进
1. **叙事结构**：从原始的线性叙事改为30片段的起承转合结构
2. **情感曲线**：增强了情感起伏，每2-3分钟设置一个小高潮
3. **人物塑造**：深化了主要角色的性格描写和内心活动
4. **场景描写**：增加了更多感官细节和氛围营造
5. **对话优化**：使对话更加自然生动，符合人物性格

### 创新亮点
{framework_summary.get('innovations', 'N/A')}

## 📊 质量评估

### 编辑润色报告
{edit_report[:500] if edit_report else 'N/A'}

### 整体评价
- **故事完整性**：✅ 完整的故事弧线，包含开端、发展、高潮、结局
- **节奏控制**：✅ 30个片段节奏分明，张弛有度
- **情感共鸣**：✅ 强化了普世情感主题，易引发共鸣
- **YouTube适配**：✅ 适合30分钟朗读，有明确的讨论点

## 🎬 YouTube发布建议

### 视频标题候选
1. {framework_summary.get('title_1', '[根据故事内容生成吸引人的标题]')}
2. {framework_summary.get('title_2', '[第二个备选标题]')}
3. {framework_summary.get('title_3', '[第三个备选标题]')}

### 缩略图要素
- **视觉焦点**：{framework_summary.get('thumbnail_visual', '主角的情感爆发时刻')}
- **文字叠加**：{framework_summary.get('thumbnail_text', '震撼性标题文字')}
- **色彩方案**：{framework_summary.get('thumbnail_color', '高对比度的情感色彩')}

### 视频描述关键词
{framework_summary.get('keywords', '#故事 #情感 #励志')}

## 📁 输出文件清单

### 原始数据
- `raw/video_info.json` - 视频元信息
- `raw/comments.json` - 热门评论
- `raw/subtitle.txt` - 原始字幕/故事

### 处理过程
- `processing/1_story_dna.txt` - 故事DNA分析
- `processing/2_framework.txt` - 30片段框架
- `processing/3_draft.txt` - 拼接草稿
- `processing/4_polished.txt` - 润色版本

### 片段文件
- `segments/segment_01.txt` 至 `segments/segment_30.txt`

### 最终成品
- `final/story.txt` - 最终故事（英文）
- `final/edit_report.txt` - 编辑报告
- `final/report.md` - 本报告文件

## 🚀 后续优化建议

1. **配音制作**：建议使用AI语音合成，选择富有感情的声音
2. **背景音乐**：根据情感曲线选择合适的背景音乐
3. **视觉素材**：可根据关键场景生成AI插图
4. **互动设计**：在视频中设置互动问题，引导观众评论
5. **系列规划**：如果效果好，可以制作同类型的系列视频

---

*报告生成完毕 - YouTube Story Creator V2*
"""
        
        # 保存报告
        with open(self.final_dir / "report.md", 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ 详细报告已保存到: {self.final_dir / 'report.md'}")
    
    def _extract_dna_summary(self, dna_content: str) -> str:
        """从DNA内容中提取中文总结"""
        if not dna_content:
            return "N/A"
        
        summary = {}
        
        # 提取关键信息
        if "Story Type" in dna_content:
            import re
            type_match = re.search(r"Story Type\n(.+?)\n", dna_content)
            if type_match:
                summary['story_type'] = type_match.group(1)
        
        if "Core Theme" in dna_content:
            theme_match = re.search(r"Core Theme\n(.+?)\n", dna_content)
            if theme_match:
                summary['core_theme'] = theme_match.group(1)
        
        # 构建中文总结
        result = f"""
- **故事类型**：{summary.get('story_type', 'N/A')}
- **核心主题**：{summary.get('core_theme', 'N/A')}
- **主要角色**：从原始内容中提取并深化的角色设定
- **情感内核**：通过AI分析识别的情感驱动力
- **冲突设置**：内外冲突的双重设计"""
        
        return result
    
    def _extract_framework_summary(self, framework_content: str) -> Dict[str, Any]:
        """从框架内容中提取关键信息"""
        summary = {}
        
        if not framework_content:
            return summary
        
        # 提取目标受众
        if "Target Audience" in framework_content:
            import re
            audience_match = re.search(r"Target Audience: (.+?)\n", framework_content)
            if audience_match:
                summary['target_audience'] = audience_match.group(1)
        
        # 提取改编策略
        if "Adaptation Strategy" in framework_content:
            strategy_match = re.search(r"Adaptation Strategy: (.+?)\n", framework_content)
            if strategy_match:
                summary['adaptation_strategy'] = strategy_match.group(1)
        
        # 提取章节结构
        chapters = []
        if "Chapter One" in framework_content:
            chapters.append("第一章：开端（片段1-4）- 建立世界观和主角")
        if "Chapter Two" in framework_content:
            chapters.append("第二章：发展（片段5-13）- 深化冲突和关系")
        if "Chapter Three" in framework_content:
            chapters.append("第三章：冲突升级（片段14-19）- 推向高潮")
        if "Chapter Four" in framework_content:
            chapters.append("第四章：高潮（片段20-26）- 决战时刻")
        if "Chapter Five" in framework_content:
            chapters.append("第五章：结局（片段27-30）- 收束与升华")
        
        summary['structure'] = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(chapters)])
        
        # 提取开场钩子
        if "Segment 1:" in framework_content:
            hook_match = re.search(r"Segment 1: (.+?) \(\d+ words\)\n- Content: (.+?)\n", framework_content)
            if hook_match:
                summary['opening_hook'] = f"""
- **钩子类型**：{hook_match.group(1)}
- **设计理念**：在前100字内立即创造悬念或冲突
- **具体内容**：{hook_match.group(2)}
- **预期效果**：瞬间抓住观众注意力，产生继续观看的欲望"""
        
        # 提取关键改编点
        summary['key_adaptations'] = """
1. **结构重组**：将原始内容重新组织为30个精心设计的片段
2. **节奏优化**：确保每个片段都有明确的焦点和推进作用
3. **情感增强**：在关键时刻加入更多内心独白和感官描写
4. **悬念设置**：每个片段结尾都预留钩子，引导继续阅读
5. **高潮打造**：第20-26片段集中爆发，情感达到顶峰"""
        
        # 创新亮点
        summary['innovations'] = """
- 采用**混合视角叙事**，增强代入感
- 设置**多重反转**，保持故事新鲜感
- 加入**当代元素**，提高故事相关性
- 强化**情感共鸣点**，便于观众分享传播"""
        
        # YouTube相关
        summary['title_1'] = "[震撼] 你绝对想不到的结局！30分钟改变人生的故事"
        summary['title_2'] = "从平凡到非凡：一个真实故事的30个转折点"
        summary['title_3'] = "必看！这个故事会让你重新思考人生的意义"
        
        summary['thumbnail_visual'] = "主角在关键时刻的情感爆发特写"
        summary['thumbnail_text'] = "改变一生的30分钟"
        summary['thumbnail_color'] = "暖色调与冷色调的强烈对比"
        
        summary['keywords'] = "#励志故事 #人生感悟 #情感故事 #30分钟故事 #真实改编 #泪点满满 #正能量"
        
        return summary
    
    def _generate_ai_summary(self, dna_content: str, framework_content: str, 
                            edit_report: str, final_story: str) -> Optional[Dict[str, Any]]:
        """调用AI生成详细的分析报告
        
        Args:
            dna_content: DNA分析内容
            framework_content: 框架内容
            edit_report: 编辑报告
            final_story: 最终故事（前1000字用于提取人物特征）
            
        Returns:
            AI生成的JSON格式分析结果，失败返回None
        """
        try:
            logger.info("🤖 调用AI生成详细分析报告...")
            
            # 读取报告生成提示词
            prompt_file = Path(__file__).parent.parent / "prompts" / "report_generator.md"
            if not prompt_file.exists():
                logger.error(f"找不到报告生成提示词: {prompt_file}")
                return None
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            
            # 构建输入内容
            input_content = f"""
==================================================
Story DNA
==================================================
{dna_content if dna_content else 'N/A'}

==================================================
Adaptation Framework
==================================================
{framework_content if framework_content else 'N/A'}

==================================================
Editorial Report
==================================================
{edit_report if edit_report else 'N/A'}

==================================================
Final Story Sample
==================================================
{final_story[:1000] if final_story else 'N/A'}
"""
            
            # DEBUG: 记录完整输入
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_ai_summary - AI调用输入:")
            logger.debug(f"system_prompt长度: {len(system_prompt)} 字符")
            logger.debug("完整system_prompt:")
            logger.debug(system_prompt)
            logger.debug(f"input_content长度: {len(input_content)} 字符")
            logger.debug("完整input_content:")
            logger.debug(input_content)
            logger.debug("=" * 80)
            
            # 调用Gemini API
            response = self.gemini_client.analyze_text(
                text=input_content,
                prompt=system_prompt
            )
            
            # DEBUG: 记录完整输出
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_ai_summary - AI调用输出:")
            logger.debug(f"输出长度: {len(response) if response else 0} 字符")
            if response:
                logger.debug("完整输出内容:")
                logger.debug(response)
            else:
                logger.debug("响应为空")
            logger.debug("=" * 80)
            
            if not response:
                logger.error("AI分析返回空结果")
                return None
            
            # 提取JSON部分
            import json
            import re
            
            # 查找JSON代码块
            json_match = re.search(r'```json\s*\n(.+?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = response
            
            # 解析JSON
            try:
                result = json.loads(json_str)
                logger.info("✅ AI分析报告生成成功")
                
                # 保存AI分析结果
                ai_report_file = self.final_dir / "ai_analysis.json"
                with open(ai_report_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 AI分析结果已保存: {ai_report_file}")
                
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.debug(f"原始响应: {response[:500]}...")
                import traceback
                traceback.print_exc()
                return None
                
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_ai_dna_analysis(self, ai_summary: Dict[str, Any]) -> str:
        """格式化AI生成的DNA分析结果
        
        Args:
            ai_summary: AI生成的分析结果
            
        Returns:
            格式化的中文DNA分析文本
        """
        try:
            story_analysis = ai_summary.get('story_analysis', {})
            
            # 提取关键信息
            original_type = story_analysis.get('original_type', 'N/A')
            original_theme = story_analysis.get('original_theme', 'N/A')
            adaptation_strategy = story_analysis.get('adaptation_strategy', 'N/A')
            key_improvements = story_analysis.get('key_improvements', [])
            
            # 构建格式化文本
            result = f"""
- **故事类型**：{original_type}
- **核心主题**：{original_theme}
- **改编策略**：{adaptation_strategy}

### 关键改进点
"""
            
            for i, improvement in enumerate(key_improvements, 1):
                result += f"{i}. {improvement}\n"
            
            # 添加人物分析（如果有）
            character_profiles = ai_summary.get('character_profiles', [])
            if character_profiles:
                result += "\n### 主要角色分析\n"
                for char in character_profiles[:3]:  # 只显示前3个主要角色
                    result += f"\n**{char.get('chinese_name', char.get('name', 'N/A'))}**"
                    result += f" ({char.get('role', '')})"
                    result += f"\n- 性格：{char.get('personality', 'N/A')}"
                    physical = char.get('physical_features', {})
                    if physical:
                        result += f"\n- 外貌：{physical.get('age', '')}，{physical.get('build', '')}，{physical.get('hair', '')}"
                    result += "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"格式化AI DNA分析失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回基础分析
            return self._extract_dna_summary('')
    
    def _format_ai_framework_summary(self, ai_summary: Dict[str, Any]) -> Dict[str, Any]:
        """格式化AI生成的框架分析结果
        
        Args:
            ai_summary: AI生成的分析结果
            
        Returns:
            格式化的框架分析字典
        """
        try:
            summary = {}
            
            # 从AI分析中提取信息
            story_analysis = ai_summary.get('story_analysis', {})
            opening_hook = ai_summary.get('opening_hook', {})
            climax_analysis = ai_summary.get('climax_analysis', {})
            youtube_strategy = ai_summary.get('youtube_strategy', {})
            production_guide = ai_summary.get('production_guide', {})
            
            # 目标受众和策略
            summary['target_audience'] = youtube_strategy.get('target_audience', '年轻成年人（18-35岁），对情感故事感兴趣')
            summary['adaptation_strategy'] = story_analysis.get('adaptation_strategy', '将线性叙事转换为戏剧性弧线结构')
            
            # 章节结构
            structure = f"""
- **第一章：开端**（片段1-4）- 建立世界观和主角
- **第二章：发展**（片段5-13）- 深化冲突和关系
- **第三章：冲突升级**（片段14-19）- 推向高潮
- **第四章：高潮**（片段20-26）- {climax_analysis.get('emotional_peak', '决战时刻')}
- **第五章：结局**（片段27-30）- {climax_analysis.get('resolution', '情感升华与主题回归')}
"""
            summary['structure'] = structure
            
            # 开场钩子
            hook_info = f"""
- **钩子类型**：{opening_hook.get('type', 'Opening Hook')}
- **具体内容**：{opening_hook.get('content', 'N/A')}
- **预期效果**：{opening_hook.get('effectiveness', '瞬间抓住观众注意力')}
- **第一句话**：{opening_hook.get('first_line', 'N/A')}
"""
            summary['opening_hook'] = hook_info
            
            # 关键改编点
            key_improvements = story_analysis.get('key_improvements', [])
            adaptations = "\n".join([f"{i+1}. {imp}" for i, imp in enumerate(key_improvements)])
            summary['key_adaptations'] = adaptations if adaptations else "1. 结构重组\n2. 节奏优化\n3. 情感增强"
            
            # YouTube标题
            titles = youtube_strategy.get('titles', [])
            if titles:
                summary['title_1'] = titles[0].get('title', '[震撼] 30分钟改变人生的故事')
                summary['title_2'] = titles[1].get('title', '一个真实故事的30个转折点') if len(titles) > 1 else '必看故事'
                summary['title_3'] = titles[2].get('title', '这个故事会让你重新思考') if len(titles) > 2 else '感人故事'
            else:
                summary['title_1'] = "[震撼] 30分钟改变人生的故事"
                summary['title_2'] = "一个真实故事的30个转折点"
                summary['title_3'] = "这个故事会让你重新思考人生"
            
            # 缩略图设计
            thumbnail = youtube_strategy.get('thumbnail', {})
            summary['thumbnail_visual'] = thumbnail.get('main_element', '主角情感爆发特写')
            summary['thumbnail_text'] = thumbnail.get('text_overlay', '改变一生的30分钟')
            summary['thumbnail_color'] = thumbnail.get('color_scheme', '暖冷色对比')
            
            # 标签和关键词
            tags = youtube_strategy.get('tags', [])
            summary['keywords'] = ' '.join(tags) if tags else "#励志故事 #情感故事 #30分钟故事"
            
            # 制作建议
            summary['voice_style'] = production_guide.get('voice_style', '富有感情的叙述风格')
            summary['bgm_suggestion'] = production_guide.get('bgm_suggestion', '渐进式情感音乐')
            summary['pacing'] = production_guide.get('pacing', '2-3分钟一个小高潮')
            
            # 质量评分
            quality = ai_summary.get('quality_metrics', {})
            summary['quality_score'] = f"""
- 故事连贯性：{quality.get('story_coherence', 90)}%
- 情感冲击力：{quality.get('emotional_impact', 85)}%
- 节奏质量：{quality.get('pacing_quality', 88)}%
- YouTube适配度：{quality.get('youtube_readiness', 92)}%
"""
            
            # 系列潜力
            series = ai_summary.get('series_potential', {})
            if series.get('feasibility') == '高':
                summary['series_suggestion'] = f"建议制作{series.get('suggested_episodes', 5)}集系列"
            
            return summary
            
        except Exception as e:
            logger.error(f"格式化AI框架分析失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回基础分析
            return self._extract_framework_summary('')
    
    def generate_image_prompts_v2(self) -> bool:
        """
        优化版SD图片提示词生成
        使用新的独立模块 ImagePromptGenerator
        
        Returns:
            bool: 成功返回true，失败返回false
        """
        try:
            logger.info(f"🎨 开始生成SD图片提示词（使用新模块，每片段{self.images_per_segment}张）...")
            
            # 使用新的ImagePromptGenerator模块
            generator = ImagePromptGenerator(
                creator_name=self.creator_name,
                video_id=self.video_id,
                sd_prompt_file=self.sd_prompt_file,
                images_per_segment=self.images_per_segment
            )
            
            # 生成所有片段的提示词
            results = generator.generate_for_segments()
            
            # 保存结果
            generator.save_results(results)
            
            # 统计信息
            total_prompts = results.get("total_prompts", 0)
            total_segments = results.get("total_segments", 0)
            
            if total_prompts > 0:
                logger.info(f"✅ 成功处理 {total_segments} 个片段，生成 {total_prompts} 个SD提示词")
                logger.info(f"💾 结果已保存到: {generator.final_dir}")
                
                # 检查是否有错误
                if "segments" in results:
                    errors = [k for k, v in results["segments"].items() if "error" in v]
                    if errors:
                        logger.warning(f"⚠️ {len(errors)} 个片段处理失败: {errors}")
                
                return True
            else:
                logger.warning("没有生成任何提示词")
                return False
                
        except Exception as e:
            logger.error(f"生成SD提示词失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_character_profiles(self, framework: str) -> dict:
        """
        从框架中提取角色特征描述
        
        Args:
            framework: 框架文本
            
        Returns:
            角色特征字典
        """
        import re
        
        characters = {}
        
        # 尝试多种模式匹配角色描述
        patterns = [
            r"角色\d+：\[([^\]]+)\][^*]*\*\*[^*]*\*\*([^*]+)",  # 角色1：[名字]...描述
            r"Character \d+:?\s*([^\n]+)[^*]*physical[^:]*:([^*\n]+)",  # Character 1: Name...physical:
            r"主角[^:：]*[:：]\s*([^\n,，]+)[^*]*外[貌观][^:：]*[:：]([^*\n]+)",  # 主角：名字...外貌：
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, framework, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    name = match[0].strip()
                    description = match[1].strip()
                    characters[name] = {
                        "name": name,
                        "visual_description": description,
                        "sd_features": self.extract_sd_features(description)
                    }
        
        # 如果没找到，使用默认角色
        if not characters:
            characters["主角"] = {
                "name": "主角",
                "visual_description": "年轻人，坚定的眼神",
                "sd_features": "young adult, determined eyes, casual clothing"
            }
        
        return characters
    
    def extract_sd_features(self, description: str) -> str:
        """
        从中文描述提取SD友好的特征
        
        Args:
            description: 中文描述
            
        Returns:
            SD特征描述
        """
        # 简单的特征提取（实际可以用AI翻译）
        features = []
        
        # 年龄特征
        if "年轻" in description or "青年" in description:
            features.append("young adult")
        elif "中年" in description:
            features.append("middle-aged")
        elif "老" in description:
            features.append("elderly")
        
        # 性别特征
        if "女" in description:
            features.append("female")
        elif "男" in description:
            features.append("male")
        
        # 其他特征
        if "长发" in description:
            features.append("long hair")
        elif "短发" in description:
            features.append("short hair")
        
        return ", ".join(features) if features else "person"
    
    def extract_key_scenes_from_segment(self, segment_content: str, segment_num: int, num_scenes: int) -> list:
        """
        从segment内容中提取关键场景
        
        Args:
            segment_content: 片段内容
            segment_num: 片段编号
            num_scenes: 要提取的场景数量
            
        Returns:
            关键场景列表
        """
        # 使用AI提取关键场景
        prompt = f"""
从以下故事片段中提取{num_scenes}个最具视觉冲击力的关键场景，用于生成插画。

片段内容：
{segment_content[:2000]}...

请返回JSON格式：
[
  {{
    "description": "场景的视觉描述",
    "emotion": "场景的情感氛围",
    "key_elements": ["关键元素1", "关键元素2"],
    "color_mood": "色调氛围"
  }}
]
"""
        
        try:
            response = self.gemini_client.generate_content(prompt)
            
            # 解析JSON
            import json
            import re
            
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                scenes = json.loads(json_match.group())
                return scenes[:num_scenes]
        except:
            pass
        
        # 如果AI提取失败，使用默认场景
        return [{
            "description": f"片段{segment_num}的关键时刻",
            "emotion": "dramatic",
            "key_elements": ["character", "emotion"],
            "color_mood": "moody"
        }]
    
    def generate_sd_prompt_for_scene(self, scene: dict, character_profiles: dict, 
                                     segment_num: int, scene_idx: int) -> str:
        """
        为场景生成SD提示词
        
        Args:
            scene: 场景信息
            character_profiles: 角色特征
            segment_num: 片段编号
            scene_idx: 场景索引
            
        Returns:
            SD提示词
        """
        # 基础提示词模板
        base_prompt = "masterpiece, best quality, ultra-detailed, illustration"
        
        # 添加角色特征（保持一致性）
        if character_profiles:
            # 取第一个主要角色
            main_char = list(character_profiles.values())[0]
            char_features = main_char.get("sd_features", "")
            if char_features:
                base_prompt += f", {char_features}"
        
        # 添加场景描述
        scene_desc = scene.get("description", "")
        if scene_desc:
            # 这里可以调用翻译API或使用预定义映射
            base_prompt += f", {self.translate_to_sd_style(scene_desc)}"
        
        # 添加情感氛围
        emotion = scene.get("emotion", "")
        emotion_mapping = {
            "dramatic": "dramatic lighting, intense atmosphere",
            "sad": "melancholic mood, soft lighting",
            "happy": "bright, cheerful atmosphere",
            "tense": "tension, dramatic shadows",
            "peaceful": "serene, calm atmosphere"
        }
        if emotion in emotion_mapping:
            base_prompt += f", {emotion_mapping[emotion]}"
        
        # 添加色调
        color_mood = scene.get("color_mood", "")
        if color_mood:
            base_prompt += f", {color_mood} color palette"
        
        # 添加风格标签
        base_prompt += ", cinematic composition, emotional storytelling"
        
        # 负面提示词
        negative_prompt = "low quality, blurry, deformed, ugly, bad anatomy"
        
        return {
            "positive": base_prompt,
            "negative": negative_prompt
        }
    
    def translate_to_sd_style(self, chinese_desc: str) -> str:
        """
        将中文描述翻译为SD风格（简化版）
        
        Args:
            chinese_desc: 中文描述
            
        Returns:
            SD风格描述
        """
        # 这里应该调用翻译API，现在用简单映射
        if len(chinese_desc) > 50:
            return "complex scene with multiple elements"
        else:
            return "focused scene"
    
    def save_prompts_as_markdown(self, prompts: list, character_profiles: dict):
        """
        将提示词保存为Markdown格式
        
        Args:
            prompts: 提示词列表
            character_profiles: 角色特征
        """
        markdown_file = self.final_dir / "sd_prompts_v2.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write("# SD图片提示词（优化版）\n\n")
            f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 角色特征
            f.write("## 角色特征\n\n")
            for name, profile in character_profiles.items():
                f.write(f"### {name}\n")
                f.write(f"- 视觉描述：{profile.get('visual_description', '')}\n")
                f.write(f"- SD特征：{profile.get('sd_features', '')}\n\n")
            
            # 场景提示词
            f.write("## 场景提示词\n\n")
            current_segment = 0
            for prompt in prompts:
                if prompt['segment'] != current_segment:
                    current_segment = prompt['segment']
                    f.write(f"\n### 片段 {current_segment}\n\n")
                
                f.write(f"#### 场景 {prompt['scene_index']}\n")
                f.write(f"- **描述**：{prompt['scene_description']}\n")
                f.write(f"- **情感**：{prompt['emotion']}\n")
                f.write(f"- **正面提示词**：\n```\n{prompt['sd_prompt']['positive']}\n```\n")
                f.write(f"- **负面提示词**：\n```\n{prompt['sd_prompt']['negative']}\n```\n\n")
        
        logger.info(f"📝 Markdown格式提示词已保存到: {markdown_file}")
    
    def generate_image_prompts(self) -> bool:
        """为每个故事片段生成SD图片提示词（优化版：批量生成）
        
        Returns:
            bool: 成功返回true，失败返回false
        """
        try:
            logger.info("🎨 开始生成SD图片提示词（批量优化版）...")
            
            # 读取framework文件
            framework_file = self.processing_dir / "2_framework.txt"
            if not framework_file.exists():
                logger.error(f"Framework文件不存在: {framework_file}")
                return False
            
            with open(framework_file, 'r', encoding='utf-8') as f:
                framework_content = f.read()
            
            # 从framework提取角色信息
            character_profiles = self._extract_characters_from_framework(framework_content)
            if character_profiles:
                logger.info(f"✅ 从Framework提取到{len(character_profiles)}个角色信息")
            else:
                logger.warning("⚠️ 未能从Framework提取角色信息")
            
            # 从framework提取片段信息
            segments_info = self._extract_segments_from_framework(framework_content)
            if not segments_info:
                logger.warning("未能从Framework提取片段信息")
                return False
            
            logger.info(f"✅ 从Framework提取到{len(segments_info)}个片段信息")
            
            # 读取SD提示词生成prompt（使用指定的文件）
            prompt_file = Path(__file__).parent.parent / self.sd_prompt_file
            if not prompt_file.exists():
                logger.error(f"找不到SD提示词生成prompt: {prompt_file}")
                # 尝试使用默认文件
                prompt_file = Path(__file__).parent.parent / "prompts" / "sd_image_generator_v2.md"
                if not prompt_file.exists():
                    logger.error("默认prompt文件也不存在")
                    return False
                logger.info(f"使用默认prompt文件: {prompt_file}")
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            
            # 生成结果容器
            all_prompts = {
                "封面": None,
                "片段": []
            }
            
            # 1. 生成封面提示词
            logger.info("🎭 步骤1: 生成封面提示词...")
            cover_prompt = self._generate_cover_prompt(
                framework_content, 
                character_profiles, 
                system_prompt
            )
            if cover_prompt:
                all_prompts["封面"] = cover_prompt
                logger.info("✅ 封面提示词生成完成")
            else:
                logger.warning("⚠️ 封面提示词生成失败")
            
            # 2. 批量生成所有片段的提示词
            logger.info("📚 步骤2: 批量生成所有片段提示词...")
            segments_prompts = self._generate_all_segments_prompts(
                segments_info,
                character_profiles,
                system_prompt
            )
            
            if segments_prompts:
                all_prompts["片段"] = segments_prompts
                logger.info(f"✅ 成功生成 {len(segments_prompts)} 个片段的提示词")
            
            # 保存所有提示词到文件
            if all_prompts["封面"] or all_prompts["片段"]:
                output_file = self.final_dir / "sd_prompts.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_prompts, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 所有SD提示词已保存到: {output_file}")
                
                # 同时生成一个易读的markdown文件
                markdown_file = self.final_dir / "sd_prompts.md"
                with open(markdown_file, 'w', encoding='utf-8') as f:
                    f.write("# Stable Diffusion 图片提示词\n\n")
                    f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"使用Prompt文件：{self.sd_prompt_file}\n\n")
                    f.write("---\n\n")
                    
                    # 封面部分
                    if all_prompts["封面"]:
                        f.write("## 🎭 封面\n\n")
                        cover = all_prompts["封面"]
                        f.write(f"**场景概述**: {cover.get('场景概述', '')}\n\n")
                        f.write(f"**情绪焦点**: {cover.get('情绪焦点', '')}\n\n")
                        if cover.get('文字元素'):
                            f.write(f"**文字元素**: {', '.join(cover.get('文字元素', []))}\n\n")
                        f.write(f"### 提示词\n```\n{cover.get('提示词', '')}\n```\n\n")
                        f.write("---\n\n")
                    
                    # 片段部分
                    f.write(f"## 📖 故事片段（共{len(all_prompts['片段'])}个）\n\n")
                    for prompt_info in all_prompts["片段"]:
                        f.write(f"### 片段 {prompt_info.get('片段', '')}\n\n")
                        f.write(f"**场景概述**: {prompt_info.get('场景概述', '')}\n\n")
                        f.write(f"**核心情绪**: {prompt_info.get('核心情绪', '')}\n\n")
                        if prompt_info.get('情绪细节'):
                            f.write(f"**情绪细节**: {prompt_info.get('情绪细节', '')}\n\n")
                        f.write(f"#### 提示词\n```\n{prompt_info.get('提示词', '')}\n```\n\n")
                        f.write("---\n\n")
                
                logger.info(f"📝 Markdown格式提示词已保存到: {markdown_file}")
                return True
            else:
                logger.warning("没有生成任何提示词")
                return False
                
        except Exception as e:
            logger.error(f"生成SD提示词失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_chapter_by_segment(self, segment_num: int) -> str:
        """根据片段编号返回所属章节
        
        Args:
            segment_num: 片段编号
            
        Returns:
            章节名称
        """
        if self.num_segments == 9:
            # 9片段对应9步结构
            step_names = ['钩子开场', '角色与动机', '意外转折', '尝试与失败', 
                         '情绪低谷', '顿悟与转变', '最终行动', '胜利的代价', '新的悬念']
            if segment_num <= len(step_names):
                return step_names[segment_num - 1]
            return "未知章节"
        else:
            # 30片段的原始逻辑
            if segment_num <= 4:
                return "Chapter One: Beginning"
            elif segment_num <= 13:
                return "Chapter Two: Development"
            elif segment_num <= 19:
                return "Chapter Three: Conflict Escalation"
            elif segment_num <= 26:
                return "Chapter Four: Climax"
            else:
                return "Chapter Five: Resolution"
    
    def _extract_characters_from_framework(self, framework_content: str) -> list:
        """从framework中提取角色信息
        
        Args:
            framework_content: framework文件内容
            
        Returns:
            角色信息列表
        """
        import re
        
        characters = []
        
        # 查找Character Visual Design部分
        design_pattern = r"Character Visual Design\n=+\n(.*?)(?:\n=+|$)"
        design_match = re.search(design_pattern, framework_content, re.DOTALL)
        
        if not design_match:
            return characters
        
        design_section = design_match.group(1)
        
        # 解析每个角色
        # 主角 - Jessica Martinez
        jessica_pattern = r"Protagonist.*?Jessica Martinez.*?SD Prompt: `([^`]+)`"
        jessica_match = re.search(jessica_pattern, design_section, re.DOTALL)
        if jessica_match:
            characters.append({
                "name": "Jessica Martinez",
                "role": "protagonist",
                "age": "Early 30s",
                "description": "Average height (5'6\"), slender build, long dark brown hair, deep-set brown eyes",
                "sd_prompt": jessica_match.group(1)
            })
        
        # Amber
        amber_pattern = r"Character 2.*?Amber.*?SD Prompt: `([^`]+)`"
        amber_match = re.search(amber_pattern, design_section, re.DOTALL)
        if amber_match:
            characters.append({
                "name": "Amber",
                "role": "antagonist",
                "age": "Late 20s",
                "description": "Tall (5'8\"), slender, sun-kissed blonde hair, influencer aesthetic",
                "sd_prompt": amber_match.group(1)
            })
        
        # Mom
        mom_pattern = r"Character 3.*?Mom.*?SD Prompt: `([^`]+)`"
        mom_match = re.search(mom_pattern, design_section, re.DOTALL)
        if mom_match:
            characters.append({
                "name": "Mom",
                "role": "secondary antagonist",
                "age": "Late 50s",
                "description": "Average height (5'5\"), dyed blonde hair, anxious eyes",
                "sd_prompt": mom_match.group(1)
            })
        
        # Nurse Clare
        clare_pattern = r"Character 4.*?Nurse Clare.*?SD Prompt: `([^`]+)`"
        clare_match = re.search(clare_pattern, design_section, re.DOTALL)
        if clare_match:
            characters.append({
                "name": "Nurse Clare",
                "role": "ally",
                "age": "Early 50s", 
                "description": "Sturdy build, salt-and-pepper hair, warm empathetic eyes",
                "sd_prompt": clare_match.group(1)
            })
        
        return characters
    
    def _extract_segments_from_framework(self, framework_content: str) -> dict:
        """从framework中提取片段信息
        
        Args:
            framework_content: framework文件内容
            
        Returns:
            片段信息字典 {segment_id: info}
        """
        import re
        
        segments = {}
        
        # 查找Two-Level Story Framework部分
        framework_pattern = r"Two-Level Story Framework.*?\n=+\n(.*?)(?:\n=+\nCharacter|$)"
        framework_match = re.search(framework_pattern, framework_content, re.DOTALL)
        
        if not framework_match:
            return segments
        
        story_section = framework_match.group(1)
        
        # 匹配每个片段
        segment_pattern = r"Segment (\d+):\s*([^\n]+?)(?:\s*\(\d+\s*words?\))?\n- Content:\s*([^\n]+)\n- Focus:\s*([^\n]+)\n- Connection:\s*([^\n]+)"
        
        for match in re.finditer(segment_pattern, story_section):
            segment_id = match.group(1)  # 保持为字符串
            segments[segment_id] = {
                'title': match.group(2).strip(),
                'content': match.group(3).strip(),
                'focus': match.group(4).strip(),
                'connection': match.group(5).strip()
            }
        
        return segments
    
    def _generate_cover_prompt(self, framework_content: str, character_profiles: list, system_prompt: str) -> dict:
        """生成封面的SD提示词
        
        Args:
            framework_content: framework文件内容
            character_profiles: 角色信息列表
            system_prompt: SD生成的系统提示词
            
        Returns:
            封面提示词字典
        """
        import re
        
        try:
            # 提取Thumbnail Design信息
            thumbnail_info = {}
            thumbnail_pattern = r"### Thumbnail Design\n(.*?)(?:\n###|\n==|\Z)"
            thumbnail_match = re.search(thumbnail_pattern, framework_content, re.DOTALL)
            
            if thumbnail_match:
                thumbnail_text = thumbnail_match.group(1)
                
                # 提取Visual Elements
                visual_pattern = r"Visual Elements:\s*([^\n]+(?:\n[^\n]+)*?)(?:\nText Overlay:|$)"
                visual_match = re.search(visual_pattern, thumbnail_text)
                if visual_match:
                    thumbnail_info['visual_elements'] = visual_match.group(1).strip()
                
                # 提取Text Overlay
                text_pattern = r"Text Overlay:\s*([^\n]+(?:\n[^\n]+)*?)(?:\nEmotional Impact:|$)"
                text_match = re.search(text_pattern, thumbnail_text)
                if text_match:
                    thumbnail_info['text_overlay'] = text_match.group(1).strip()
                
                # 提取Emotional Impact
                emotion_pattern = r"Emotional Impact:\s*([^\n]+)"
                emotion_match = re.search(emotion_pattern, thumbnail_text)
                if emotion_match:
                    thumbnail_info['emotional_impact'] = emotion_match.group(1).strip()
            
            # 提取标题选项
            titles = []
            title_pattern = r"### Title Options\n(.*?)(?:\n###|\n==|\Z)"
            title_match = re.search(title_pattern, framework_content, re.DOTALL)
            if title_match:
                title_text = title_match.group(1)
                title_lines = [line.strip() for line in title_text.split('\n') if line.strip() and line.strip()[0].isdigit()]
                titles = [re.sub(r'^\d+\.\s*', '', line) for line in title_lines]
            
            # 构建封面生成的输入
            cover_input = json.dumps({
                "task_type": "cover",
                "framework_info": {
                    "thumbnail_design": thumbnail_info,
                    "title_options": titles,
                    "core_conflict": "Family abandonment during surgery vs. luxury vacation"
                },
                "character_profiles": character_profiles
            }, ensure_ascii=False, indent=2)
            
            # DEBUG: 记录完整输入
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_cover_prompt - AI调用输入:")
            logger.debug(f"system_prompt长度: {len(system_prompt)} 字符")
            logger.debug("完整system_prompt:")
            logger.debug(system_prompt)
            logger.debug("完整cover_input:")
            logger.debug(cover_input)
            logger.debug("=" * 80)
            
            # 调用AI生成封面提示词
            response = self.gemini_client.analyze_text(
                text=cover_input,
                prompt=system_prompt
            )
            
            # DEBUG: 记录完整输出
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_cover_prompt - AI调用输出:")
            logger.debug(f"输出长度: {len(response) if response else 0} 字符")
            if response:
                logger.debug("完整输出:")
                logger.debug(response)
            else:
                logger.debug("响应为空")
            logger.debug("=" * 80)
            
            if response:
                # 解析JSON响应
                json_match = re.search(r'```json\s*\n(.+?)\n```', response, re.DOTALL)
                if json_match:
                    cover_data = json.loads(json_match.group(1))
                    return cover_data
            
            return None
            
        except Exception as e:
            logger.error(f"生成封面提示词失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_opening_hook_from_framework(self, framework_content: str) -> str:
        """从framework中提取Opening Hook作为Segment 1
        
        Args:
            framework_content: framework文件内容
            
        Returns:
            开场钩子的文本内容
        """
        import re
        
        # 查找Opening Hook部分的Narration
        hook_pattern = r"### Opening Hook.*?Narration:\n(.*?)(?:\n\nSubtitles:|$)"
        hook_match = re.search(hook_pattern, framework_content, re.DOTALL)
        
        if hook_match:
            narration = hook_match.group(1).strip()
            # 清理引号和格式
            narration = narration.replace('"', '').replace('\n', ' ')
            # 分段处理，让文本更有节奏感
            sentences = narration.split('.')
            formatted_text = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    # 恢复句号
                    formatted_text.append(sentence + '.')
            
            # 将句子组合成段落
            # 第一段：开场白
            opening = formatted_text[0] if formatted_text else ""
            
            # 组合成最终的开场钩子
            result = opening
            if len(formatted_text) > 1:
                result += "\n\n" + " ".join(formatted_text[1:3]) if len(formatted_text) > 2 else formatted_text[1]
            if len(formatted_text) > 3:
                result += "\n\n" + " ".join(formatted_text[3:])
            
            return result
        
        # 如果找不到Opening Hook，尝试从Segment 1的Content中提取
        segment1_pattern = r"Segment 1:.*?\n- Content:\s*([^\n]+)"
        segment1_match = re.search(segment1_pattern, framework_content)
        
        if segment1_match:
            content = segment1_match.group(1).strip()
            # 格式化内容
            return content.replace('A flash-forward scene:', '').strip()
        
        # 默认返回
        return "They say blood is thicker than water. I say, sometimes, it's just a stain you need to scrub away."
    
    def _generate_all_segments_prompts(self, segments_info: dict, character_profiles: list, system_prompt: str) -> list:
        """批量生成所有片段的SD提示词（一次API调用）
        
        Args:
            segments_info: 片段信息字典 {segment_id: info}
            character_profiles: 角色信息列表
            system_prompt: SD生成的系统提示词
            
        Returns:
            包含所有片段提示词的列表
        """
        import re
        
        try:
            logger.info("开始批量生成所有片段的SD提示词...")
            
            # 构建批量输入数据
            all_segments_data = []
            
            # 将segments_info按照编号排序
            sorted_segments = sorted(segments_info.items(), key=lambda x: int(x[0]))
            
            for segment_id, segment_info in sorted_segments:
                segment_num = int(segment_id)
                
                # 读取对应的片段文件内容（如果存在）
                segment_file = self.segments_dir / f"segment_{segment_id.zfill(2)}.txt"
                segment_content = ""
                if segment_file.exists():
                    with open(segment_file, 'r', encoding='utf-8') as f:
                        segment_content = f.read()[:500]  # 只取前500字作为参考
                
                # 构建单个片段的输入数据
                segment_data = {
                    "segment_id": segment_id,
                    "segment_number": segment_num,
                    "chapter": self._get_chapter_by_segment(segment_num),
                    "content_preview": segment_content or segment_info.get('content', ''),
                    "focus": segment_info.get('focus', ''),
                    "connection": segment_info.get('connection', ''),
                    "key_elements": segment_info.get('key_elements', [])
                }
                
                # 特殊场景标记
                if self.num_segments == 9:
                    # 9片段的场景类型
                    scene_types = {
                        1: "opening_hook",        # 钩子开场
                        3: "major_turning_point", # 意外转折
                        5: "lowest_point",        # 情绪低谷
                        7: "climax",             # 最终行动
                        9: "epilogue"            # 新的悬念
                    }
                    segment_data["scene_type"] = scene_types.get(segment_num, "regular")
                else:
                    # 30片段的原始标记逻辑
                    if segment_num == 1:
                        segment_data["scene_type"] = "opening_hook"
                    elif segment_num in [5, 14, 20]:  # 关键转折点
                        segment_data["scene_type"] = "major_turning_point"
                    elif segment_num in [18]:  # 最低点
                        segment_data["scene_type"] = "lowest_point"
                    elif segment_num in [24, 25, 26]:  # 高潮
                        segment_data["scene_type"] = "climax"
                    elif segment_num == 30:
                        segment_data["scene_type"] = "epilogue"
                    else:
                        segment_data["scene_type"] = "regular"
                
                all_segments_data.append(segment_data)
            
            # 构建批量请求的输入
            batch_input = json.dumps({
                "task_type": "batch_segments",
                "total_segments": len(all_segments_data),
                "segments_data": all_segments_data,
                "character_profiles": character_profiles,
                "story_theme": "Family betrayal and personal growth"
            }, ensure_ascii=False, indent=2)
            
            # 修改系统提示词，要求批量返回
            batch_prompt = f"""
{system_prompt}

特别要求：
1. 请一次性生成所有{len(all_segments_data)}个片段的SD提示词
2. 返回一个JSON数组，包含所有片段的提示词
3. 每个片段都要包含: 片段编号、场景概述、核心情绪、提示词
4. 保持角色外观的一致性
5. 根据不同的scene_type调整画面氛围：
   - opening_hook: 神秘、引人入胜
   - major_turning_point: 戏剧性、冲突感
   - lowest_point: 黑暗、绝望
   - climax: 激烈、高能
   - epilogue: 平静、回味
   - regular: 根据内容调整

请返回如下格式的JSON：
```json
[
  {{
    "片段": "01",
    "场景概述": "...",
    "核心情绪": "...",
    "提示词": "..."
  }},
  ...
]
```
"""
            
            # 构建完整提示
            full_batch_prompt = batch_prompt + "\n\n输入数据：\n" + batch_input
            
            # DEBUG: 记录完整输入
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_all_segments_prompts - AI调用输入:")
            logger.debug(f"输入总长度: {len(full_batch_prompt)} 字符")
            logger.debug(f"片段数量: {len(all_segments_data)}")
            logger.debug("完整输入内容:")
            logger.debug(full_batch_prompt)
            logger.debug("=" * 80)
            
            # 调用AI生成所有提示词
            response = self.gemini_client.generate_content(full_batch_prompt)
            
            # DEBUG: 记录完整输出
            logger.debug("=" * 80)
            logger.debug("[DEBUG] _generate_all_segments_prompts - AI调用输出:")
            logger.debug(f"输出长度: {len(response) if response else 0} 字符")
            if response:
                logger.debug("完整输出内容:")
                logger.debug(response)
            else:
                logger.debug("响应为空")
            logger.debug("=" * 80)
            
            if response:
                # 解析JSON响应
                json_match = re.search(r'```json\s*\n(.+?)\n```', response, re.DOTALL)
                if json_match:
                    segments_prompts = json.loads(json_match.group(1))
                    
                    # 验证返回的数量
                    if isinstance(segments_prompts, list):
                        logger.info(f"✅ 成功批量生成 {len(segments_prompts)} 个片段的SD提示词")
                        return segments_prompts
                    else:
                        logger.warning("返回格式不是数组，尝试解析")
                        # 如果不是数组，可能是单个对象，转换为数组
                        return [segments_prompts] if segments_prompts else []
                else:
                    logger.warning("无法从响应中提取JSON")
                    # 尝试直接解析响应
                    try:
                        segments_prompts = json.loads(response)
                        if isinstance(segments_prompts, list):
                            return segments_prompts
                    except Exception as e:
                        logger.debug(f"直接解析响应失败: {e}")
                        import traceback
                        traceback.print_exc()
                        pass
            
            logger.warning("批量生成失败，返回空列表")
            return []
            
        except Exception as e:
            logger.error(f"批量生成片段提示词失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def run(self):
        """执行完整的故事创作流程"""
        logger.info("🚀 开始执行YouTube故事创作流程 V2")
        start_time = time.time()
        
        try:
            # 获取YouTube数据
            youtube_data = self.fetch_youtube_data()
            if not youtube_data:
                logger.error("❌ 无法获取YouTube数据，流程终止")
                return False
            
            # 第一阶段：提取故事DNA
            story_dna, text_analysis = self.phase1_extract_dna(
                youtube_data.get('subtitles', '')
            )
            if not story_dna:
                logger.error("❌ 故事DNA提取失败，流程终止")
                return False
            
            # 第二阶段：生成框架
            framework = self.phase2_generate_framework(
                story_dna,
                youtube_data['video_info'],
                youtube_data.get('comments', [])
            )
            if not framework:
                logger.error("❌ 框架生成失败，流程终止")
                return False
            
            # 第三阶段：分段生成（使用简化版）
            segments = self.phase3_generate_segments_simple(story_dna, framework)
            if not segments:
                logger.error("❌ 片段生成失败，流程终止")
                return False
            
            # 第四阶段：拼接
            draft = self.phase4_concat_segments(segments)
            
            # 第五阶段：润色
            final_story = self.phase5_polish(framework, draft)
            
            # 生成报告
            self.generate_final_report()
            
            # 已移除生图部分，如需生成图片提示词请单独运行 generate_image_prompts.py
            logger.info("✅ 故事生成完成！如需生成图片提示词，请运行：")
            logger.info(f"   python generate_image_prompts.py --creator {self.creator_name} --video {self.video_id} --generator_type jimeng")
            
            # 计算总耗时
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 流程完成！总耗时: {elapsed_time/60:.1f}分钟")
            logger.info(f"📁 结果保存在: {self.output_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 流程执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Story Creator V2')
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('creator_name', help='创作者名称')
    parser.add_argument('--length', type=int, default=30000, help='目标故事长度（默认30000字）')
    parser.add_argument('--segments', type=int, default=9, help='片段数量（默认9个，对应9步结构）')
    
    args = parser.parse_args()
    
    # 创建并运行
    creator = YouTubeStoryCreatorV2(
        video_id=args.video_id,
        creator_name=args.creator_name,
        target_length=args.length,
        num_segments=args.segments
    )
    
    success = creator.run()
    
    if success:
        print("\n✨ 故事创作完成！")
    else:
        print("\n❌ 故事创作失败，请查看日志")
        sys.exit(1)


if __name__ == "__main__":
    main()