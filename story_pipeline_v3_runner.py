#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Story Pipeline V3 Runner - 严格模式Pipeline运行器
任何步骤失败都会立即终止程序
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量配置
from config_loader import load_env_file
load_env_file()

from pipeline_architecture import Pipeline, PipelineStep, PromptManager
from pipeline_context_v3 import PipelineContextV3
# 分别导入模块，确保所有步骤都被正确加载
import pipeline_steps_v3
import pipeline_steps_youtube_metadata

# 从模块中导入类
from pipeline_steps_v3 import (
    FetchYouTubeDataV3Step,
    GenerateFrameworkV3Step,
    ParseFrameworkV3Step,
    GenerateStoryHeaderStep,
    GenerateAllSegmentsStep,
    MergeAndPolishStep,
    GenerateSummaryStep,
    SaveFinalOutputStep
)
from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
from youtube_client import YouTubeAPIClient
from gemini_client import GeminiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline_v3.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class StrictPipeline(Pipeline):
    """严格模式Pipeline - 任何失败都会终止程序"""
    
    def execute(self, context: PipelineContextV3) -> bool:
        """
        执行Pipeline（严格模式）
        
        Args:
            context: V3上下文
            
        Returns:
            成功返回True，失败直接终止程序
        """
        logger.info(f"[START] 启动严格模式Pipeline: {self.name}")
        logger.info(f"[VIDEO] 处理视频: {context.video_id}")
        
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"步骤 {i}/{total_steps}: {step.name}")
            logger.info(f"{'='*60}")
            
            try:
                # 执行步骤
                result = step.execute(context)
                
                if not result.success:
                    # 步骤失败，立即终止
                    logger.error(f"\n{'='*60}")
                    logger.error(f"[FAILED] 步骤失败: {step.name}")
                    logger.error(f"错误信息: {result.error}")
                    logger.error(f"Pipeline终止!")
                    logger.error(f"{'='*60}")
                    
                    # 保存错误信息
                    if context.cache_dir:
                        self._save_error_log(context, step.name, result.error)
                    
                    # 终止程序
                    sys.exit(1)
                
                logger.info(f"[OK] 步骤完成: {step.name}")
                
            except Exception as e:
                # 捕获异常，终止程序
                logger.error(f"\n{'='*60}")
                logger.error(f"[ERROR] 步骤异常: {step.name}")
                logger.error(f"异常信息: {str(e)}")
                logger.error(f"Pipeline终止!")
                logger.error(f"{'='*60}")
                
                # 保存错误信息
                if context.cache_dir:
                    self._save_error_log(context, step.name, str(e))
                
                # 打印堆栈
                import traceback
                traceback.print_exc()
                
                # 终止程序
                sys.exit(1)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[SUCCESS] Pipeline执行成功!")
        logger.info(f"[OUTPUT] 输出目录: {context.cache_dir}")
        logger.info(f"{'='*60}")
        
        return True
    
    def _save_error_log(self, context: PipelineContextV3, step_name: str, error: str):
        """保存错误日志"""
        try:
            error_file = context.cache_dir / "error.json"
            error_data = {
                'step': step_name,
                'error': error,
                'video_id': context.video_id,
                'creator_name': context.creator_name
            }
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
        except:
            pass


