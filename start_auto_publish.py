#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动发布系统启动脚本
启动账号驱动的自动发布服务
"""

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from config_loader import load_env_file
load_env_file()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('auto_publish.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 导入服务模块
from database import init_database
from account_service import get_account_service
from pipeline_registry import get_pipeline_registry
from ring_scheduler import get_ring_scheduler
from account_driven_executor import get_account_driven_executor
from platform_monitor import get_platform_monitor
from strategy_engine import get_strategy_engine

# 全局变量
executor = None
monitor = None
running = True

def signal_handler(signum, frame):
    """信号处理器"""
    global running
    logger.info(f"收到信号 {signum}，准备停止服务...")
    running = False

async def initialize_services():
    """初始化所有服务"""
    logger.info("初始化数据库...")
    init_database()
    
    logger.info("初始化账号服务...")
    account_service = get_account_service()
    account_service.initialize_accounts()
    
    logger.info("初始化Pipeline注册表...")
    pipeline_registry = get_pipeline_registry()
    
    logger.info("初始化环形调度器...")
    ring_scheduler = get_ring_scheduler()
    
    logger.info("初始化策略引擎...")
    strategy_engine = get_strategy_engine()
    
    logger.info("所有服务初始化完成")

async def start_executor():
    """启动执行器"""
    global executor
    logger.info("启动账号驱动执行器...")
    executor = get_account_driven_executor()
    
    # 创建执行器任务
    executor_task = asyncio.create_task(executor.start())
    
    # 等待执行器运行
    while running:
        await asyncio.sleep(1)
    
    # 停止执行器
    logger.info("停止执行器...")
    await executor.stop()
    
    # 取消执行器任务
    executor_task.cancel()
    try:
        await executor_task
    except asyncio.CancelledError:
        pass

async def start_monitor():
    """启动平台监控"""
    global monitor
    logger.info("启动平台监控器...")
    monitor = get_platform_monitor()
    
    # 创建监控任务
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    # 等待监控运行
    while running:
        await asyncio.sleep(1)
    
    # 停止监控
    logger.info("停止监控器...")
    await monitor.stop_monitoring()
    
    # 取消监控任务
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自动发布系统启动")
    logger.info("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化服务
        await initialize_services()
        
        # 创建并发任务
        tasks = [
            asyncio.create_task(start_executor()),
            asyncio.create_task(start_monitor())
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，停止服务...")
    except Exception as e:
        logger.error(f"服务异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("=" * 60)
        logger.info("自动发布系统已停止")
        logger.info("=" * 60)

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())