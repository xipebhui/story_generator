#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动槽位生成器
定期为每日定时任务生成槽位
"""

import asyncio
import logging
from datetime import datetime, timedelta
from generate_daily_slots import process_daily_configs

logger = logging.getLogger(__name__)

class AutoSlotGenerator:
    """自动槽位生成器"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 3600  # 每小时检查一次
        
    async def start(self):
        """启动生成器"""
        self.running = True
        logger.info("自动槽位生成器启动")
        
        while self.running:
            try:
                # 每天凌晨1点生成未来7天的槽位
                now = datetime.now()
                if now.hour == 1 and now.minute < 10:
                    logger.info("开始生成每日定时任务槽位...")
                    process_daily_configs()
                    
                    # 等待到下个小时，避免重复生成
                    await asyncio.sleep(3600)
                else:
                    # 每小时检查一次
                    await asyncio.sleep(self.check_interval)
                    
            except Exception as e:
                logger.error(f"槽位生成异常: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """停止生成器"""
        self.running = False
        logger.info("自动槽位生成器停止")

def get_auto_slot_generator():
    """获取槽位生成器实例"""
    return AutoSlotGenerator()

if __name__ == "__main__":
    # 测试运行
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config_loader import load_env_file
    load_env_file()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 立即生成一次槽位
    logger.info("手动触发槽位生成...")
    process_daily_configs()
    logger.info("槽位生成完成")