#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整故事二创Pipeline
包含所有阶段：故事生成、TTS、草稿生成、视频导出、YouTube发布
支持灵活配置各阶段的启用/禁用
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from pipelines.base_pipeline import BasePipeline, PipelineStage
from pipelines.pipeline_context import PipelineContext
from pipelines import pipeline_stages

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class StoryFullPipeline(BasePipeline):
    """
    完整的故事二创Pipeline
    包含从故事生成到视频发布的完整流程
    """


    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Pipeline
        
        Args:
            config: Pipeline配置，包括：
                - enable_video_fetch: 是否启用自动获取视频（默认False）
                - enable_story: 是否启用故事生成（默认True）
                - enable_tts: 是否启用TTS（默认True）
                - enable_draft: 是否启用草稿生成（默认True）
                - enable_publish: 是否启用YouTube发布（默认False）
                - video_fetch_config: 视频获取配置
                - story_config: 故事生成配置
                - tts_config: TTS配置
                - draft_config: 草稿生成配置
                - video_config: 视频导出配置
                - publish_config: 发布配置
        """
        super().__init__(config)
        
        # 默认配置 - 强模式：所有步骤都是必需的
        self.default_config = {
            'enable_video_fetch': True,  # 默认不启用自动获取
            'enable_story': True,
            'enable_tts': True,
            'enable_draft': True,
            'enable_publish': True,  # 默认启用发布
            'enable_video_export': True,  # 默认启用视频导出
            'strict_mode': True,  # 强模式：任何失败都中断
            'video_fetch_config': {},
            'story_config': {},
            'tts_config': {},
            'draft_config': {},
            'video_config': {},
            'publish_config': {}
        }
        
        # 合并配置
        if config:
            self.config = {**self.default_config, **config}
        else:
            self.config = self.default_config
            
        logger.info(f"StoryFullPipeline initialized with config: {self.config}")
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整的故事二创Pipeline
        
        Args:
            params: 执行参数
                当enable_video_fetch=True时（自动获取模式）：
                    必选参数:
                    - creator_list: List[str] - 创作者ID列表，按优先级排序
                    - account_id: str - 账号ID（用于音频和草稿生成）
                    
                    可选参数:
                    - duration: int - 视频时长（秒），默认300
                    
                当enable_video_fetch=False时（传统模式）：
                    必选参数:
                    - video_id: str - YouTube视频ID
                    - creator_id: str - 创作者ID
                    - account_id: str - 账号ID
                    
                    可选参数:
                    - duration: int - 视频时长（秒），默认300
        
        Returns:
            dict: 执行结果
        """
        logger.info(f"[START] Executing StoryFullPipeline with params: {params}")
        self.start_time = datetime.now()
        
        # 智能检测：如果提供了creator_list但没有video_id，自动启用video_fetch
        if 'creator_list' in params and 'video_id' not in params:
            if not self.config.get('enable_video_fetch'):
                logger.info("[AUTO] Detected creator_list without video_id, enabling video_fetch")
                self.config['enable_video_fetch'] = True
        
        # 记录最终的配置状态
        logger.info(f"[CONFIG] Final enable_video_fetch={self.config.get('enable_video_fetch')}")
        logger.info(f"[CONFIG] Has creator_list={('creator_list' in params)}")
        logger.info(f"[CONFIG] Has video_id={('video_id' in params)}")
        
        # 参数验证 - 根据是否启用video_fetch决定必需参数
        if self.config.get('enable_video_fetch', False):
            # 自动获取模式：需要creator_list和account_id
            required_params = ['creator_list', 'account_id']
        else:
            # 传统模式：需要video_id、creator_id和account_id
            required_params = ['video_id', 'creator_id', 'account_id']
        is_valid, error_msg = self.validate_params(params, required_params)
        if not is_valid:
            return self.handle_error(Exception(error_msg), 'validation')
        
        # 创建执行上下文
        context = PipelineContext(params)
        
        try:
            # 构建执行阶段
            stages = self._build_stages()
            logger.info(f"[STAGES] Built {len(stages)} stages: {[s.name for s in stages]}")
            
            # 执行各阶段
            for stage in stages:
                logger.info(f"[STAGE] Executing stage: {stage.name}")
                
                # 检查是否可以跳过（基于缓存）
                if self.should_skip_stage(stage.name, context.cache_dir):
                    logger.info(f"[SKIP] Stage {stage.name} skipped (cached)")
                    self.stages_results.append(
                        self.create_stage_result(stage.name, True, {'cached': True})
                    )
                    continue
                
                # 执行阶段，传递包含上下文引用的字典
                execute_context = {
                    '_context': context,
                    'params': context.params,
                    'outputs': context.outputs,
                    'cache_dir': str(context.cache_dir)
                }
                
                # 特别记录video_fetch阶段的参数
                if stage.name == 'video_fetch':
                    logger.info(f"[VIDEO_FETCH] About to execute video_fetch stage")
                    logger.info(f"[VIDEO_FETCH] Input params: {context.params}")
                    logger.info(f"[VIDEO_FETCH] Stage config: {stage.config}")
                    logger.info(f"[VIDEO_FETCH] creator_list={context.params.get('creator_list')}")
                
                result = await stage.execute(execute_context)
                
                # 特别记录video_fetch阶段的结果并更新params
                if stage.name == 'video_fetch':
                    logger.info(f"[VIDEO_FETCH] Output: success={result.get('success')}, data={result.get('data')}")
                    if result.get('success') and result.get('data'):
                        # 更新context params以供后续阶段使用
                        data = result['data']
                        if 'video_id' in data:
                            context.params['video_id'] = data['video_id']
                            params['video_id'] = data['video_id']
                            logger.info(f"[VIDEO_FETCH] Set video_id={data['video_id']}")
                        if 'selected_creator_id' in data:
                            context.params['creator_id'] = data['selected_creator_id']
                            params['creator_id'] = data['selected_creator_id']
                            logger.info(f"[VIDEO_FETCH] Set creator_id={data['selected_creator_id']}")
                        logger.info(f"[VIDEO_FETCH] Updated params after fetch: {context.params}")
                
                self.stages_results.append(result)
                
                # 保存阶段输出
                if result['success']:
                    context.set_stage_output(stage.name, result.get('data', {}))
                    logger.info(f"[OK] Stage {stage.name} completed successfully")
                else:
                    # 强模式下，任何失败都终止Pipeline
                    if self.config.get('strict_mode', True):
                        logger.error(f"[FAILED] Stage {stage.name} failed in strict mode: {result.get('error')}")
                        self.end_time = datetime.now()
                        return {
                            'success': False,
                            'error': f"Stage '{stage.name}' failed: {result.get('error')}",
                            'stage': stage.name,
                            'stages': self.stages_results,
                            'summary': self.get_execution_summary()
                        }
                    # 非强模式下，检查是否是必需阶段
                    elif stage.is_required():
                        logger.error(f"[FAILED] Required stage {stage.name} failed: {result.get('error')}")
                        self.end_time = datetime.now()
                        return {
                            'success': False,
                            'error': f"Required stage '{stage.name}' failed: {result.get('error')}",
                            'stage': stage.name,
                            'stages': self.stages_results,
                            'summary': self.get_execution_summary()
                        }
                    else:
                        logger.warning(f"[WARNING] Optional stage {stage.name} failed: {result.get('error')}")
            
            # 收集所有输出
            outputs = self.collect_outputs()
            
            # 构建最终结果
            self.end_time = datetime.now()
            
            result = {
                'success': True,
                'data': {
                    'cache_dir': str(context.cache_dir),
                    'video_id': params.get('video_id'),
                    'creator_id': params.get('creator_id'),
                    'account_id': params.get('account_id'),
                    **outputs
                },
                'stages': self.stages_results,
                'summary': self.get_execution_summary(),
                'metadata': {
                    'pipeline_type': 'story_full_pipeline',
                    'config': self.config
                }
            }
            
            # 如果有视频路径，添加到结果中
            if 'video_export' in outputs and outputs['video_export'].get('video_path'):
                result['video_path'] = outputs['video_export']['video_path']
            
            # 如果有发布结果，添加到结果中
            if 'youtube_publish' in outputs and outputs['youtube_publish'].get('video_url'):
                result['video_url'] = outputs['youtube_publish']['video_url']
            
            logger.info(f"[SUCCESS] StoryFullPipeline completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] StoryFullPipeline failed: {e}")
            self.end_time = datetime.now()
            return self.handle_error(e, 'execution')
    
    def _build_stages(self) -> List[PipelineStage]:
        """
        根据配置构建执行阶段
        
        Returns:
            list: PipelineStage列表
        """
        stages = []
        
        # 强模式下，所有启用的阶段都是必需的
        is_strict = self.config.get('strict_mode', True)
        
        # 视频获取预处理阶段（如果启用）
        logger.info(f"[BUILD_STAGES] enable_video_fetch={self.config.get('enable_video_fetch')}")
        if self.config.get('enable_video_fetch', False):
            logger.info("[BUILD_STAGES] Adding video_fetch stage")
            from pipelines.pipeline_stages_video_fetch import fetch_latest_video_stage
            stages.append(PipelineStage(
                name='video_fetch',
                handler=fetch_latest_video_stage,
                required=True,  # 如果启用，必须成功
                config=self.config.get('video_fetch_config', {})
            ))
        
        # 故事生成阶段
        if self.config.get('enable_story', True):
            stages.append(PipelineStage(
                name='story_generation',
                handler=pipeline_stages.story_generation_stage,
                required=is_strict or self.config.get('story_required', True),
                config=self.config.get('story_config', {})
            ))
        
        # TTS生成阶段
        if self.config.get('enable_tts', True):
            stages.append(PipelineStage(
                name='tts_generation',
                handler=pipeline_stages.tts_generation_stage,
                required=is_strict or self.config.get('tts_required', True),
                config=self.config.get('tts_config', {})
            ))
        
        # 草稿生成阶段
        if self.config.get('enable_draft', True):
            stages.append(PipelineStage(
                name='draft_generation',
                handler=pipeline_stages.draft_generation_stage,
                required=is_strict or self.config.get('draft_required', True),
                config=self.config.get('draft_config', {})
            ))
        
        # 视频导出阶段（强模式下必需）
        if self.config.get('enable_video_export', True):
            stages.append(PipelineStage(
                name='video_export',
                handler=pipeline_stages.video_export_stage,
                required=True,  # 视频导出始终是必需的
                config=self.config.get('video_config', {})
            ))
        
        # YouTube发布阶段（强模式下必需）
        if self.config.get('enable_publish', True):
            stages.append(PipelineStage(
                name='youtube_publish',
                handler=pipeline_stages.youtube_publish_stage,
                required=True,  # 发布始终是必需的
                config=self.config.get('publish_config', {})
            ))
        
        logger.info(f"Built {len(stages)} stages for execution")
        return stages
    
    def should_skip_stage(self, stage_name: str, cache_dir: Path) -> bool:
        """
        检查阶段是否可以跳过（基于缓存）
        
        Args:
            stage_name: 阶段名称
            cache_dir: 缓存目录
        
        Returns:
            bool: 是否跳过
        """
        # 检查缓存策略
        cache_strategy = self.config.get('cache_strategy', 'auto')
        
        if cache_strategy == 'none':
            return False
        
        if cache_strategy == 'all':
            # 检查阶段输出文件是否存在
            if stage_name == 'story_generation':
                story_file = cache_dir / 'story' / 'story.txt'
                return story_file.exists()
            elif stage_name == 'tts_generation':
                audio_file = cache_dir / 'audio' / 'audio.mp3'
                return audio_file.exists()
            elif stage_name == 'draft_generation':
                draft_folder = cache_dir / 'draft' / 'draft_folder'
                return draft_folder.exists()
            elif stage_name == 'video_export':
                video_file = cache_dir / 'video' / 'final_video.mp4'
                return video_file.exists()
        
        return False


