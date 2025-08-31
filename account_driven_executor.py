#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号驱动执行器模块
实现账号驱动的Pipeline执行和发布流程
"""

import logging
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from database import get_db_manager
from pipeline_registry import get_pipeline_registry
from ring_scheduler import get_ring_scheduler, TimeSlot
from account_service import get_account_service
from publish_service import PublishService

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStatus(Enum):
    """Pipeline执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PublishStatus(Enum):
    """发布状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class ExecutionTask:
    """执行任务"""
    task_id: str
    config_id: str
    group_id: str
    account_id: str
    pipeline_id: str
    slot_id: Optional[int] = None
    strategy_id: Optional[str] = None
    variant_name: Optional[str] = None
    pipeline_config: Optional[Dict[str, Any]] = None
    pipeline_status: str = PipelineStatus.PENDING.value
    pipeline_result: Optional[Dict[str, Any]] = None
    publish_status: str = PublishStatus.PENDING.value
    publish_result: Optional[Dict[str, Any]] = None
    platform: str = "youtube"
    priority: int = 50
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AccountDrivenExecutor:
    """账号驱动执行器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.pipeline_registry = get_pipeline_registry()
        self.ring_scheduler = get_ring_scheduler()
        self.account_service = get_account_service()
        self.publish_service = PublishService()
        
        # 执行配置
        self.max_concurrent_pipelines = 3
        self.max_concurrent_publishes = 5
        self.max_retry_count = 2
        self.retry_delay_minutes = 30
        
        # 执行器
        self.pipeline_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_pipelines)
        self.publish_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_publishes)
        
        # 运行状态
        self._running = False
        self._tasks = {}  # task_id -> ExecutionTask
    
    async def start(self):
        """启动执行器"""
        if self._running:
            logger.warning("执行器已在运行")
            return
        
        self._running = True
        logger.info("账号驱动执行器启动")
        
        # 启动主循环
        await self._main_loop()
    
    async def stop(self):
        """停止执行器"""
        self._running = False
        logger.info("账号驱动执行器停止")
        
        # 等待正在执行的任务
        self.pipeline_executor.shutdown(wait=True)
        self.publish_executor.shutdown(wait=True)
    
    async def _main_loop(self):
        """主执行循环"""
        while self._running:
            try:
                # 1. 检查待执行的调度槽位
                await self._check_scheduled_slots()
                
                # 2. 执行Pipeline任务
                await self._execute_pipeline_tasks()
                
                # 3. 执行发布任务
                await self._execute_publish_tasks()
                
                # 4. 检查失败重试
                await self._check_retry_tasks()
                
                # 5. 清理完成的任务
                self._cleanup_completed_tasks()
                
                # 休眠
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                await asyncio.sleep(10)
    
    async def _check_scheduled_slots(self):
        """检查待执行的调度槽位"""
        try:
            configs = self._get_active_configs()
            
            for config in configs:
                # 获取下一个槽位
                next_slot = self.ring_scheduler.get_next_slot(config['config_id'])
                
                if next_slot and self._should_execute_slot(next_slot):
                    # 创建执行任务
                    task = await self._create_task_from_slot(config, next_slot)
                    if task:
                        self._tasks[task.task_id] = task
                        logger.info(f"创建任务: {task.task_id} for slot {next_slot.slot_id}")
                        
                        # 更新槽位状态
                        self.ring_scheduler.update_slot_status(
                            next_slot.slot_id,
                            "scheduled",
                            task.task_id
                        )
                        
        except Exception as e:
            logger.error(f"检查调度槽位失败: {e}")
    
    async def _execute_pipeline_tasks(self):
        """执行Pipeline任务"""
        pending_tasks = [
            task for task in self._tasks.values()
            if task.pipeline_status == PipelineStatus.PENDING.value
        ]
        
        # 按优先级排序
        pending_tasks.sort(key=lambda t: (-t.priority, t.created_at or datetime.now()))
        
        # 限制并发数
        running_count = sum(
            1 for task in self._tasks.values()
            if task.pipeline_status == PipelineStatus.RUNNING.value
        )
        
        for task in pending_tasks:
            if running_count >= self.max_concurrent_pipelines:
                break
            
            # 异步执行Pipeline
            asyncio.create_task(self._run_pipeline(task))
            running_count += 1
    
    async def _run_pipeline(self, task: ExecutionTask):
        """运行Pipeline"""
        try:
            logger.info(f"开始执行Pipeline: {task.task_id}")
            task.pipeline_status = PipelineStatus.RUNNING.value
            task.started_at = datetime.now()
            self._save_task(task)
            
            # 创建Pipeline实例
            pipeline = self.pipeline_registry.create_instance(
                task.pipeline_id,
                task.pipeline_config or {}
            )
            
            if not pipeline:
                raise Exception(f"无法创建Pipeline实例: {task.pipeline_id}")
            
            # 执行Pipeline
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.pipeline_executor,
                self._execute_pipeline_sync,
                pipeline,
                task.pipeline_config
            )
            
            # 更新任务状态
            task.pipeline_status = PipelineStatus.COMPLETED.value
            task.pipeline_result = result
            task.publish_status = PublishStatus.SCHEDULED.value
            logger.info(f"Pipeline执行成功: {task.task_id}")
            
        except Exception as e:
            logger.error(f"Pipeline执行失败: {task.task_id} - {e}")
            task.pipeline_status = PipelineStatus.FAILED.value
            task.error_message = str(e)
            task.retry_count += 1
            
            # 发送告警
            await self._send_alert(task, f"Pipeline执行失败: {e}")
        
        finally:
            self._save_task(task)
    
    def _execute_pipeline_sync(self, pipeline, config: Dict[str, Any]) -> Dict[str, Any]:
        """同步执行Pipeline"""
        try:
            # 调用Pipeline的execute方法
            if hasattr(pipeline, 'execute'):
                return pipeline.execute(config)
            elif hasattr(pipeline, 'run'):
                return pipeline.run(config)
            else:
                raise Exception("Pipeline没有execute或run方法")
        except Exception as e:
            logger.error(f"Pipeline执行异常: {e}")
            raise
    
    async def _execute_publish_tasks(self):
        """执行发布任务"""
        scheduled_tasks = [
            task for task in self._tasks.values()
            if task.pipeline_status == PipelineStatus.COMPLETED.value
            and task.publish_status == PublishStatus.SCHEDULED.value
        ]
        
        # 限制并发数
        publishing_count = sum(
            1 for task in self._tasks.values()
            if task.publish_status == "publishing"
        )
        
        for task in scheduled_tasks:
            if publishing_count >= self.max_concurrent_publishes:
                break
            
            # 异步发布
            asyncio.create_task(self._publish_content(task))
            publishing_count += 1
    
    async def _publish_content(self, task: ExecutionTask):
        """发布内容"""
        try:
            logger.info(f"开始发布: {task.task_id}")
            task.publish_status = "publishing"
            self._save_task(task)
            
            # 获取Pipeline结果
            if not task.pipeline_result:
                raise Exception("Pipeline结果为空")
            
            # 准备发布数据
            publish_data = self._prepare_publish_data(task)
            
            # 执行发布
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.publish_executor,
                self._publish_sync,
                task.account_id,
                publish_data
            )
            
            # 更新任务状态
            task.publish_status = PublishStatus.PUBLISHED.value
            task.publish_result = result
            task.completed_at = datetime.now()
            logger.info(f"发布成功: {task.task_id}")
            
            # 更新槽位状态
            if task.slot_id:
                self.ring_scheduler.update_slot_status(
                    task.slot_id,
                    "completed"
                )
            
        except Exception as e:
            logger.error(f"发布失败: {task.task_id} - {e}")
            task.publish_status = PublishStatus.FAILED.value
            task.error_message = str(e)
            task.retry_count += 1
            
            # 更新槽位状态
            if task.slot_id:
                self.ring_scheduler.update_slot_status(
                    task.slot_id,
                    "failed"
                )
            
            # 发送告警
            await self._send_alert(task, f"发布失败: {e}")
        
        finally:
            self._save_task(task)
    
    def _publish_sync(self, account_id: str, publish_data: Dict[str, Any]) -> Dict[str, Any]:
        """同步发布"""
        try:
            # 调用发布服务
            result = self.publish_service.publish_content(
                account_id=account_id,
                **publish_data
            )
            return result
        except Exception as e:
            logger.error(f"发布异常: {e}")
            raise
    
    async def _check_retry_tasks(self):
        """检查需要重试的任务"""
        retry_tasks = [
            task for task in self._tasks.values()
            if task.retry_count > 0 and task.retry_count <= self.max_retry_count
            and (task.pipeline_status == PipelineStatus.FAILED.value
                 or task.publish_status == PublishStatus.FAILED.value)
        ]
        
        for task in retry_tasks:
            # 检查重试时间
            if task.started_at:
                retry_time = task.started_at + timedelta(minutes=self.retry_delay_minutes)
                if datetime.now() >= retry_time:
                    logger.info(f"重试任务: {task.task_id} (第{task.retry_count}次)")
                    
                    # 重置状态
                    if task.pipeline_status == PipelineStatus.FAILED.value:
                        task.pipeline_status = PipelineStatus.PENDING.value
                    elif task.publish_status == PublishStatus.FAILED.value:
                        task.publish_status = PublishStatus.SCHEDULED.value
                    
                    task.error_message = None
                    self._save_task(task)
    
    def _cleanup_completed_tasks(self):
        """清理完成的任务"""
        # 保留最近24小时的任务
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            if task.completed_at and task.completed_at < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"清理了 {len(tasks_to_remove)} 个已完成任务")
    
    def _get_active_configs(self) -> List[Dict[str, Any]]:
        """获取活跃的发布配置"""
        try:
            with self.db.get_session() as session:
                # 这里简化处理，实际应该查询publish_configs表
                # 返回模拟数据用于测试
                return [
                    {
                        'config_id': 'test_config_1',
                        'group_id': 'default_group',
                        'pipeline_id': 'story_v3',
                        'trigger_type': 'scheduled',
                        'trigger_config': {'interval': 'daily'}
                    }
                ]
        except Exception as e:
            logger.error(f"获取活跃配置失败: {e}")
            return []
    
    def _should_execute_slot(self, slot: TimeSlot) -> bool:
        """判断是否应该执行槽位"""
        # 提前5分钟准备
        prepare_time = slot.datetime - timedelta(minutes=5)
        return datetime.now() >= prepare_time
    
    async def _create_task_from_slot(
        self,
        config: Dict[str, Any],
        slot: TimeSlot
    ) -> Optional[ExecutionTask]:
        """从槽位创建任务"""
        try:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            # 获取Pipeline配置
            pipeline_config = self._get_pipeline_config(config, slot.account_id)
            
            task = ExecutionTask(
                task_id=task_id,
                config_id=config['config_id'],
                group_id=config['group_id'],
                account_id=slot.account_id,
                pipeline_id=config['pipeline_id'],
                slot_id=slot.slot_id,
                pipeline_config=pipeline_config,
                created_at=datetime.now(),
                scheduled_at=slot.datetime
            )
            
            # 保存到数据库
            self._save_task(task)
            
            return task
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return None
    
    def _get_pipeline_config(
        self,
        config: Dict[str, Any],
        account_id: str
    ) -> Dict[str, Any]:
        """获取Pipeline配置"""
        # 基础配置
        pipeline_config = {
            'account_id': account_id,
            'config_id': config['config_id']
        }
        
        # 根据Pipeline类型添加特定配置
        if config['pipeline_id'] == 'story_v3':
            # 故事Pipeline配置
            pipeline_config.update({
                'video_id': 'test_video',  # 实际应该从配置或监控结果获取
                'duration': 120,
                'gender': 0
            })
        
        return pipeline_config
    
    def _prepare_publish_data(self, task: ExecutionTask) -> Dict[str, Any]:
        """准备发布数据"""
        pipeline_result = task.pipeline_result or {}
        
        publish_data = {
            'task_id': task.task_id,
            'platform': task.platform,
            'content_type': 'video',
            'scheduled_time': task.scheduled_at
        }
        
        # 从Pipeline结果提取发布信息
        if 'video_path' in pipeline_result:
            publish_data['video_path'] = pipeline_result['video_path']
        
        if 'title' in pipeline_result:
            publish_data['title'] = pipeline_result['title']
        
        if 'description' in pipeline_result:
            publish_data['description'] = pipeline_result['description']
        
        if 'tags' in pipeline_result:
            publish_data['tags'] = pipeline_result['tags']
        
        return publish_data
    
    def _save_task(self, task: ExecutionTask):
        """保存任务到数据库"""
        try:
            # 这里简化处理，实际应该保存到auto_publish_tasks表
            logger.debug(f"保存任务: {task.task_id}")
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    async def _send_alert(self, task: ExecutionTask, message: str):
        """发送告警"""
        try:
            alert_data = {
                'task_id': task.task_id,
                'account_id': task.account_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            # 这里可以集成告警服务（邮件、短信、webhook等）
            logger.error(f"告警: {json.dumps(alert_data, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"发送告警失败: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            return asdict(task)
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.pipeline_status in [PipelineStatus.PENDING.value, PipelineStatus.RUNNING.value]:
                task.pipeline_status = "cancelled"
                task.publish_status = "cancelled"
                self._save_task(task)
                logger.info(f"取消任务: {task_id}")
                return True
        return False


# 全局实例
_executor = None


def get_account_driven_executor() -> AccountDrivenExecutor:
    """获取账号驱动执行器实例"""
    global _executor
    if _executor is None:
        _executor = AccountDrivenExecutor()
    return _executor


# 启动执行器
async def start_executor():
    """启动执行器"""
    executor = get_account_driven_executor()
    await executor.start()


# 停止执行器
async def stop_executor():
    """停止执行器"""
    executor = get_account_driven_executor()
    await executor.stop()