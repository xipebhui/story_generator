#!/usr/bin/env python3
"""测试Pipeline执行修复"""

import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def test_pipeline_import():
    """测试Pipeline类的导入"""
    try:
        # 测试动态导入
        pipeline_class_str = "story_pipeline_v3_runner.StoryPipelineV3Runner"
        module_name, class_name = pipeline_class_str.rsplit('.', 1)
        logger.info(f"模块名: {module_name}, 类名: {class_name}")
        
        import importlib
        module = importlib.import_module(module_name)
        logger.info(f"成功导入模块: {module}")
        
        pipeline_class = getattr(module, class_name)
        logger.info(f"成功获取Pipeline类: {pipeline_class}")
        
        # 创建实例测试
        test_config = {"video_id": "test_123"}
        pipeline_instance = pipeline_class(test_config)
        logger.info(f"成功创建Pipeline实例: {pipeline_instance}")
        
        print("✅ Pipeline导入和实例化测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_pipeline_import())
    if result:
        print("\n✅ 所有测试通过！Pipeline修复成功！")
    else:
        print("\n❌ 测试失败，请检查错误日志")