async def create_pipeline(config: Optional[Dict[str, Any]] = None) -> StoryFullPipeline:
    """
    工厂函数：创建StoryFullPipeline实例
    
    Args:
        config: Pipeline配置
    
    Returns:
        StoryFullPipeline: Pipeline实例
    """
    return StoryFullPipeline(config)


# 示例配置
EXAMPLE_CONFIG = {
    # 阶段启用控制
    'enable_video_fetch': False,  # 启用自动获取最新视频
    'enable_story': True,         # 启用故事生成
    'enable_tts': True,           # 启用TTS
    'enable_draft': True,         # 启用草稿生成
    'enable_video_export': True,  # 启用视频导出
    'enable_publish': False,      # 禁用YouTube发布（手动发布）
    'strict_mode': True,          # 强模式：任何失败都中断
    
    # 缓存策略
    'cache_strategy': 'auto',  # auto, all, none
    
    # 视频获取配置（当enable_video_fetch=True时使用）
    'video_fetch_config': {
        'days_back': 7,      # 获取最近7天的视频
        'max_videos': 10     # 最多检查10个视频
    },
    
    # 各阶段配置
    'story_config': {
        'model': 'gemini-1.5-pro',
        'temperature': 0.7
    },
    'tts_config': {
        'voice': 'zh-CN-Wavenet-A',
        'speed': 1.0
    },
    'draft_config': {
        'template': 'default',
        'quality': 'high'
    },
    'video_config': {
        'resolution': '1920x1080',
        'fps': 30,
        'quality': 'high'
    },
    'publish_config': {
        'privacy': 'private',
        'notify_subscribers': False
    }
}

