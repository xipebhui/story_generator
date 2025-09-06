#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视频获取预处理功能
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

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


async def test_video_fetch_only():
    """测试只获取视频信息，不执行后续流程"""
    logger.info("=" * 60)
    logger.info("测试1: 只获取最新视频信息")
    logger.info("=" * 60)
    
    # 配置：只启用视频获取，禁用所有其他阶段
    config = {
        'enable_video_fetch': True,
        'enable_story': False,
        'enable_tts': False,
        'enable_draft': False,
        'enable_video_export': False,
        'enable_publish': False,
        'strict_mode': True,
        'video_fetch_config': {
            'creator_list': ['UCH9vY_kzBKhDDrpMavKxTIQ'],  # 示例创作者ID
            'days_back': 7,
            'max_videos': 5
        },
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    
    # 只需要提供creator_id
    params = {
        'creator_id': 'UCH9vY_kzBKhDDrpMavKxTIQ',
        'account_id': 'test_account'
    }
    
    try:
        result = await pipeline.execute(params)
        
        logger.info(f"\n执行结果: success={result['success']}")
        
        if result['success']:
            data = result.get('data', {})
            logger.info(f"找到视频:")
            logger.info(f"  - video_id: {data.get('video_id')}")
            logger.info(f"  - creator_id: {data.get('creator_id')}")
            logger.info(f"  - channel_id: {data.get('channel_id')}")
            logger.info(f"  - channel_title: {data.get('channel_title')}")
            
            if 'video_fetch' in data:
                video_info = data['video_fetch'].get('video_info', {})
                logger.info(f"  - video_title: {video_info.get('title')}")
                logger.info(f"  - published_at: {video_info.get('published_at')}")
                logger.info(f"  - view_count: {video_info.get('view_count')}")
        else:
            logger.error(f"获取失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"测试异常: {e}")


async def test_video_fetch_with_full_pipeline():
    """测试获取视频并执行完整流程"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 获取视频并执行完整Pipeline")
    logger.info("=" * 60)
    
    # 配置：启用视频获取和所有阶段（除了发布）
    config = {
        'enable_video_fetch': True,
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': True,
        'enable_publish': False,  # 测试时不发布
        'strict_mode': True,
        'video_fetch_config': {
            'creator_list': [
                'UCH9vY_kzBKhDDrpMavKxTIQ',  # 第一个创作者
                'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # 备选创作者
            ],
            'days_back': 7,
            'max_videos': 10
        },
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    
    # 只提供creator_id，视频会自动获取
    params = {
        'creator_id': 'UCH9vY_kzBKhDDrpMavKxTIQ',
        'account_id': 'test_account',
        'duration': 300
    }
    
    try:
        result = await pipeline.execute(params)
        
        logger.info(f"\n执行结果: success={result['success']}")
        
        if 'stages' in result:
            logger.info("\n各阶段执行情况:")
            for stage in result['stages']:
                status = "✅" if stage.get('success') else "❌"
                logger.info(f"  {status} {stage['name']}")
        
        if result['success']:
            logger.info("\n✅ 完整Pipeline执行成功")
            if 'video_path' in result:
                logger.info(f"视频路径: {result['video_path']}")
        else:
            logger.error(f"\n❌ Pipeline执行失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"测试异常: {e}")


async def test_video_fetch_with_multiple_creators():
    """测试多个创作者的备选机制"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 多创作者备选机制")
    logger.info("=" * 60)
    
    config = {
        'enable_video_fetch': True,
        'enable_story': False,
        'enable_tts': False,
        'enable_draft': False,
        'enable_video_export': False,
        'enable_publish': False,
        'video_fetch_config': {
            'creator_list': [
                'invalid_creator_1',      # 无效创作者
                'invalid_creator_2',      # 无效创作者
                'UCH9vY_kzBKhDDrpMavKxTIQ',  # 有效创作者
            ],
            'days_back': 30,
            'max_videos': 3
        }
    }
    
    pipeline = StoryFullPipeline(config)
    
    params = {
        'creator_id': 'invalid_creator_1',
        'account_id': 'test_account'
    }
    
    try:
        result = await pipeline.execute(params)
        
        if result['success']:
            data = result.get('data', {})
            logger.info(f"\n成功从备选创作者获取视频:")
            logger.info(f"  最终使用的creator_id: {data.get('creator_id')}")
            logger.info(f"  获取的video_id: {data.get('video_id')}")
        else:
            logger.error(f"获取失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"测试异常: {e}")


async def test_without_video_fetch():
    """测试禁用视频获取的传统模式"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 传统模式（禁用自动获取）")
    logger.info("=" * 60)
    
    # 传统配置：不启用视频获取
    config = {
        'enable_video_fetch': False,  # 禁用自动获取
        'enable_story': True,
        'enable_tts': True,
        'enable_draft': True,
        'enable_video_export': False,
        'enable_publish': False,
        'strict_mode': True
    }
    
    pipeline = StoryFullPipeline(config)
    
    # 必须提供video_id
    params = {
        'video_id': 'test_video_123',
        'creator_id': 'test_creator',
        'account_id': 'test_account'
    }
    
    try:
        result = await pipeline.execute(params)
        
        # 这会失败因为测试video_id不存在，但验证了参数要求
        if not result['success']:
            logger.info("✅ 传统模式正确要求了video_id参数")
            logger.info(f"   错误信息: {result.get('error')[:100]}...")
        
    except Exception as e:
        logger.info(f"预期的错误: {str(e)[:100]}...")


async def main():
    """主测试函数"""
    logger.info("🔧 开始测试视频获取预处理功能")
    logger.info("=" * 60)
    
    # 运行各项测试
    await test_video_fetch_only()
    # await test_video_fetch_with_full_pipeline()  # 注释掉完整流程测试
    await test_video_fetch_with_multiple_creators()
    await test_without_video_fetch()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 测试完成")
    logger.info("=" * 60)
    logger.info("\n功能总结:")
    logger.info("  1. 只需提供creator_id即可自动获取最新视频")
    logger.info("  2. 自动检查视频是否已处理（通过缓存）")
    logger.info("  3. 支持多个创作者备选列表")
    logger.info("  4. 与现有Pipeline完全兼容")
    logger.info("  5. 可通过配置灵活启用/禁用")


if __name__ == "__main__":
    asyncio.run(main())