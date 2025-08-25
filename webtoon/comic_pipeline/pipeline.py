#!/usr/bin/env python3
"""
漫画解说视频生成Pipeline主类
"""

import os
import time
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .models import (
    ComicImage, ComicChapter, PipelineResult,
    NarrationSegment
)
from .config import ComicPipelineConfig, load_or_create_config
from .stages import ImageAnalyzer, NarrationGenerator, AudioGenerator

# 添加项目根目录到Python路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入草稿生成服务
from draft_gen.generateDraftService import DraftGeneratorService

logger = logging.getLogger(__name__)


class ComicVideoPipeline:
    """漫画解说视频生成Pipeline"""
    
    def __init__(
        self,
        config: Optional[ComicPipelineConfig] = None,
        config_path: Optional[str] = None
    ):
        """
        初始化Pipeline
        
        Args:
            config: 配置对象
            config_path: 配置文件路径
        """
        # 加载配置
        if config:
            self.config = config
        else:
            self.config = load_or_create_config(config_path)
        
        # 初始化各阶段处理器
        self.image_analyzer = ImageAnalyzer(self.config)
        self.narration_generator = NarrationGenerator(self.config)
        self.audio_generator = AudioGenerator(self.config)
        self.draft_generator = DraftGeneratorService()
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def process_comic_chapter(
        self,
        comic_dir: str,
        chapter_name: Optional[str] = None,
        skip_download: bool = False
    ) -> PipelineResult:
        """
        处理漫画章节
        
        Args:
            comic_dir: 漫画目录路径
            chapter_name: 章节名称（可选）
            skip_download: 是否跳过下载步骤
            
        Returns:
            Pipeline执行结果
        """
        start_time = time.time()
        
        try:
            logger.info("="*60)
            logger.info("开始处理漫画章节")
            logger.info("="*60)
            
            # Step 0: 下载漫画（如果需要）
            if not skip_download and not Path(comic_dir).exists():
                logger.info("目录不存在，需要先下载漫画")
                # TODO: 调用下载器
                raise ValueError(f"漫画目录不存在: {comic_dir}")
            
            # Step 1: 加载图片
            logger.info("\n[Step 1] 加载图片")
            images = self._load_comic_images(comic_dir, chapter_name)
            logger.info(f"✓ 加载了 {len(images)} 张图片")
            
            if not images:
                raise ValueError("没有找到图片")
            
            # Step 2: 分析图片
            logger.info("\n[Step 2] 分析图片内容")
            batch_result = self.image_analyzer.analyze_batch(images, batch_size=5)
            logger.info(f"✓ 完成图片分析")
            logger.info(f"  - 故事基调: {batch_result.overall_tone.value}")
            # 处理主要角色（可能是字符串列表或字典列表）
            if batch_result.main_characters:
                if isinstance(batch_result.main_characters[0], dict):
                    character_names = [c.get('name', '未知') for c in batch_result.main_characters[:3]]
                else:
                    character_names = batch_result.main_characters[:3]
                logger.info(f"  - 主要角色: {', '.join(character_names)}")
            else:
                logger.info(f"  - 主要角色: 无")
            
            # Step 3: 生成解说文案
            logger.info("\n[Step 3] 生成解说文案")
            narrations = self.narration_generator.generate_batch_narrations(
                analyses=batch_result.analyses,
                story_outline=batch_result.story_outline
            )
            logger.info(f"✓ 生成了 {len(narrations)} 段文案")
            total_words = sum(len(n) for n in narrations)
            logger.info(f"  - 总字数: {total_words}")
            
            # Step 4: 生成音频（逐个生成，精确控制）
            logger.info("\n[Step 4] 生成音频")
            audio_output_dir = self.config.get_output_path(
                Path(comic_dir).name,
                "audio"
            )
            
            audio_results = self.audio_generator.generate_batch_audio_sync(
                texts=narrations,
                output_dir=str(audio_output_dir),
                prefix="narration"
            )
            logger.info(f"✓ 生成了 {len(audio_results)} 个音频文件")
            
            # Step 5: 创建片段列表
            logger.info("\n[Step 5] 创建时间轴")
            segments = self.audio_generator.create_segments_with_audio(
                images=images,
                narrations=narrations,
                audio_results=audio_results
            )
            
            total_duration = sum(s.duration for s in segments)
            logger.info(f"✓ 总时长: {total_duration:.2f}秒 ({total_duration/60:.1f}分钟)")
            
            # Step 6: 合并音频（可选）
            logger.info("\n[Step 6] 合并音频")
            merged_audio_path = str(audio_output_dir / "merged_audio.mp3")
            self.audio_generator.merge_audio_files(
                audio_files=[r[0] for r in audio_results],
                output_path=merged_audio_path,
                gap_ms=300  # 300ms间隔
            )
            logger.info(f"✓ 音频合并完成: {Path(merged_audio_path).name}")
            
            # Step 7: 生成剪映草稿
            logger.info("\n[Step 7] 生成剪映草稿")
            draft_path = self._create_jianying_draft(
                segments=segments,
                audio_file=merged_audio_path,
                chapter_name=Path(comic_dir).name
            )
            logger.info(f"✓ 剪映草稿生成完成: {draft_path}")
            
            # 计算统计信息
            elapsed_time = time.time() - start_time
            stats = {
                "处理时长": f"{elapsed_time:.1f}秒",
                "图片数量": len(images),
                "总字数": total_words,
                "平均字数": total_words // len(images),
                "音频时长": f"{total_duration:.1f}秒",
                "平均每图": f"{total_duration/len(images):.1f}秒"
            }
            
            # 创建成功结果
            result = PipelineResult(
                success=True,
                comic_dir=comic_dir,
                segments=segments,
                total_duration=total_duration,
                audio_file=merged_audio_path,
                draft_path=draft_path,
                stats=stats
            )
            
            logger.info("\n" + "="*60)
            logger.info("✅ Pipeline执行成功！")
            logger.info("="*60)
            logger.info(result.get_summary())
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            return PipelineResult(
                success=False,
                comic_dir=comic_dir,
                segments=[],
                total_duration=0,
                error_message=str(e)
            )
    
    def _load_comic_images(
        self,
        comic_dir: str,
        chapter_name: Optional[str] = None
    ) -> List[ComicImage]:
        """加载漫画图片"""
        comic_path = Path(comic_dir)
        
        if not comic_path.exists():
            raise ValueError(f"目录不存在: {comic_dir}")
        
        # 获取所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        image_files = []
        
        for file_path in sorted(comic_path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                image_files.append(file_path)
        
        # 创建ComicImage对象
        images = []
        for i, file_path in enumerate(image_files):
            image = ComicImage(
                path=str(file_path),
                index=i,
                chapter=chapter_name or comic_path.name,
                filename=file_path.name
            )
            images.append(image)
        
        return images
    
    def _create_jianying_draft(
        self,
        segments: List[NarrationSegment],
        audio_file: str,
        chapter_name: str
    ) -> str:
        """创建剪映草稿"""
        # 准备图片列表
        images_dir = Path(segments[0].image.path).parent
        
        # 准备输出目录
        output_dir = self.config.get_output_path("drafts")
        
        # 生成SRT字幕文件
        srt_path = self._generate_srt_from_segments(segments, audio_file)
        
        # 计算每张图片的显示时长
        image_durations = [segment.duration for segment in segments]
        avg_duration = sum(image_durations) / len(image_durations)
        
        # 调用草稿生成服务（传入字幕文件）
        draft_path = self.draft_generator.generate_draft(
            images_dir=str(images_dir),
            audio_path=audio_file,
            srt_path=srt_path,  # 添加字幕文件路径
            image_duration_seconds=avg_duration,
            video_title=f"comic_{chapter_name}",
            output_dir=str(output_dir),
            enable_transitions=True,
            enable_effects=False,
            enable_keyframes=True,
            image_scale=1.5
        )
        
        return draft_path
    
    def _generate_srt_from_segments(
        self,
        segments: List[NarrationSegment],
        audio_file: str
    ) -> str:
        """从文案段落生成SRT字幕文件"""
        # 生成SRT内容
        srt_lines = []
        current_time = 0
        
        for i, segment in enumerate(segments, 1):
            # 开始时间
            start_time = current_time
            # 结束时间
            end_time = current_time + segment.duration
            
            # 转换为SRT时间格式
            start_str = self._format_srt_time(start_time)
            end_str = self._format_srt_time(end_time)
            
            # 添加字幕条目
            srt_lines.append(str(i))
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(segment.text)
            srt_lines.append("")  # 空行分隔
            
            current_time = end_time
        
        # 保存SRT文件
        srt_path = Path(audio_file).with_suffix('.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
        
        logger.info(f"✓ 生成字幕文件: {srt_path}")
        return str(srt_path)
    
    def _format_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def process_downloaded_comic(
        self,
        webtoon_url: str,
        output_dir: str = "outputs/webtoon"
    ) -> PipelineResult:
        """
        处理已下载的漫画
        
        Args:
            webtoon_url: Webtoon URL（用于下载）
            output_dir: 输出目录
            
        Returns:
            Pipeline执行结果
        """
        # Step 1: 下载漫画
        logger.info("下载漫画...")
        from ..download_webtoon import SimpleWebtoonDownloader
        
        downloader = SimpleWebtoonDownloader(save_dir=output_dir)
        # 这里需要异步调用，简化示例
        import asyncio
        asyncio.run(downloader.download_webtoon(webtoon_url))
        
        # 获取下载的目录
        # TODO: 从下载器获取实际路径
        comic_dir = Path(output_dir).iterdir().__next__()
        
        # Step 2: 处理第一个章节
        chapters = sorted([d for d in comic_dir.iterdir() if d.is_dir()])
        if not chapters:
            raise ValueError("没有找到章节")
        
        first_chapter = chapters[0]
        logger.info(f"处理章节: {first_chapter.name}")
        
        return self.process_comic_chapter(
            comic_dir=str(first_chapter),
            chapter_name=first_chapter.name,
            skip_download=True
        )