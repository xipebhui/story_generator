#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环形调度器模块
实现账号组的环形时间调度，确保发布时间均匀分布
"""

import logging
import random
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta, date, time
from dataclasses import dataclass
from enum import Enum

from database import get_db_manager
from sqlalchemy import Column, String, Integer, Date, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)
Base = declarative_base()


class SlotStatus(Enum):
    """调度槽状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TimeSlot:
    """时间槽"""
    slot_id: Optional[int]
    config_id: str
    account_id: str
    slot_date: date
    slot_time: time
    slot_index: int
    status: str = SlotStatus.PENDING.value
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def datetime(self) -> datetime:
        """获取完整时间"""
        return datetime.combine(self.slot_date, self.slot_time)
    
    def __lt__(self, other):
        """比较时间槽"""
        return self.datetime < other.datetime


class RingScheduleSlotModel(Base):
    """环形调度槽数据模型"""
    __tablename__ = 'ring_schedule_slots'
    
    slot_id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(String(50), nullable=False)
    account_id = Column(String(50), nullable=False)
    slot_date = Column(Date, nullable=False)
    slot_hour = Column(Integer, nullable=False)
    slot_minute = Column(Integer, nullable=False)
    slot_index = Column(Integer, nullable=False)
    status = Column(String(20), default=SlotStatus.PENDING.value)
    task_id = Column(String(50))
    extra_metadata = Column('metadata', JSON)  # 使用不同的属性名，但映射到同一个数据库列
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RingScheduler:
    """环形调度器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.default_start_hour = 6  # 默认开始时间 6:00
        self.default_end_hour = 24   # 默认结束时间 24:00 (次日0:00)
        self.min_interval_minutes = 30  # 最小间隔30分钟
        self.jitter_minutes = 5  # 随机抖动±5分钟
    
    def generate_slots(
        self,
        config_id: str,
        accounts: List[str],
        target_date: date,
        start_hour: int = None,
        end_hour: int = None,
        strategy: str = "even"
    ) -> List[TimeSlot]:
        """
        生成调度槽位
        
        Args:
            config_id: 配置ID
            accounts: 账号列表
            target_date: 目标日期
            start_hour: 开始时间(小时)
            end_hour: 结束时间(小时)
            strategy: 分配策略 (even: 均匀分布, random: 随机分布)
        
        Returns:
            时间槽列表
        """
        if not accounts:
            logger.warning("账号列表为空")
            return []
        
        start_hour = start_hour or self.default_start_hour
        end_hour = end_hour or self.default_end_hour
        
        # 处理跨天情况
        if end_hour <= start_hour:
            end_hour = 24  # 限制在当天内
        
        # 计算可用时间窗口
        total_minutes = (end_hour - start_hour) * 60
        account_count = len(accounts)
        
        # 计算间隔
        if account_count == 1:
            interval_minutes = 0
        else:
            interval_minutes = max(
                total_minutes // account_count,
                self.min_interval_minutes
            )
        
        slots = []
        
        if strategy == "even":
            # 均匀分布
            current_minute = 0
            for i, account_id in enumerate(accounts):
                # 计算时间
                hour = start_hour + (current_minute // 60)
                minute = current_minute % 60
                
                # 添加抖动
                jitter = random.randint(-self.jitter_minutes, self.jitter_minutes)
                minute += jitter
                
                # 处理分钟溢出
                if minute < 0:
                    minute += 60
                    hour -= 1
                elif minute >= 60:
                    minute -= 60
                    hour += 1
                
                # 确保在时间范围内
                if hour < start_hour:
                    hour = start_hour
                    minute = 0
                elif hour >= end_hour:
                    hour = end_hour - 1
                    minute = 59
                
                slot = TimeSlot(
                    slot_id=None,
                    config_id=config_id,
                    account_id=account_id,
                    slot_date=target_date,
                    slot_time=time(hour, minute),
                    slot_index=i,
                    status=SlotStatus.PENDING.value
                )
                slots.append(slot)
                
                current_minute += interval_minutes
        
        elif strategy == "random":
            # 随机分布
            available_minutes = list(range(0, total_minutes, self.min_interval_minutes))
            random.shuffle(available_minutes)
            
            for i, account_id in enumerate(accounts):
                if i < len(available_minutes):
                    minute_offset = available_minutes[i]
                else:
                    # 如果账号数超过可用时间槽，使用均匀分布
                    minute_offset = (total_minutes * i) // account_count
                
                hour = start_hour + (minute_offset // 60)
                minute = minute_offset % 60
                
                slot = TimeSlot(
                    slot_id=None,
                    config_id=config_id,
                    account_id=account_id,
                    slot_date=target_date,
                    slot_time=time(hour, minute),
                    slot_index=i,
                    status=SlotStatus.PENDING.value
                )
                slots.append(slot)
        
        # 排序
        slots.sort()
        
        logger.info(f"生成了 {len(slots)} 个调度槽位")
        return slots
    
    def save_slots(self, slots: List[TimeSlot]) -> bool:
        """
        保存调度槽位到数据库
        
        Args:
            slots: 时间槽列表
        
        Returns:
            是否保存成功
        """
        try:
            with self.db.get_session() as session:
                for slot in slots:
                    # 检查是否已存在
                    existing = session.query(RingScheduleSlotModel).filter_by(
                        config_id=slot.config_id,
                        account_id=slot.account_id,
                        slot_date=slot.slot_date,
                        slot_hour=slot.slot_time.hour,
                        slot_minute=slot.slot_time.minute
                    ).first()
                    
                    if existing:
                        # 更新现有槽位
                        existing.slot_index = slot.slot_index
                        existing.status = slot.status
                        existing.extra_metadata = slot.metadata
                        existing.updated_at = datetime.now()
                    else:
                        # 创建新槽位
                        new_slot = RingScheduleSlotModel(
                            config_id=slot.config_id,
                            account_id=slot.account_id,
                            slot_date=slot.slot_date,
                            slot_hour=slot.slot_time.hour,
                            slot_minute=slot.slot_time.minute,
                            slot_index=slot.slot_index,
                            status=slot.status,
                            extra_metadata=slot.metadata
                        )
                        session.add(new_slot)
                
                session.commit()
                logger.info(f"保存了 {len(slots)} 个调度槽位")
                return True
                
        except Exception as e:
            logger.error(f"保存调度槽位失败: {e}")
            return False
    
    def get_next_slot(
        self,
        config_id: str,
        from_time: datetime = None
    ) -> Optional[TimeSlot]:
        """
        获取下一个待执行的槽位
        
        Args:
            config_id: 配置ID
            from_time: 起始时间(默认当前时间)
        
        Returns:
            下一个时间槽
        """
        from_time = from_time or datetime.now()
        
        try:
            with self.db.get_session() as session:
                query = session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.config_id == config_id,
                    RingScheduleSlotModel.status == SlotStatus.PENDING.value
                )
                
                # 时间筛选
                query = query.filter(
                    (RingScheduleSlotModel.slot_date > from_time.date()) |
                    ((RingScheduleSlotModel.slot_date == from_time.date()) &
                     ((RingScheduleSlotModel.slot_hour > from_time.hour) |
                      ((RingScheduleSlotModel.slot_hour == from_time.hour) &
                       (RingScheduleSlotModel.slot_minute >= from_time.minute))))
                )
                
                # 按时间排序
                slot_model = query.order_by(
                    RingScheduleSlotModel.slot_date,
                    RingScheduleSlotModel.slot_hour,
                    RingScheduleSlotModel.slot_minute
                ).first()
                
                if slot_model:
                    return TimeSlot(
                        slot_id=slot_model.slot_id,
                        config_id=slot_model.config_id,
                        account_id=slot_model.account_id,
                        slot_date=slot_model.slot_date,
                        slot_time=time(slot_model.slot_hour, slot_model.slot_minute),
                        slot_index=slot_model.slot_index,
                        status=slot_model.status,
                        task_id=slot_model.task_id,
                        metadata=slot_model.metadata
                    )
                
        except Exception as e:
            logger.error(f"获取下一个槽位失败: {e}")
        
        return None
    
    def get_slots_by_date(
        self,
        config_id: str,
        target_date: date,
        status: Optional[str] = None
    ) -> List[TimeSlot]:
        """
        获取指定日期的槽位
        
        Args:
            config_id: 配置ID
            target_date: 目标日期
            status: 状态筛选
        
        Returns:
            时间槽列表
        """
        try:
            with self.db.get_session() as session:
                query = session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.config_id == config_id,
                    RingScheduleSlotModel.slot_date == target_date
                )
                
                if status:
                    query = query.filter(RingScheduleSlotModel.status == status)
                
                slot_models = query.order_by(
                    RingScheduleSlotModel.slot_hour,
                    RingScheduleSlotModel.slot_minute
                ).all()
                
                slots = []
                for model in slot_models:
                    slots.append(TimeSlot(
                        slot_id=model.slot_id,
                        config_id=model.config_id,
                        account_id=model.account_id,
                        slot_date=model.slot_date,
                        slot_time=time(model.slot_hour, model.slot_minute),
                        slot_index=model.slot_index,
                        status=model.status,
                        task_id=model.task_id,
                        metadata=model.metadata
                    ))
                
                return slots
                
        except Exception as e:
            logger.error(f"获取日期槽位失败: {e}")
            return []
    
    def update_slot_status(
        self,
        slot_id: int,
        status: str,
        task_id: Optional[str] = None
    ) -> bool:
        """
        更新槽位状态
        
        Args:
            slot_id: 槽位ID
            status: 新状态
            task_id: 任务ID
        
        Returns:
            是否更新成功
        """
        try:
            with self.db.get_session() as session:
                slot = session.query(RingScheduleSlotModel).filter_by(
                    slot_id=slot_id
                ).first()
                
                if not slot:
                    logger.error(f"槽位不存在: {slot_id}")
                    return False
                
                slot.status = status
                if task_id:
                    slot.task_id = task_id
                slot.updated_at = datetime.now()
                
                session.commit()
                logger.info(f"更新槽位状态: {slot_id} -> {status}")
                return True
                
        except Exception as e:
            logger.error(f"更新槽位状态失败: {e}")
            return False
    
    def allocate_account(
        self,
        config_id: str,
        target_time: datetime
    ) -> Optional[str]:
        """
        分配账号(根据时间找最近的槽位)
        
        Args:
            config_id: 配置ID
            target_time: 目标时间
        
        Returns:
            分配的账号ID
        """
        try:
            with self.db.get_session() as session:
                # 查找最近的未使用槽位
                query = session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.config_id == config_id,
                    RingScheduleSlotModel.status == SlotStatus.PENDING.value,
                    RingScheduleSlotModel.slot_date == target_time.date()
                )
                
                # 找最接近的时间
                slots = query.all()
                if not slots:
                    return None
                
                # 计算时间差
                target_minutes = target_time.hour * 60 + target_time.minute
                best_slot = None
                min_diff = float('inf')
                
                for slot in slots:
                    slot_minutes = slot.slot_hour * 60 + slot.slot_minute
                    diff = abs(slot_minutes - target_minutes)
                    if diff < min_diff:
                        min_diff = diff
                        best_slot = slot
                
                if best_slot:
                    return best_slot.account_id
                
        except Exception as e:
            logger.error(f"分配账号失败: {e}")
        
        return None
    
    def rebalance_slots(
        self,
        config_id: str,
        target_date: date,
        accounts: List[str]
    ) -> bool:
        """
        重新平衡槽位分配
        
        Args:
            config_id: 配置ID
            target_date: 目标日期
            accounts: 新的账号列表
        
        Returns:
            是否重新平衡成功
        """
        try:
            # 删除旧槽位
            with self.db.get_session() as session:
                session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.config_id == config_id,
                    RingScheduleSlotModel.slot_date == target_date,
                    RingScheduleSlotModel.status == SlotStatus.PENDING.value
                ).delete()
                session.commit()
            
            # 生成新槽位
            new_slots = self.generate_slots(
                config_id=config_id,
                accounts=accounts,
                target_date=target_date
            )
            
            # 保存新槽位
            return self.save_slots(new_slots)
            
        except Exception as e:
            logger.error(f"重新平衡槽位失败: {e}")
            return False
    
    def get_account_schedule(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[TimeSlot]:
        """
        获取账号的调度安排
        
        Args:
            account_id: 账号ID
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            时间槽列表
        """
        try:
            with self.db.get_session() as session:
                slot_models = session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.account_id == account_id,
                    RingScheduleSlotModel.slot_date >= start_date,
                    RingScheduleSlotModel.slot_date <= end_date
                ).order_by(
                    RingScheduleSlotModel.slot_date,
                    RingScheduleSlotModel.slot_hour,
                    RingScheduleSlotModel.slot_minute
                ).all()
                
                slots = []
                for model in slot_models:
                    slots.append(TimeSlot(
                        slot_id=model.slot_id,
                        config_id=model.config_id,
                        account_id=model.account_id,
                        slot_date=model.slot_date,
                        slot_time=time(model.slot_hour, model.slot_minute),
                        slot_index=model.slot_index,
                        status=model.status,
                        task_id=model.task_id,
                        metadata=model.metadata
                    ))
                
                return slots
                
        except Exception as e:
            logger.error(f"获取账号调度失败: {e}")
            return []
    
    def cleanup_old_slots(self, days_to_keep: int = 30) -> int:
        """
        清理旧的调度槽位
        
        Args:
            days_to_keep: 保留天数
        
        Returns:
            清理的槽位数
        """
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            
            with self.db.get_session() as session:
                deleted = session.query(RingScheduleSlotModel).filter(
                    RingScheduleSlotModel.slot_date < cutoff_date,
                    RingScheduleSlotModel.status.in_([
                        SlotStatus.COMPLETED.value,
                        SlotStatus.FAILED.value,
                        SlotStatus.SKIPPED.value
                    ])
                ).delete()
                
                session.commit()
                logger.info(f"清理了 {deleted} 个旧槽位")
                return deleted
                
        except Exception as e:
            logger.error(f"清理旧槽位失败: {e}")
            return 0


# 全局实例
_ring_scheduler = None


def get_ring_scheduler() -> RingScheduler:
    """获取环形调度器实例"""
    global _ring_scheduler
    if _ring_scheduler is None:
        _ring_scheduler = RingScheduler()
    return _ring_scheduler