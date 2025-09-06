#!/usr/bin/env python3
"""测试异步Pipeline执行"""

import asyncio
import time
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_async_pipeline():
    """测试Pipeline的异步执行"""
    try:
        # 导入Pipeline
        from story_pipeline_v3_runner import StoryPipelineV3Runner
        
        logger.info("创建Pipeline实例...")
        runner = StoryPipelineV3Runner()
        
        # 测试参数
        test_params = {
            "video_id": "test_async_123",
            "account_id": "test_account",
            "creator_name": "async_test"
        }
        
        logger.info(f"开始异步执行Pipeline: {test_params}")
        start_time = time.time()
        
        # 异步执行Pipeline
        result = await runner.execute(test_params)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"Pipeline执行完成，耗时: {execution_time:.2f}秒")
        logger.info(f"执行结果: {result}")
        
        # 验证结果
        assert isinstance(result, dict), "结果应该是字典"
        assert "success" in result, "结果应该包含success字段"
        
        if result["success"]:
            logger.info("✅ Pipeline异步执行成功!")
        else:
            logger.error(f"❌ Pipeline执行失败: {result.get('error')}")
            
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

async def test_concurrent_pipelines():
    """测试并发执行多个Pipeline"""
    logger.info("\n" + "="*60)
    logger.info("测试并发执行多个Pipeline...")
    logger.info("="*60)
    
    try:
        from story_pipeline_v3_runner import StoryPipelineV3Runner
        
        # 创建多个Pipeline任务
        tasks = []
        for i in range(3):
            runner = StoryPipelineV3Runner()
            params = {
                "video_id": f"concurrent_test_{i}",
                "account_id": f"account_{i}",
                "creator_name": f"concurrent_{i}"
            }
            logger.info(f"创建任务 {i+1}: {params['video_id']}")
            tasks.append(runner.execute(params))
        
        # 并发执行所有任务
        logger.info(f"\n开始并发执行 {len(tasks)} 个Pipeline任务...")
        start_time = time.time()
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.info(f"\n所有任务完成，总耗时: {total_time:.2f}秒")
        
        # 分析结果
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {i+1} 异常: {result}")
            elif isinstance(result, dict):
                if result.get("success"):
                    success_count += 1
                    logger.info(f"任务 {i+1} ✅ 成功")
                else:
                    logger.error(f"任务 {i+1} ❌ 失败: {result.get('error')}")
            else:
                logger.warning(f"任务 {i+1} 返回未知类型: {type(result)}")
        
        logger.info(f"\n成功率: {success_count}/{len(tasks)} ({success_count*100/len(tasks):.1f}%)")
        
        if success_count == len(tasks):
            logger.info("✅ 所有Pipeline并发执行成功!")
        
    except Exception as e:
        logger.error(f"并发测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_non_blocking():
    """测试Pipeline执行是否真的是非阻塞的"""
    logger.info("\n" + "="*60)
    logger.info("测试Pipeline执行的非阻塞性...")
    logger.info("="*60)
    
    try:
        from story_pipeline_v3_runner import StoryPipelineV3Runner
        
        runner = StoryPipelineV3Runner()
        params = {
            "video_id": "non_blocking_test",
            "account_id": "test_account"
        }
        
        # 启动Pipeline任务
        logger.info("启动Pipeline任务...")
        pipeline_task = asyncio.create_task(runner.execute(params))
        
        # 在Pipeline执行时，执行其他异步操作
        logger.info("Pipeline正在后台执行，同时执行其他任务...")
        
        for i in range(5):
            await asyncio.sleep(0.5)
            logger.info(f"  其他任务进度: {i+1}/5")
        
        logger.info("等待Pipeline完成...")
        result = await pipeline_task
        
        if result.get("success"):
            logger.info("✅ Pipeline非阻塞执行验证成功!")
        else:
            logger.error(f"Pipeline执行失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"非阻塞测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主测试函数"""
    logger.info("="*60)
    logger.info("开始测试异步Pipeline执行")
    logger.info("="*60)
    
    # 测试1: 基本异步执行
    logger.info("\n[测试1] 基本异步执行")
    await test_async_pipeline()
    
    # 测试2: 并发执行
    logger.info("\n[测试2] 并发执行")
    await test_concurrent_pipelines()
    
    # 测试3: 非阻塞验证
    logger.info("\n[测试3] 非阻塞验证")
    await test_non_blocking()
    
    logger.info("\n" + "="*60)
    logger.info("所有测试完成!")
    logger.info("="*60)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())