#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试StoryFullPipeline
测试新的模块化Pipeline架构
"""

import asyncio
import logging
import sys
import json
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

# 导入Pipeline和注册表
from pipelines.story_full_pipeline import StoryFullPipeline, EXAMPLE_CONFIG
from pipeline_registry import register_story_full_pipeline, get_pipeline_registry


async def test_direct_instantiation():
    """测试直接实例化Pipeline"""
    logger.info("=" * 60)
    logger.info("测试1: 直接实例化StoryFullPipeline")
    logger.info("=" * 60)
    
    # 自定义配置
    config = {
        'enable_story': True,      # 启用故事生成
        'enable_tts': True,        # 启用TTS
        'enable_draft': True,      # 启用草稿生成
        'enable_publish': False,   # 禁用发布（测试环境）
        'cache_strategy': 'none',  # 禁用缓存，确保全流程执行
        
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
        }
    }
    
    # 创建Pipeline实例
    pipeline = StoryFullPipeline(config)
    
    # 测试参数
    params = {
        'video_id': 'jNQXAC9IVRw',  # 使用真实的YouTube视频ID进行测试
        'creator_id': 'test_creator',
        'account_id': 'test_account'
    }
    
    try:
        # 执行Pipeline
        logger.info(f"开始执行Pipeline: {params}")
        result = await pipeline.execute(params)
        
        # 打印结果
        if result['success']:
            logger.info("✅ Pipeline执行成功!")
            logger.info(f"输出目录: {result['data'].get('cache_dir')}")
            logger.info(f"执行摘要: {json.dumps(result['summary'], indent=2, ensure_ascii=False)}")
            
            # 打印各阶段结果
            logger.info("\n各阶段执行结果:")
            for stage in result['stages']:
                status = "✅" if stage['success'] else "❌"
                logger.info(f"  {status} {stage['name']}: {stage.get('duration', 0):.2f}s")
        else:
            logger.error(f"❌ Pipeline执行失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_registry():
    """测试通过注册表使用Pipeline"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 通过注册表使用Pipeline")
    logger.info("=" * 60)
    
    # 注册Pipeline
    success = register_story_full_pipeline()
    if success:
        logger.info("✅ Pipeline注册成功")
    else:
        logger.info("⚠️ Pipeline已注册或注册失败")
    
    # 获取注册表
    registry = get_pipeline_registry()
    
    # 获取Pipeline元数据
    metadata = registry.get_pipeline("story_full_pipeline")
    if metadata:
        logger.info(f"Pipeline元数据:")
        logger.info(f"  - ID: {metadata.pipeline_id}")
        logger.info(f"  - 名称: {metadata.pipeline_name}")
        logger.info(f"  - 类型: {metadata.pipeline_type}")
        logger.info(f"  - 版本: {metadata.version}")
        logger.info(f"  - 状态: {metadata.status}")
        
        # 创建实例
        config = {
            'enable_story': True,
            'enable_tts': False,    # 跳过TTS测试
            'enable_draft': False,  # 跳过草稿生成测试
            'enable_publish': False,
            'cache_strategy': 'none'
        }
        
        instance = registry.create_instance("story_full_pipeline", config)
        if instance:
            logger.info("✅ 通过注册表创建实例成功")
            
            # 执行测试
            params = {
                'video_id': 'test_video_456',
                'creator_id': 'registry_test',
                'account_id': 'registry_account'
            }
            
            result = await instance.execute(params)
            if result['success']:
                logger.info("✅ 通过注册表执行Pipeline成功")
            else:
                logger.error(f"❌ 执行失败: {result.get('error')}")
        else:
            logger.error("❌ 创建实例失败")
    else:
        logger.error("❌ 获取Pipeline元数据失败")


async def test_optional_stages():
    """测试可选阶段配置"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 可选阶段配置（仅执行必需的视频导出）")
    logger.info("=" * 60)
    
    # 仅启用视频导出（必需阶段）
    config = {
        'enable_story': False,     # 禁用故事生成
        'enable_tts': False,       # 禁用TTS
        'enable_draft': False,     # 禁用草稿生成
        'enable_publish': False,   # 禁用发布
        'cache_strategy': 'none'
    }
    
    pipeline = StoryFullPipeline(config)
    
    params = {
        'video_id': 'minimal_test',
        'creator_id': 'minimal_creator',
        'account_id': 'minimal_account',
        # 视频导出需要的参数
        'draft_path': '/path/to/existing/draft',  # 假设已存在草稿
    }
    
    try:
        result = await pipeline.execute(params)
        
        if result['success']:
            logger.info("✅ 仅执行必需阶段成功")
            
            # 验证只执行了video_export阶段
            executed_stages = [s['name'] for s in result['stages']]
            logger.info(f"执行的阶段: {executed_stages}")
            
            if executed_stages == ['video_export']:
                logger.info("✅ 确认仅执行了视频导出阶段")
            else:
                logger.warning(f"⚠️ 执行了额外的阶段: {executed_stages}")
        else:
            logger.error(f"❌ 执行失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")


async def test_error_handling():
    """测试错误处理"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 错误处理")
    logger.info("=" * 60)
    
    pipeline = StoryFullPipeline()
    
    # 缺少必需参数的测试
    params = {
        'creator_id': 'error_test'
        # 缺少video_id
    }
    
    result = await pipeline.execute(params)
    
    if not result['success']:
        logger.info(f"✅ 正确处理缺少参数: {result.get('error')}")
    else:
        logger.error("❌ 未能检测到缺少的参数")
    
    # 无效的video_id测试
    params = {
        'video_id': 'invalid_id_12345',
        'creator_id': 'error_test'
    }
    
    result = await pipeline.execute(params)
    
    if not result['success']:
        logger.info(f"✅ 正确处理无效参数: Stage '{result.get('stage')}' failed")
    else:
        logger.warning("⚠️ 未预期的成功执行")


async def main():
    """主测试函数"""
    logger.info("🚀 开始测试StoryFullPipeline")
    logger.info("=" * 60)
    
    # 运行各项测试
    tests = [
        ("直接实例化测试", test_direct_instantiation),
        ("注册表测试", test_registry),
        ("可选阶段测试", test_optional_stages),
        ("错误处理测试", test_error_handling)
    ]
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n📋 运行: {test_name}")
            await test_func()
        except Exception as e:
            logger.error(f"❌ {test_name}失败: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())