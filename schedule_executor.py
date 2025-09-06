#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的调度执行器
支持多种调度模式：间隔执行、Cron表达式、每日/每周/每月定时
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import croniter
import json

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """调度类型"""
    DAILY = "daily"      # 每天固定时间
    WEEKLY = "weekly"    # 每周固定时间
    MONTHLY = "monthly"  # 每月固定时间
    INTERVAL = "interval"  # 间隔执行
    CRON = "cron"       # Cron表达式
    ONCE = "once"       # 一次性执行


@dataclass
class ScheduleConfig:
    """调度配置"""
    config_id: str
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    is_active: bool = True


class ScheduleExecutor:
    """调度执行器"""
    
    def __init__(self):
        self.configs: Dict[str, ScheduleConfig] = {}
        self.running = False
        self.check_interval = 60  # 检查间隔（秒）
        self._task = None
        
    def add_config(self, config_id: str, trigger_config: Dict[str, Any]) -> bool:
        """
        添加调度配置
        
        Args:
            config_id: 配置ID
            trigger_config: 触发器配置
                - schedule_type: daily/weekly/monthly/interval/cron
                - 其他参数根据类型而定
        
        Returns:
            是否添加成功
        """
        try:
            schedule_type = ScheduleType(trigger_config.get('schedule_type', 'daily'))
            
            config = ScheduleConfig(
                config_id=config_id,
                schedule_type=schedule_type,
                schedule_config=trigger_config
            )
            
            # 计算下次运行时间
            config.next_run_time = self._calculate_next_run(config)
            
            self.configs[config_id] = config
            logger.info(f"添加调度配置: {config_id}, 下次运行: {config.next_run_time}")
            return True
            
        except Exception as e:
            logger.error(f"添加调度配置失败: {e}")
            return False
    
    def _calculate_next_run(self, config: ScheduleConfig, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        计算下次运行时间
        
        Args:
            config: 调度配置
            from_time: 起始时间（默认当前时间）
        
        Returns:
            下次运行时间
        """
        from_time = from_time or datetime.now()
        schedule_config = config.schedule_config
        
        try:
            if config.schedule_type == ScheduleType.DAILY:
                # 每天固定时间
                time_str = schedule_config.get('schedule_time', '10:00')
                hour, minute = map(int, time_str.split(':'))
                
                next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= from_time:
                    next_run += timedelta(days=1)
                return next_run
            
            elif config.schedule_type == ScheduleType.WEEKLY:
                # 每周固定时间
                days = schedule_config.get('schedule_days', [1])  # 默认周一
                time_str = schedule_config.get('schedule_time', '10:00')
                hour, minute = map(int, time_str.split(':'))
                
                # 找到下一个符合条件的日期
                next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                for _ in range(7):
                    if next_run.weekday() in days and next_run > from_time:
                        return next_run
                    next_run += timedelta(days=1)
                return next_run
            
            elif config.schedule_type == ScheduleType.MONTHLY:
                # 每月固定时间
                dates = schedule_config.get('schedule_dates', [1])  # 默认1号
                time_str = schedule_config.get('schedule_time', '10:00')
                hour, minute = map(int, time_str.split(':'))
                
                # 找到下一个符合条件的日期
                next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # 当月检查
                for date in sorted(dates):
                    try:
                        candidate = next_run.replace(day=date)
                        if candidate > from_time:
                            return candidate
                    except ValueError:
                        # 日期不存在（如2月30日）
                        continue
                
                # 下月检查
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)
                
                for date in sorted(dates):
                    try:
                        candidate = next_run.replace(day=date)
                        return candidate
                    except ValueError:
                        continue
                
                return None
            
            elif config.schedule_type == ScheduleType.INTERVAL:
                # 间隔执行
                interval = schedule_config.get('schedule_interval', 60)
                unit = schedule_config.get('schedule_interval_unit', 'minutes')
                
                # 转换为秒
                if unit == 'minutes':
                    seconds = interval * 60
                elif unit == 'hours':
                    seconds = interval * 3600
                elif unit == 'days':
                    seconds = interval * 86400
                else:
                    seconds = interval
                
                # 如果是第一次运行
                if config.last_run_time is None:
                    return from_time + timedelta(seconds=1)  # 立即执行
                
                # 基于上次运行时间计算
                return config.last_run_time + timedelta(seconds=seconds)
            
            elif config.schedule_type == ScheduleType.CRON:
                # Cron表达式
                cron_expr = schedule_config.get('schedule_cron', '0 10 * * *')
                
                # 使用croniter计算下次运行时间
                cron = croniter.croniter(cron_expr, from_time)
                return cron.get_next(datetime)
            
            elif config.schedule_type == ScheduleType.ONCE:
                # 一次性执行
                scheduled_time = schedule_config.get('scheduled_time')
                if scheduled_time:
                    if isinstance(scheduled_time, str):
                        return datetime.fromisoformat(scheduled_time)
                    return scheduled_time
                return None
            
        except Exception as e:
            logger.error(f"计算下次运行时间失败: {e}")
            return None
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("调度执行器已启动")
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("调度执行器已停止")
    
    async def _run_scheduler(self):
        """调度器主循环"""
        while self.running:
            try:
                await self._check_and_execute()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度器执行出错: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_execute(self):
        """检查并执行到期的任务"""
        current_time = datetime.now()
        
        for config_id, config in self.configs.items():
            if not config.is_active:
                continue
            
            if config.next_run_time and current_time >= config.next_run_time:
                # 执行任务
                logger.info(f"执行调度任务: {config_id}")
                asyncio.create_task(self._execute_task(config_id))
                
                # 更新运行时间
                config.last_run_time = current_time
                config.next_run_time = self._calculate_next_run(config, current_time)
                
                # 如果是一次性任务，执行后禁用
                if config.schedule_type == ScheduleType.ONCE:
                    config.is_active = False
                
                logger.info(f"调度任务 {config_id} 下次运行: {config.next_run_time}")
    
    async def _execute_task(self, config_id: str):
        """
        执行调度任务
        
        Args:
            config_id: 配置ID
        """
        try:
            logger.info(f"开始执行任务: {config_id}")
            
            # 这里应该调用实际的Pipeline执行逻辑
            # 例如：
            # - 获取配置详情
            # - 选择账号
            # - 创建Pipeline实例
            # - 执行Pipeline
            # - 发布内容
            
            # 模拟执行
            await asyncio.sleep(1)
            
            logger.info(f"任务执行完成: {config_id}")
            
        except Exception as e:
            logger.error(f"执行任务失败: {config_id} - {e}")
    
    def get_schedule_status(self) -> List[Dict[str, Any]]:
        """
        获取调度状态
        
        Returns:
            调度状态列表
        """
        status_list = []
        
        for config_id, config in self.configs.items():
            status = {
                'config_id': config_id,
                'schedule_type': config.schedule_type.value,
                'is_active': config.is_active,
                'last_run_time': config.last_run_time.isoformat() if config.last_run_time else None,
                'next_run_time': config.next_run_time.isoformat() if config.next_run_time else None,
                'schedule_config': config.schedule_config
            }
            status_list.append(status)
        
        return status_list
    
    def update_config(self, config_id: str, trigger_config: Dict[str, Any]) -> bool:
        """
        更新调度配置
        
        Args:
            config_id: 配置ID
            trigger_config: 新的触发器配置
        
        Returns:
            是否更新成功
        """
        if config_id not in self.configs:
            return self.add_config(config_id, trigger_config)
        
        try:
            config = self.configs[config_id]
            config.schedule_type = ScheduleType(trigger_config.get('schedule_type', 'daily'))
            config.schedule_config = trigger_config
            config.next_run_time = self._calculate_next_run(config)
            
            logger.info(f"更新调度配置: {config_id}, 下次运行: {config.next_run_time}")
            return True
            
        except Exception as e:
            logger.error(f"更新调度配置失败: {e}")
            return False
    
    def remove_config(self, config_id: str) -> bool:
        """
        移除调度配置
        
        Args:
            config_id: 配置ID
        
        Returns:
            是否移除成功
        """
        if config_id in self.configs:
            del self.configs[config_id]
            logger.info(f"移除调度配置: {config_id}")
            return True
        return False
    
    def pause_config(self, config_id: str) -> bool:
        """
        暂停调度配置
        
        Args:
            config_id: 配置ID
        
        Returns:
            是否暂停成功
        """
        if config_id in self.configs:
            self.configs[config_id].is_active = False
            logger.info(f"暂停调度配置: {config_id}")
            return True
        return False
    
    def resume_config(self, config_id: str) -> bool:
        """
        恢复调度配置
        
        Args:
            config_id: 配置ID
        
        Returns:
            是否恢复成功
        """
        if config_id in self.configs:
            config = self.configs[config_id]
            config.is_active = True
            # 重新计算下次运行时间
            config.next_run_time = self._calculate_next_run(config)
            logger.info(f"恢复调度配置: {config_id}, 下次运行: {config.next_run_time}")
            return True
        return False


# 全局实例
_schedule_executor = None


def get_schedule_executor() -> ScheduleExecutor:
    """获取调度执行器实例"""
    global _schedule_executor
    if _schedule_executor is None:
        _schedule_executor = ScheduleExecutor()
    return _schedule_executor


# 示例使用
if __name__ == "__main__":
    import asyncio
    
    async def test():
        executor = get_schedule_executor()
        
        # 添加每日定时任务
        executor.add_config("daily_task", {
            "schedule_type": "daily",
            "schedule_time": "10:30"
        })
        
        # 添加间隔任务（每2小时）
        executor.add_config("interval_task", {
            "schedule_type": "interval",
            "schedule_interval": 2,
            "schedule_interval_unit": "hours"
        })
        
        # 添加Cron任务（每天10点和14点）
        executor.add_config("cron_task", {
            "schedule_type": "cron",
            "schedule_cron": "0 10,14 * * *"
        })
        
        # 启动调度器
        await executor.start()
        
        # 查看状态
        status = executor.get_schedule_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        
        # 运行一段时间
        await asyncio.sleep(10)
        
        # 停止调度器
        await executor.stop()
    
    asyncio.run(test())