class StoryPipelineV3Runner:
    """V3 Pipeline运行器"""
    
    def __init__(self):
        """初始化运行器"""
        # 初始化API客户端
        self._init_clients()
        
        # 创建提示词管理器
        self.prompt_manager = PromptManager(Path("prompts"))
        
        # 加载提示词
        self._load_prompts()
        
        logger.info("[OK] V3 Pipeline Runner初始化完成")
    
    def _init_clients(self):
        """初始化API客户端"""
        # YouTube API
        youtube_api_key = os.getenv("YOUTUBE_API_KEY", "AIzaSyCdbljoACNX1Ov3GsU6KRrnwWnCHAyyjVQ")
        self.youtube_client = YouTubeAPIClient()
        
        # Gemini API
        gemini_api_key = os.getenv("NEWAPI_API_KEY")
        if not gemini_api_key:
            gemini_api_key = "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu"
            logger.warning("使用默认API密钥")
        
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        
        logger.info("[OK] API客户端初始化完成")
    
    def _load_prompts(self):
        """加载所有需要的提示词"""
        prompts_to_load = [
            'framework_generatorv3',
            'story_header',
            'segment_generator',
            'final_polisher'
        ]
        
        for prompt_name in prompts_to_load:
            try:
                self.prompt_manager.load_prompt(prompt_name)
                logger.info(f"[OK] 加载提示词: {prompt_name}")
            except FileNotFoundError as e:
                logger.warning(f"[WARNING] 提示词文件不存在: {prompt_name} - {e}")
    
    def create_pipeline(self) -> StrictPipeline:
        """创建V3 Pipeline"""
        pipeline = StrictPipeline("story_generation_v3")
        
        # 设置提示词管理器
        pipeline.prompt_manager = self.prompt_manager
        
        # 添加步骤（按顺序）
        steps = [
            FetchYouTubeDataV3Step(self.youtube_client),
            GenerateFrameworkV3Step(self.gemini_client),
            ParseFrameworkV3Step(),
            GenerateStoryHeaderStep(self.gemini_client),
            GenerateAllSegmentsStep(self.gemini_client),
            MergeAndPolishStep(self.gemini_client),
            GenerateSummaryStep(self.gemini_client),
            GenerateYouTubeMetadataStep(self.gemini_client),  # 新增：YouTube元数据生成
            SaveFinalOutputStep()
        ]
        
        # 为每个步骤设置提示词管理器
        for step in steps:
            step.set_prompt_manager(self.prompt_manager)
            pipeline.add_step(step)
        
        logger.info(f"[OK] 创建Pipeline，包含 {len(steps)} 个步骤")
        
        return pipeline
    
    def run(self, video_id: str, creator_name: str = "default") -> bool:
        """
        运行V3 Pipeline
        
        Args:
            video_id: YouTube视频ID
            creator_name: 创作者名称
            
        Returns:
            成功返回True，失败终止程序
        """
        # 创建上下文
        context = PipelineContextV3(
            video_id=video_id,
            creator_name=creator_name,
            cache_dir=Path("story_result") / creator_name / video_id
        )
        
        # 确保输出目录存在
        context.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建Pipeline
        pipeline = self.create_pipeline()
        
        # 执行Pipeline（严格模式）
        success = pipeline.execute(context)
        
        if success:
            # 打印最终统计
            self._print_statistics(context)
        
        return success
    
    def _print_statistics(self, context: PipelineContextV3):
        """打印最终统计信息"""
        print("\n" + "="*60)
        print("[STATS] 最终统计")
        print("="*60)
        print(f"视频ID: {context.video_id}")
        print(f"视频标题: {context.video_info.get('title', 'N/A')}")
        print(f"Segment数量: {context.segment_count}")
        print(f"故事总长度: {len(context.final_story)} 字符")
        print(f"输出目录: {context.cache_dir}")
        print("="*60)
        
        # 列出生成的文件
        print("\n[OUTPUT] 生成的文件:")
        final_dir = context.cache_dir / "final"
        if final_dir.exists():
            for file in final_dir.iterdir():
                print(f"  - {file.name}")
        print("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='YouTube Story Pipeline V3 - 严格模式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python story_pipeline_v3_runner.py VIDEO_ID
  python story_pipeline_v3_runner.py VIDEO_ID --creator myname
  
注意:
  - 任何步骤失败都会立即终止程序
  - 所有中间结果都会保存用于调试
  - 最终输出为纯英文故事 + 中文总结
        """
    )
    
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('--creator', default='default', help='创作者名称（默认: default）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 打印启动信息
    print("\n" + "="*60)
    print("YouTube Story Pipeline V3 - 严格模式")  # 移除emoji以避免编码问题
    print("="*60)
    print(f"视频ID: {args.video_id}")
    print(f"创作者: {args.creator}")
    print(f"调试模式: {'是' if args.debug else '否'}")
    print("="*60 + "\n")
    
    # 创建运行器
    runner = StoryPipelineV3Runner()
    
    # 运行Pipeline
    try:
        success = runner.run(
            video_id=args.video_id,
            creator_name=args.creator
        )
        
        if success:
            print("\n[OK] Pipeline执行成功!")
            sys.exit(0)
        else:
            print("\n[FAILED] Pipeline执行失败!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[WARNING] 用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 发生致命错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()