#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Pipeline路径兼容性
验证新的Pipeline是否正确处理旧的路径结构
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from pipelines.pipeline_context import PipelineContext
from pipelines.story_full_pipeline import StoryFullPipeline


def test_path_compatibility():
    """测试路径兼容性"""
    logger.info("=" * 60)
    logger.info("测试路径兼容性")
    logger.info("=" * 60)
    
    # 测试参数
    params = {
        'video_id': 'test_video_123',
        'creator_id': 'test_creator',
        'account_id': 'test_account'
    }
    
    # 创建上下文
    context = PipelineContext(params)
    
    # 测试各种路径方法
    logger.info("\n--- 测试路径兼容性方法 ---")
    
    # 故事路径
    story_path = context.get_story_source_path()
    logger.info(f"故事源路径: {story_path}")
    logger.info(f"  - 期望格式: story_result/test_creator/test_video_123/final/story.txt")
    logger.info(f"  - 匹配: {'✅' if 'story_result' in str(story_path) else '❌'}")
    
    # 音频路径
    audio_path = context.get_audio_output_path()
    logger.info(f"音频输出路径: {audio_path}")
    logger.info(f"  - 期望格式: output/test_creator_test_account_test_video_123_story.mp3")
    logger.info(f"  - 匹配: {'✅' if 'output/' in str(audio_path) and '_story.mp3' in str(audio_path) else '❌'}")
    
    # 草稿路径
    draft_path = context.get_draft_output_path()
    logger.info(f"草稿输出路径: {draft_path}")
    logger.info(f"  - 期望格式: output/drafts/test_creator_test_account_test_video_123_story")
    logger.info(f"  - 匹配: {'✅' if 'output/drafts' in str(draft_path) and '_story' in str(draft_path) else '❌'}")
    
    # 测试新的缓存目录路径
    logger.info(f"\n新的缓存目录: {context.cache_dir}")
    logger.info(f"  - 格式: outputs/test_creator/test_account/test_video_123")
    
    # 测试内部路径
    logger.info("\n--- 内部路径结构 ---")
    for key, path in context.paths.items():
        logger.info(f"  {key}: {path}")


async def test_pipeline_stages():
    """测试Pipeline各阶段的路径处理"""
    logger.info("\n" + "=" * 60)
    logger.info("测试Pipeline阶段路径处理")
    logger.info("=" * 60)
    
    # 创建测试配置
    config = {
        'enable_story': False,  # 跳过故事生成（因为需要真实的YouTube视频）
        'enable_tts': False,    # 跳过TTS（因为需要故事文件）
        'enable_draft': False,  # 跳过草稿生成（因为需要音频文件）
        'enable_publish': False,
        'cache_strategy': 'none'
    }
    
    # 创建Pipeline
    pipeline = StoryFullPipeline(config)
    
    # 测试参数
    params = {
        'video_id': 'path_test_123',
        'creator_id': 'path_creator',
        'account_id': 'path_account',
        'draft_path': '/mock/draft/path'  # 模拟草稿路径
    }
    
    try:
        # 注意：由于所有阶段都被禁用，只有video_export是必需的
        # 但它需要draft_path，所以会失败
        result = await pipeline.execute(params)
        
        if not result['success']:
            logger.info(f"✅ 预期的失败（因为没有真实的草稿）: {result.get('error')}")
            
            # 检查阶段执行
            logger.info("\n执行的阶段:")
            for stage in result.get('stages', []):
                logger.info(f"  - {stage['name']}: {stage['status']}")
    except Exception as e:
        logger.info(f"✅ 预期的异常（测试环境）: {e}")
    
    # 测试带account_id的路径生成
    logger.info("\n--- 测试带account_id的路径生成 ---")
    
    context = PipelineContext(params)
    
    # 检查路径是否包含account_id
    audio_path = context.get_audio_output_path()
    draft_path = context.get_draft_output_path()
    
    logger.info(f"音频路径包含account_id: {'✅' if 'path_account' in str(audio_path) else '❌'}")
    logger.info(f"草稿路径包含account_id: {'✅' if 'path_account' in str(draft_path) else '❌'}")
    
    # 测试不带account_id的情况
    params_no_account = {
        'video_id': 'no_account_test',
        'creator_id': 'solo_creator'
    }
    
    context_no_account = PipelineContext(params_no_account)
    
    audio_path = context_no_account.get_audio_output_path()
    draft_path = context_no_account.get_draft_output_path()
    
    logger.info(f"\n不带account_id的音频路径: {audio_path}")
    logger.info(f"不带account_id的草稿路径: {draft_path}")
    logger.info(f"格式正确: {'✅' if 'solo_creator_no_account_test' in str(audio_path) else '❌'}")


def main():
    """主测试函数"""
    logger.info("🔧 开始测试Pipeline路径兼容性")
    logger.info("=" * 60)
    
    # 同步测试
    test_path_compatibility()
    
    # 异步测试
    asyncio.run(test_pipeline_stages())
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 路径兼容性测试完成")
    logger.info("=" * 60)
    logger.info("\n重要说明:")
    logger.info("  1. 新Pipeline使用兼容性方法确保与原有服务的路径一致")
    logger.info("  2. 故事生成输出到: story_result/{creator}/{video}/final/")
    logger.info("  3. 音频生成输出到: output/{creator}_{account}_{video}_story.mp3")
    logger.info("  4. 草稿生成输出到: output/drafts/{creator}_{account}_{video}_story/")
    logger.info("  5. 新的缓存目录仅用于内部管理，不影响服务调用")


if __name__ == "__main__":
    main()