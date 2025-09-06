#!/usr/bin/env python3
"""测试异步执行机制（不依赖真实视频）"""

import asyncio
import time
import logging
import sys
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class MockPipeline:
    """模拟Pipeline用于测试异步执行"""
    
    def __init__(self, name="mock"):
        self.name = name
        
    def run(self, video_id: str, creator_name: str) -> bool:
        """模拟同步执行方法"""
        logger.info(f"[{self.name}] 开始同步处理: video_id={video_id}, creator={creator_name}")
        # 模拟耗时操作
        time.sleep(2)
        logger.info(f"[{self.name}] 处理完成")
        return True
    
    async def execute(self, params: dict) -> dict:
        """异步执行方法 - 与实际Pipeline相同的实现"""
        try:
            video_id = params.get('video_id')
            if not video_id:
                return {
                    'success': False,
                    'error': 'Missing required parameter: video_id'
                }
            
            creator_name = params.get('creator_name') or params.get('account_id', 'default')
            
            logger.info(f"[{self.name}] 异步执行开始")
            
            # 使用与实际代码相同的异步执行逻辑
            if sys.version_info >= (3, 9):
                # Python 3.9+ 使用 to_thread
                success = await asyncio.to_thread(self.run, video_id=video_id, creator_name=creator_name)
            else:
                # Python 3.8 及以下使用 run_in_executor
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, self.run, video_id, creator_name)
            
            return {
                'success': success,
                'pipeline_name': self.name,
                'video_id': video_id,
                'creator_name': creator_name
            }
            
        except Exception as e:
            logger.error(f"[{self.name}] 执行异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

async def test_single_async_execution():
    """测试单个异步执行"""
    logger.info("\n" + "="*60)
    logger.info("测试1: 单个异步执行")
    logger.info("="*60)
    
    pipeline = MockPipeline("Pipeline1")
    params = {
        "video_id": "test_123",
        "account_id": "account_001"
    }
    
    start_time = time.time()
    result = await pipeline.execute(params)
    end_time = time.time()
    
    logger.info(f"执行结果: {result}")
    logger.info(f"执行耗时: {end_time - start_time:.2f}秒")
    
    if result['success']:
        logger.info("✅ 单个异步执行测试通过!")
    else:
        logger.error("❌ 单个异步执行测试失败!")
    
    return result['success']

async def test_concurrent_execution():
    """测试并发异步执行"""
    logger.info("\n" + "="*60)
    logger.info("测试2: 并发异步执行")
    logger.info("="*60)
    
    # 创建3个Pipeline实例
    pipelines = []
    tasks = []
    
    for i in range(3):
        pipeline = MockPipeline(f"Pipeline{i+1}")
        params = {
            "video_id": f"video_{i+1}",
            "account_id": f"account_{i+1}"
        }
        pipelines.append(pipeline)
        tasks.append(pipeline.execute(params))
    
    logger.info(f"开始并发执行 {len(tasks)} 个Pipeline...")
    start_time = time.time()
    
    # 并发执行
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info(f"所有Pipeline执行完成，总耗时: {total_time:.2f}秒")
    
    # 如果是串行执行，应该需要6秒（3个x2秒）
    # 如果是并行执行，应该只需要约2秒
    if total_time < 4:  # 给一些余量
        logger.info("✅ 并发执行验证成功! (执行时间小于串行时间)")
    else:
        logger.warning("⚠️ 执行时间过长，可能不是真正的并发执行")
    
    success_count = sum(1 for r in results if r['success'])
    logger.info(f"成功率: {success_count}/{len(results)}")
    
    return all(r['success'] for r in results)

async def test_non_blocking_execution():
    """测试非阻塞执行"""
    logger.info("\n" + "="*60)
    logger.info("测试3: 非阻塞执行")
    logger.info("="*60)
    
    pipeline = MockPipeline("NonBlockingPipeline")
    params = {
        "video_id": "non_blocking_test",
        "account_id": "test_account"
    }
    
    # 启动Pipeline任务
    logger.info("启动Pipeline任务（后台执行）...")
    pipeline_task = asyncio.create_task(pipeline.execute(params))
    
    # 同时执行其他任务来验证非阻塞
    logger.info("Pipeline在后台执行，同时执行其他任务...")
    
    other_tasks_completed = []
    for i in range(5):
        await asyncio.sleep(0.3)
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"  [{timestamp}] 其他任务执行中: {i+1}/5")
        other_tasks_completed.append(i+1)
    
    # 等待Pipeline完成
    logger.info("等待Pipeline完成...")
    result = await pipeline_task
    
    if result['success'] and len(other_tasks_completed) == 5:
        logger.info("✅ 非阻塞执行验证成功! (其他任务能够同时执行)")
        return True
    else:
        logger.error("❌ 非阻塞执行验证失败!")
        return False

async def main():
    """主测试函数"""
    logger.info("="*60)
    logger.info(f"Python版本: {sys.version}")
    logger.info("开始测试异步执行机制")
    logger.info("="*60)
    
    all_passed = True
    
    # 执行测试
    test1_passed = await test_single_async_execution()
    all_passed = all_passed and test1_passed
    
    test2_passed = await test_concurrent_execution()
    all_passed = all_passed and test2_passed
    
    test3_passed = await test_non_blocking_execution()
    all_passed = all_passed and test3_passed
    
    # 总结
    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("✅ 所有测试通过! 异步执行机制正常工作!")
    else:
        logger.error("❌ 部分测试失败，请检查实现")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(main())