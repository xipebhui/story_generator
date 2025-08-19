#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Story Pipeline Runner - 使用新的Pipeline架构运行故事生成
这是新架构的主入口，完全解耦了提示词和业务逻辑
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_architecture import (
    Pipeline, PipelineContext, PipelineConfig, 
    PipelineFactory, PromptManager
)
from pipeline_steps import (
    FetchYouTubeDataStep, ExtractDNAStep, GenerateFrameworkStep,
    GenerateSegmentsStep, PolishStoryStep, GenerateReportStep
)
from youtube_client import YouTubeAPIClient
from gemini_client import GeminiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class StoryPipelineRunner:
    """故事Pipeline运行器 - 协调整个流程"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化运行器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = PipelineConfig(config_path or "pipeline_config.json")
        
        # 初始化API客户端
        self._init_clients()
        
        # 创建Pipeline
        self.pipeline = None
        
    def _init_clients(self):
        """初始化API客户端"""
        # YouTube API
        youtube_api_key = os.getenv("YOUTUBE_API_KEY", "AIzaSyCdbljoACNX1Ov3GsU6KRrnwWnCHAyyjVQ")
        self.youtube_client = YouTubeAPIClient()
        
        # Gemini API
        gemini_api_key = os.getenv("NEWAPI_API_KEY", "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu")
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        
        logger.info("✅ API客户端初始化完成")
    
    def create_pipeline(self, pipeline_name: str = "story_generation") -> Pipeline:
        """
        创建Pipeline实例
        
        Args:
            pipeline_name: Pipeline名称
            
        Returns:
            配置好的Pipeline实例
        """
        pipeline_config = self.config.get_pipeline_config(pipeline_name)
        
        # 创建Pipeline
        pipeline = Pipeline(pipeline_name)
        
        # 设置提示词管理器
        prompt_manager = PromptManager(Path("prompts"))
        
        # 加载提示词配置
        for prompt_name, prompt_config in self.config.config.get('prompts', {}).items():
            if 'file' in prompt_config:
                prompt_manager.load_prompt(prompt_name, prompt_config['file'])
        
        pipeline.prompt_manager = prompt_manager
        
        # 添加步骤
        for step_config in pipeline_config.get('steps', []):
            step = self._create_step(step_config)
            if step:
                pipeline.add_step(step)
        
        # 添加钩子函数
        self._add_hooks(pipeline)
        
        logger.info(f"✅ Pipeline '{pipeline_name}' 创建完成，包含 {len(pipeline.steps)} 个步骤")
        
        return pipeline
    
    def _create_step(self, step_config: Dict[str, Any]) -> Optional[PipelineStep]:
        """
        根据配置创建步骤实例
        
        Args:
            step_config: 步骤配置
            
        Returns:
            步骤实例
        """
        step_class = step_config.get('class')
        
        # 步骤类映射
        step_classes = {
            'FetchYouTubeDataStep': lambda: FetchYouTubeDataStep(self.youtube_client),
            'ExtractDNAStep': lambda: ExtractDNAStep(self.gemini_client),
            'GenerateFrameworkStep': lambda: GenerateFrameworkStep(self.gemini_client),
            'GenerateSegmentsStep': lambda: GenerateSegmentsStep(
                self.gemini_client, 
                step_config.get('strategy', 'simple')
            ),
            'PolishStoryStep': lambda: PolishStoryStep(self.gemini_client),
            'GenerateReportStep': lambda: GenerateReportStep()
        }
        
        if step_class in step_classes:
            step = step_classes[step_class]()
            logger.debug(f"创建步骤: {step.name}")
            return step
        else:
            logger.warning(f"未知的步骤类: {step_class}")
            return None
    
    def _add_hooks(self, pipeline: Pipeline):
        """添加Pipeline钩子函数"""
        
        def before_step_hook(step, context):
            """步骤执行前的钩子"""
            logger.info(f"🔄 开始执行步骤: {step.name}")
        
        def after_step_hook(step, context, result):
            """步骤执行后的钩子"""
            if result.success:
                logger.info(f"✅ 步骤 {step.name} 执行成功")
            else:
                logger.error(f"❌ 步骤 {step.name} 执行失败: {result.error}")
        
        def on_error_hook(step, context, error):
            """错误处理钩子"""
            logger.error(f"💥 步骤 {step.name} 发生错误: {error}")
            # 可以在这里添加错误恢复逻辑
        
        def on_complete_hook(context):
            """Pipeline完成钩子"""
            logger.info("🎉 Pipeline执行完成!")
            logger.info(f"最终故事长度: {len(context.final_story)} 字")
        
        pipeline.add_hook('before_step', before_step_hook)
        pipeline.add_hook('after_step', after_step_hook)
        pipeline.add_hook('on_error', on_error_hook)
        pipeline.add_hook('on_complete', on_complete_hook)
    
    def run(self, video_id: str, creator_name: str, 
            target_length: int = 30000, num_segments: int = 9) -> bool:
        """
        运行完整的故事生成流程
        
        Args:
            video_id: YouTube视频ID
            creator_name: 创作者名称
            target_length: 目标故事长度
            num_segments: 片段数量
            
        Returns:
            是否成功
        """
        logger.info(f"🚀 开始处理视频: {video_id}")
        
        # 创建上下文
        context = PipelineContext(
            video_id=video_id,
            creator_name=creator_name,
            target_length=target_length,
            num_segments=num_segments,
            cache_dir=Path("story_result") / creator_name / video_id
        )
        
        # 创建Pipeline
        if not self.pipeline:
            self.pipeline = self.create_pipeline()
        
        # 执行Pipeline
        success = self.pipeline.execute(context)
        
        if success:
            logger.info("✅ 故事生成成功!")
            self._save_results(context)
        else:
            logger.error("❌ 故事生成失败")
        
        return success
    
    def _save_results(self, context: PipelineContext):
        """保存最终结果"""
        output_dir = context.cache_dir / "final"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存最终故事
        story_file = output_dir / "story.txt"
        with open(story_file, 'w', encoding='utf-8') as f:
            f.write(context.final_story)
        
        logger.info(f"💾 故事已保存到: {story_file}")
        
        # 保存元数据
        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'video_id': context.video_id,
                'creator_name': context.creator_name,
                'target_length': context.target_length,
                'actual_length': len(context.final_story),
                'num_segments': context.num_segments,
                'video_info': context.video_info,
                'metadata': context.metadata
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 元数据已保存到: {metadata_file}")


def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Story Pipeline Runner')
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('--creator', default='default', help='创作者名称')
    parser.add_argument('--length', type=int, default=30000, help='目标故事长度')
    parser.add_argument('--segments', type=int, default=9, help='片段数量')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--pipeline', default='story_generation', help='Pipeline名称')
    
    args = parser.parse_args()
    
    # 创建运行器
    runner = StoryPipelineRunner(args.config)
    
    # 运行Pipeline
    success = runner.run(
        video_id=args.video_id,
        creator_name=args.creator,
        target_length=args.length,
        num_segments=args.segments
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()