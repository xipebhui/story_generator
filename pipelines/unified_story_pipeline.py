#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一故事Pipeline
支持从YouTube和抖音获取视频并处理
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from pipelines.base_pipeline import BasePipeline, PipelineStage
from pipelines.pipeline_context import PipelineContext
from pipelines import pipeline_stages
from pipelines.pipeline_stages_unified_fetch import unified_video_fetch_stage, mark_video_status_stage

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class UnifiedStoryPipeline(BasePipeline):
    """
    统一的故事二创Pipeline
    支持从YouTube和抖音获取视频并处理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Pipeline
        
        Args:
            config: Pipeline配置，包括：
                - platform: 平台（youtube/douyin），默认youtube
                - enable_story: 是否启用故事生成（默认True）
                - enable_tts: 是否启用TTS（默认True）
                - enable_draft: 是否启用草稿生成（默认True）
                - enable_video_export: 是否启用视频导出（默认True）
                - enable_publish: 是否启用发布（默认True）
                - mark_completed: 是否在完成后标记视频状态（默认True）
                - fetch_config: 视频获取配置
                - story_config: 故事生成配置
                - tts_config: TTS配置
                - draft_config: 草稿生成配置
                - video_config: 视频导出配置
                - publish_config: 发布配置
        """
        super().__init__(config)
        
        # 默认配置
        self.default_config = {
            'platform': 'youtube',
            'enable_story': True,
            'enable_tts': True,
            'enable_draft': True,
            'enable_video_export': True,
            'enable_publish': True,
            'mark_completed': True,  # 完成后标记视频状态
            'strict_mode': True,
            'fetch_config': {},
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
        
        logger.info(f"UnifiedStoryPipeline initialized with config: {self.config}")
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Pipeline
        
        Args:
            params: 执行参数
                必选参数：
                - creator_list: List[str] - 创作者ID列表
                - account_id: str - 账号ID
                
                可选参数：
                - platform: str - 平台（youtube/douyin），默认使用配置中的值
                - duration: int - 视频时长（秒），默认300
                - fetch_config: Dict - 视频获取配置
        
        Returns:
            dict: 执行结果
        """
        logger.info(f"[START] Executing UnifiedStoryPipeline with params: {params}")
        self.start_time = datetime.now()
        
        # 设置平台
        if 'platform' not in params:
            params['platform'] = self.config.get('platform', 'youtube')
        
        # 参数验证
        required_params = ['creator_list', 'account_id']
        is_valid, error_msg = self.validate_params(params, required_params)
        if not is_valid:
            return self.handle_error(Exception(error_msg), 'validation')
        
        # 创建执行上下文
        context = PipelineContext(params)
        video_processed = None
        
        try:
            # 构建执行阶段
            stages = self._build_stages()
            logger.info(f"[STAGES] Built {len(stages)} stages: {[s.name for s in stages]}")
            
            # 执行各阶段
            for stage in stages:
                logger.info(f"[STAGE] Executing stage: {stage.name}")
                
                # 构建阶段上下文
                execute_context = {
                    '_context': context,
                    'params': context.params,
                    'outputs': context.outputs,
                    'cache_dir': str(context.cache_dir)
                }
                
                # 执行阶段
                result = await stage.execute(execute_context)
                
                # 记录结果
                self.stages_results.append(result)
                
                # 保存阶段输出
                if result['success']:
                    context.set_stage_output(stage.name, result.get('data', {}))
                    
                    # 如果是视频获取阶段，保存视频信息
                    if stage.name == 'unified_video_fetch':
                        video_processed = result.get('data', {})
                        # 更新params供后续阶段使用
                        context.params['video_id'] = video_processed.get('video_id')
                        context.params['creator_id'] = video_processed.get('creator_id')
                        context.params['platform'] = video_processed.get('platform')
                    
                    logger.info(f"[OK] Stage {stage.name} completed successfully")
                else:
                    # 强模式下，任何失败都终止Pipeline
                    if self.config.get('strict_mode', True):
                        logger.error(f"[FAILED] Stage {stage.name} failed: {result.get('error')}")
                        
                        # 如果有视频正在处理，标记为失败
                        if video_processed and self.config.get('mark_completed', True):
                            await self._mark_video_failed(
                                context,
                                video_processed,
                                f"Stage {stage.name} failed: {result.get('error')}"
                            )
                        
                        self.end_time = datetime.now()
                        return {
                            'success': False,
                            'error': f"Stage '{stage.name}' failed: {result.get('error')}",
                            'stage': stage.name,
                            'stages': self.stages_results,
                            'summary': self.get_execution_summary()
                        }
            
            # Pipeline成功完成，标记视频为已完成
            if video_processed and self.config.get('mark_completed', True):
                await self._mark_video_completed(context, video_processed)
            
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
                    'platform': params.get('platform'),
                    'account_id': params.get('account_id'),
                    **outputs
                },
                'stages': self.stages_results,
                'summary': self.get_execution_summary(),
                'metadata': {
                    'pipeline_type': 'unified_story_pipeline',
                    'config': self.config
                }
            }
            
            # 如果有视频路径，添加到结果中
            if 'video_export' in outputs and outputs['video_export'].get('video_path'):
                result['video_path'] = outputs['video_export']['video_path']
            
            # 如果有发布结果，添加到结果中
            if 'youtube_publish' in outputs and outputs['youtube_publish'].get('video_url'):
                result['video_url'] = outputs['youtube_publish']['video_url']
            
            logger.info(f"[SUCCESS] UnifiedStoryPipeline completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] UnifiedStoryPipeline failed: {e}")
            
            # 如果有视频正在处理，标记为失败
            if video_processed and self.config.get('mark_completed', True):
                await self._mark_video_failed(context, video_processed, str(e))
            
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
        
        # 1. 统一视频获取阶段（必需）
        stages.append(PipelineStage(
            name='unified_video_fetch',
            handler=unified_video_fetch_stage,
            required=True,
            config=self.config.get('fetch_config', {})
        ))
        
        # 2. 故事生成阶段
        if self.config.get('enable_story', True):
            stages.append(PipelineStage(
                name='story_generation',
                handler=pipeline_stages.story_generation_stage,
                required=is_strict or self.config.get('story_required', True),
                config=self.config.get('story_config', {})
            ))
        
        # 3. TTS生成阶段
        if self.config.get('enable_tts', True):
            stages.append(PipelineStage(
                name='tts_generation',
                handler=pipeline_stages.tts_generation_stage,
                required=is_strict or self.config.get('tts_required', True),
                config=self.config.get('tts_config', {})
            ))
        
        # 4. 草稿生成阶段
        if self.config.get('enable_draft', True):
            stages.append(PipelineStage(
                name='draft_generation',
                handler=pipeline_stages.draft_generation_stage,
                required=is_strict or self.config.get('draft_required', True),
                config=self.config.get('draft_config', {})
            ))
        
        # 5. 视频导出阶段
        if self.config.get('enable_video_export', True):
            stages.append(PipelineStage(
                name='video_export',
                handler=pipeline_stages.video_export_stage,
                required=True,  # 视频导出始终是必需的
                config=self.config.get('video_config', {})
            ))
        
        # 6. YouTube发布阶段
        if self.config.get('enable_publish', True):
            stages.append(PipelineStage(
                name='youtube_publish',
                handler=pipeline_stages.youtube_publish_stage,
                required=True,  # 发布始终是必需的
                config=self.config.get('publish_config', {})
            ))
        
        logger.info(f"Built {len(stages)} stages for execution")
        return stages
    
    async def _mark_video_completed(self, context: PipelineContext, video_info: Dict[str, Any]):
        """
        标记视频为已完成
        """
        mark_context = {
            'params': {
                'platform': video_info.get('platform'),
                'creator_id': video_info.get('creator_id'),
                'video_id': video_info.get('video_id'),
                'status': 'completed'
            }
        }
        
        result = await mark_video_status_stage(mark_context)
        if result['success']:
            logger.info(f"Marked video as completed: {video_info.get('video_id')}")
        else:
            logger.error(f"Failed to mark video as completed: {result.get('error')}")
    
    async def _mark_video_failed(self, context: PipelineContext, video_info: Dict[str, Any], error_msg: str):
        """
        标记视频为失败
        """
        mark_context = {
            'params': {
                'platform': video_info.get('platform'),
                'creator_id': video_info.get('creator_id'),
                'video_id': video_info.get('video_id'),
                'status': 'failed',
                'error_msg': error_msg
            }
        }
        
        result = await mark_video_status_stage(mark_context)
        if result['success']:
            logger.info(f"Marked video as failed: {video_info.get('video_id')}")
        else:
            logger.error(f"Failed to mark video as failed: {result.get('error')}")


# 示例配置
EXAMPLE_CONFIG = {
    'platform': 'youtube',  # 或 'douyin'
    'enable_story': True,
    'enable_tts': True,
    'enable_draft': True,
    'enable_video_export': True,
    'enable_publish': True,
    'mark_completed': True,
    'strict_mode': True,
    
    'fetch_config': {
        'max_videos': 10,  # 多创作者模式下每个创作者获取的视频数
        'days_back': 30,   # 单创作者模式下获取多少天内的视频
        # 'youtube_api_key': 'YOUR_API_KEY',  # YouTube API密钥（可选）
        # 'douyin_api_url': 'http://localhost:51084',  # 抖音API地址
    },
    
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


if __name__ == "__main__":
    """测试代码"""
    import asyncio
    
    async def test_pipeline():
        """测试Pipeline"""
        print("=" * 60)
        print("测试 UnifiedStoryPipeline")
        print("=" * 60)
        
        # 创建Pipeline
        pipeline = UnifiedStoryPipeline(EXAMPLE_CONFIG)
        
        # 测试参数
        params = {
            'creator_list': [
                'UCH9vY_kzBKhDDrpMavKxTIQ',  # YouTube创作者ID
                # 'MS4wLjABAAAA...',  # 抖音创作者ID
            ],
            'account_id': 'test_account',
            'platform': 'youtube',  # 或 'douyin'
            'duration': 300
        }
        
        # 执行Pipeline
        result = await pipeline.execute(params)
        
        # 打印结果
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 运行测试
    asyncio.run(test_pipeline())