# 自动获取视频的配置示例
AUTO_FETCH_CONFIG = {
    'enable_video_fetch': True,   # 启用自动获取
    'enable_story': True,
    'enable_tts': True,
    'enable_draft': True,
    'enable_video_export': True,
    'enable_publish': True,        # 启用发布
    'strict_mode': True,
    
    'video_fetch_config': {
        'days_back': 3,           # 获取最近3天的视频
        'max_videos': 5           # 最多检查5个视频
    }
}


if __name__ == "__main__":
    """测试代码"""
    import asyncio
    
    async def test_traditional():
        """测试传统模式（需要提供video_id）"""
        print("=" * 60)
        print("测试传统模式")
        print("=" * 60)
        
        # 创建Pipeline（不启用自动获取）
        pipeline = StoryFullPipeline(EXAMPLE_CONFIG)
        
        # 测试参数（必须包含video_id）
        params = {
            'video_id': 'test_video_123',
            'creator_id': 'test_creator',
            'account_id': 'test_account'
        }
        
        # 执行Pipeline
        result = await pipeline.execute(params)
        
        # 打印结果
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    async def test_auto_fetch():
        """测试自动获取模式（需要creator_list）"""
        print("\n" + "=" * 60)
        print("测试自动获取模式")
        print("=" * 60)
        
        # 创建Pipeline（启用自动获取）
        pipeline = StoryFullPipeline(AUTO_FETCH_CONFIG)
        
        # 测试参数（需要creator_list和account_id）
        params = {
            'creator_list': [
                'UCH9vY_kzBKhDDrpMavKxTIQ',  # 第一优先级
                'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # 第二优先级
                'UCddiUEpeqJcYeBxX1IVBKvQ',  # 第三优先级
            ],
            'account_id': 'test_account',
            'duration': 300  # 可选参数
        }
        
        # 执行Pipeline
        result = await pipeline.execute(params)
        
        # 打印结果
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 运行测试
    # asyncio.run(test_traditional())  # 测试传统模式
    asyncio.run(test_auto_fetch())  # 测试自动获取模式