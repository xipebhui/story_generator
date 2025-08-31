#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动发布系统数据库模型
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class AccountGroupModel(Base):
    """账号组数据模型"""
    __tablename__ = 'account_groups'
    
    group_id = Column(String(50), primary_key=True)
    group_name = Column(String(100), nullable=False, unique=True)
    group_type = Column(String(20), nullable=False)  # 'experiment', 'production', 'test'
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column('metadata', JSON)  # 使用不同的属性名，但映射到同一个数据库列
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AccountGroupMemberModel(Base):
    """账号组成员数据模型"""
    __tablename__ = 'account_group_members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(50), nullable=False)
    account_id = Column(String(50), nullable=False)
    role = Column(String(20), default='member')  # 'control', 'experiment', 'member'
    join_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)


class PublishStrategyModel(Base):
    """发布策略数据模型"""
    __tablename__ = 'publish_strategies'
    
    strategy_id = Column(String(50), primary_key=True)
    strategy_name = Column(String(100), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    parameters = Column(JSON)
    description = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column('metadata', JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)