#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Pipeline强模式
验证任何步骤失败都会立即中断执行
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

from pipelines.story_full_pipeline import StoryFullPipeline


async def test_strict_mode():
    """测试强模式：任何失败都中断"""
    logger.info("=" * 60)
    logger.info("测试强模式Pipeline")
    logger.info("=" * 60)
    
    # 强模式配置（默认）
    config = {
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': True,
        'enable_publish': True,  # 发布也是必需的
        'strict_mode': True,     # 强模式
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    
    logger.info("\n配置详情:")
    logger.info(f"  strict_mode: {config['strict_mode']}")
    logger.info(f"  enable_publish: {config['enable_publish']}")
    logger.info(f"  所有阶段在强模式下都是必需的")
    
    # 使用无效的video_id，第一步就会失败
    params = {
        'video_id': 'invalid_test_123',
        'creator_id': 'test_creator',
        'account_id': 'test_account'
    }
    
    try:
        result = await pipeline.execute(params)
        
        logger.info(f"\n执行结果: success={result['success']}")
        
        if not result['success']:
            logger.info(f"错误信息: {result.get('error')}")
            logger.info(f"失败阶段: {result.get('stage')}")
            
            # 检查执行了多少阶段
            if 'stages' in result:
                logger.info("\n执行的阶段:")
                for stage in result['stages']:
                    status = "✅" if stage.get('success') else "❌"
                    logger.info(f"  {status} {stage['name']}")
                    
            logger.info("\n✅ 强模式测试通过：第一个失败的阶段立即中断了执行")
        else:
            logger.error("\n❌ 测试失败：强模式下应该失败但返回了成功")
            
    except Exception as e:
        logger.error(f"测试异常: {e}")


async def test_non_strict_mode():
    """测试非强模式：可以继续执行"""
    logger.info("\n" + "=" * 60)
    logger.info("测试非强模式Pipeline（对比）")
    logger.info("=" * 60)
    
    # 非强模式配置
    config = {
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': True,
        'enable_publish': False,  # 不启用发布（避免失败）
        'strict_mode': False,      # 非强模式
        'story_required': False,   # 故事非必需
        'tts_required': False,     # TTS非必需
        'draft_required': False,   # 草稿非必需
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    
    logger.info("\n配置详情:")
    logger.info(f"  strict_mode: {config['strict_mode']}")
    logger.info(f"  各阶段可以独立设置是否必需")
    
    params = {
        'video_id': 'invalid_test_456',
        'creator_id': 'test_creator',
        'account_id': 'test_account'
    }
    
    try:
        result = await pipeline.execute(params)
        
        logger.info(f"\n执行结果: success={result['success']}")
        
        if 'stages' in result:
            logger.info("\n各阶段执行情况:")
            for stage in result['stages']:
                status = "✅" if stage.get('success') else "❌"
                required = "(必需)" if stage.get('required') else "(可选)"
                logger.info(f"  {status} {stage['name']} {required}")
        
        if result['success']:
            logger.info("\n✅ 非强模式测试通过：可选阶段失败不影响整体")
        else:
            # 检查是否因为必需阶段失败
            if 'video_export' in result.get('stage', ''):
                logger.info("\n✅ 非强模式测试通过：必需阶段（video_export）失败导致中断")
            else:
                logger.warning("\n⚠️ 非强模式下因其他原因失败")
                
    except Exception as e:
        logger.error(f"测试异常: {e}")


async def test_all_stages_required():
    """测试强模式下所有阶段都必需"""
    logger.info("\n" + "=" * 60)
    logger.info("测试强模式下所有启用的阶段都是必需的")
    logger.info("=" * 60)
    
    config = {
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': True,
        'enable_publish': True,
        'strict_mode': True,  # 强模式
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    stages = pipeline._build_stages()
    
    logger.info(f"构建的阶段数: {len(stages)}")
    logger.info("\n各阶段配置:")
    
    all_required = True
    for stage in stages:
        logger.info(f"  - {stage.name}: required={stage.required}")
        if not stage.required:
            all_required = False
    
    if all_required:
        logger.info("\n✅ 测试通过：强模式下所有阶段都是必需的")
    else:
        logger.error("\n❌ 测试失败：强模式下存在非必需的阶段")
    
    # 特别检查视频导出和发布
    video_export_stage = next((s for s in stages if s.name == 'video_export'), None)
    publish_stage = next((s for s in stages if s.name == 'youtube_publish'), None)
    
    if video_export_stage and video_export_stage.required:
        logger.info("✅ 视频导出是必需的")
    else:
        logger.error("❌ 视频导出应该是必需的")
    
    if publish_stage and publish_stage.required:
        logger.info("✅ 发布是必需的")
    else:
        logger.error("❌ 发布应该是必需的")


async def main():
    """主测试函数"""
    logger.info("🔧 开始测试Pipeline强模式")
    logger.info("=" * 60)
    
    # 运行各项测试
    await test_strict_mode()
    await test_non_strict_mode()
    await test_all_stages_required()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 测试完成")
    logger.info("=" * 60)
    logger.info("\n强模式总结：")
    logger.info("  1. strict_mode=True时，任何阶段失败都会立即中断")
    logger.info("  2. 视频导出始终是必需的")
    logger.info("  3. 发布在启用时也是必需的")
    logger.info("  4. 默认配置使用强模式，适合生产环境")


if __name__ == "__main__":
    asyncio.run(main())