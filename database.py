#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块
支持SQLite和MySQL，便于后期迁移
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# ============ 数据模型定义 ============

class User(Base):
    """用户表 - 用于API认证"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    status = Column(String(20), default='active', nullable=False)  # active/inactive/banned
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'api_key': self.api_key,
            'is_active': self.is_active,
            'status': self.status,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PipelineTask(Base):
    """Pipeline任务表（原task_history，包含所有任务）"""
    __tablename__ = 'pipeline_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # 请求参数
    video_id = Column(String(50), nullable=False, index=True)
    creator_id = Column(String(50), nullable=False, index=True)
    account_name = Column(String(100), nullable=True)  # 发布账号名称
    gender = Column(Integer, default=1)  # 0男1女
    image_duration = Column(Integer, default=60)  # 每张图片持续时间(秒)
    image_dir = Column(String(500), nullable=True)
    export_video = Column(Boolean, default=False)
    enable_subtitle = Column(Boolean, default=True)
    
    # 执行状态
    status = Column(String(20), nullable=False, index=True)  # pending/running/completed/failed
    current_stage = Column(String(50), nullable=True)
    progress = Column(Text, nullable=True)  # JSON格式的进度详情
    
    # 时间记录
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    total_duration = Column(Float, nullable=True)  # 总耗时(秒)
    
    # 生成结果
    youtube_metadata = Column(Text, nullable=True)  # JSON格式(标题、描述、标签等)
    video_path = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)
    draft_path = Column(String(500), nullable=True)
    audio_path = Column(String(500), nullable=True)
    story_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    
    # 错误信息
    error = Column(Text, nullable=True)
    
    # 关系
    publish_tasks = relationship("PublishTask", back_populates="pipeline_task")
    
    # 索引优化查询
    __table_args__ = (
        Index('idx_creator_created', 'creator_id', 'created_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'video_id': self.video_id,
            'creator_id': self.creator_id,
            'account_name': self.account_name,
            'gender': self.gender,
            'image_duration': self.image_duration,
            'image_dir': self.image_dir,
            'export_video': self.export_video,
            'enable_subtitle': self.enable_subtitle,
            'status': self.status,
            'current_stage': self.current_stage,
            'progress': json.loads(self.progress) if self.progress else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration': self.total_duration,
            'youtube_metadata': json.loads(self.youtube_metadata) if self.youtube_metadata else None,
            'video_path': self.video_path,
            'preview_url': self.preview_url,
            'draft_path': self.draft_path,
            'audio_path': self.audio_path,
            'story_path': self.story_path,
            'thumbnail_path': self.thumbnail_path,
            'error': self.error
        }


class Account(Base):
    """YouTube账号表"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(50), unique=True, nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    profile_id = Column(String(100), nullable=False)  # BitBrowser Profile ID
    channel_url = Column(String(200), nullable=True)
    window_number = Column(String(50), nullable=True)  # 窗口序号
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # 关系
    publish_tasks = relationship("PublishTask", back_populates="account")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'profile_id': self.profile_id,
            'channel_url': self.channel_url,
            'window_number': self.window_number,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PublishTask(Base):
    """发布任务表"""
    __tablename__ = 'publish_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    publish_id = Column(String(100), unique=True, nullable=False, index=True)
    task_id = Column(String(100), ForeignKey('pipeline_tasks.task_id'), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey('accounts.account_id'), nullable=False, index=True)
    
    # 发布内容
    video_path = Column(String(500), nullable=False)
    video_title = Column(String(200), nullable=False)
    video_description = Column(Text, nullable=True)
    video_tags = Column(Text, nullable=True)  # JSON数组
    thumbnail_path = Column(String(500), nullable=True)
    
    # 发布配置
    scheduled_time = Column(DateTime, nullable=True)
    is_scheduled = Column(Boolean, default=False, index=True)
    privacy_status = Column(String(20), default='public')  # public/private/unlisted
    
    # 发布状态
    status = Column(String(20), nullable=False, default='pending', index=True)  # pending/uploading/success/failed
    upload_started_at = Column(DateTime, nullable=True)
    upload_completed_at = Column(DateTime, nullable=True)
    
    # YouTube响应
    youtube_video_id = Column(String(50), nullable=True)
    youtube_video_url = Column(String(200), nullable=True)
    upload_response = Column(Text, nullable=True)  # 完整的上传响应(JSON)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # 关系
    pipeline_task = relationship("PipelineTask", back_populates="publish_tasks")
    account = relationship("Account", back_populates="publish_tasks")
    
    # 索引
    __table_args__ = (
        Index('idx_task_account', 'task_id', 'account_id'),
        Index('idx_account_status', 'account_id', 'status'),
        Index('idx_scheduled', 'is_scheduled', 'scheduled_time'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'publish_id': self.publish_id,
            'task_id': self.task_id,
            'account_id': self.account_id,
            'video_path': self.video_path,
            'video_title': self.video_title,
            'video_description': self.video_description,
            'video_tags': json.loads(self.video_tags) if self.video_tags else [],
            'thumbnail_path': self.thumbnail_path,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'is_scheduled': self.is_scheduled,
            'privacy_status': self.privacy_status,
            'status': self.status,
            'upload_started_at': self.upload_started_at.isoformat() if self.upload_started_at else None,
            'upload_completed_at': self.upload_completed_at.isoformat() if self.upload_completed_at else None,
            'youtube_video_id': self.youtube_video_id,
            'youtube_video_url': self.youtube_video_url,
            'upload_response': json.loads(self.upload_response) if self.upload_response else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ============ 数据库管理器 ============

class DatabaseManager:
    """数据库管理器 - 支持SQLite和MySQL"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库管理器
        
        Args:
            db_url: 数据库连接URL
                   - SQLite: sqlite:///path/to/database.db
                   - MySQL: mysql+pymysql://user:password@host:port/database
        """
        if not db_url:
            # 默认使用SQLite
            db_path = os.environ.get('DB_PATH', './data/pipeline_tasks.db')
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
            db_url = f'sqlite:///{db_path}'
        
        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            echo=False,  # 生产环境设为False
            pool_pre_ping=True,  # 连接池健康检查
            connect_args={'check_same_thread': False} if 'sqlite' in db_url else {}
        )
        
        # 创建表
        Base.metadata.create_all(self.engine)
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"数据库初始化成功: {db_url}")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    # ============ Pipeline任务管理 ============
    
    def create_task(self, task_data: Dict[str, Any]) -> PipelineTask:
        """创建任务记录"""
        with self.get_session() as session:
            # 处理duration字段名称差异
            if 'duration' in task_data:
                task_data['image_duration'] = task_data.pop('duration')
            
            task = PipelineTask(
                task_id=task_data['task_id'],
                video_id=task_data['video_id'],
                creator_id=task_data['creator_id'],
                gender=task_data.get('gender', 1),
                image_duration=task_data.get('image_duration', 60),
                image_dir=task_data.get('image_dir'),
                export_video=task_data.get('export_video', False),
                enable_subtitle=task_data.get('enable_subtitle', True),
                status='pending',
                progress=json.dumps(task_data.get('progress', {}))
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
    
    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Optional[PipelineTask]:
        """更新任务记录"""
        with self.get_session() as session:
            task = session.query(PipelineTask).filter_by(task_id=task_id).first()
            if not task:
                return None
            
            # 更新字段
            for key, value in update_data.items():
                if key == 'progress' and isinstance(value, dict):
                    value = json.dumps(value)
                elif key == 'youtube_metadata' and isinstance(value, dict):
                    value = json.dumps(value)
                
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # 计算总耗时
            if task.completed_at and task.created_at:
                task.total_duration = (task.completed_at - task.created_at).total_seconds()
            
            session.commit()
            session.refresh(task)
            return task
    
    def get_task(self, task_id: str) -> Optional[PipelineTask]:
        """获取单个任务"""
        with self.get_session() as session:
            return session.query(PipelineTask).filter_by(task_id=task_id).first()
    
    def get_tasks_history(
        self,
        creator_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PipelineTask]:
        """查询任务历史"""
        with self.get_session() as session:
            query = session.query(PipelineTask)
            
            if creator_id:
                query = query.filter(PipelineTask.creator_id == creator_id)
            if status:
                query = query.filter(PipelineTask.status == status)
            if start_date:
                query = query.filter(PipelineTask.created_at >= start_date)
            if end_date:
                query = query.filter(PipelineTask.created_at <= end_date)
            
            # 按创建时间倒序
            query = query.order_by(PipelineTask.created_at.desc())
            
            # 分页
            query = query.limit(limit).offset(offset)
            
            return query.all()
    
    # ============ 账号管理 ============
    
    def create_account(self, account_data: Dict[str, Any]) -> Account:
        """创建账号"""
        with self.get_session() as session:
            account = Account(**account_data)
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账号"""
        with self.get_session() as session:
            return session.query(Account).filter_by(account_id=account_id).first()
    
    def get_active_accounts(self) -> List[Account]:
        """获取所有活跃账号"""
        with self.get_session() as session:
            return session.query(Account).filter_by(is_active=True).all()
    
    def update_account(self, account_id: str, update_data: Dict[str, Any]) -> Optional[Account]:
        """更新账号信息"""
        with self.get_session() as session:
            account = session.query(Account).filter_by(account_id=account_id).first()
            if not account:
                return None
            
            for key, value in update_data.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            
            session.commit()
            session.refresh(account)
            return account
    
    # ============ 发布任务管理 ============
    
    def create_publish_task(self, publish_data: Dict[str, Any]) -> PublishTask:
        """创建发布任务"""
        with self.get_session() as session:
            # 处理JSON字段
            if 'video_tags' in publish_data and isinstance(publish_data['video_tags'], list):
                publish_data['video_tags'] = json.dumps(publish_data['video_tags'])
            
            publish = PublishTask(**publish_data)
            session.add(publish)
            session.commit()
            session.refresh(publish)
            return publish
    
    def update_publish_task(self, publish_id: str, update_data: Dict[str, Any]) -> Optional[PublishTask]:
        """更新发布任务"""
        with self.get_session() as session:
            publish = session.query(PublishTask).filter_by(publish_id=publish_id).first()
            if not publish:
                return None
            
            for key, value in update_data.items():
                if key == 'video_tags' and isinstance(value, list):
                    value = json.dumps(value)
                elif key == 'upload_response' and isinstance(value, dict):
                    value = json.dumps(value)
                
                if hasattr(publish, key):
                    setattr(publish, key, value)
            
            session.commit()
            session.refresh(publish)
            return publish
    
    def get_publish_tasks_by_task(self, task_id: str) -> List[PublishTask]:
        """获取某个任务的所有发布记录"""
        with self.get_session() as session:
            return session.query(PublishTask).filter_by(task_id=task_id).all()
    
    def get_pending_publish_tasks(self, limit: int = 10) -> List[PublishTask]:
        """获取待发布任务"""
        with self.get_session() as session:
            return session.query(PublishTask)\
                .filter_by(status='pending')\
                .limit(limit)\
                .all()
    
    # ============ 用户管理 ============
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        with self.get_session() as session:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with self.get_session() as session:
            return session.query(User).filter_by(username=username).first()
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """根据API Key获取用户"""
        with self.get_session() as session:
            return session.query(User).filter_by(api_key=api_key, is_active=True).first()
    
    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """更新用户信息"""
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            session.commit()
            session.refresh(user)
            return user
    
    # ============ 统计功能 ============
    
    def get_statistics(self, creator_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        with self.get_session() as session:
            # Pipeline任务统计
            task_query = session.query(PipelineTask)
            if creator_id:
                task_query = task_query.filter(PipelineTask.creator_id == creator_id)
            
            total_tasks = task_query.count()
            completed_tasks = task_query.filter(PipelineTask.status == 'completed').count()
            failed_tasks = task_query.filter(PipelineTask.status == 'failed').count()
            running_tasks = task_query.filter(PipelineTask.status == 'running').count()
            
            # 发布任务统计
            publish_total = session.query(PublishTask).count()
            publish_success = session.query(PublishTask).filter(PublishTask.status == 'success').count()
            publish_failed = session.query(PublishTask).filter(PublishTask.status == 'failed').count()
            
            # 平均耗时
            avg_duration = session.query(func.avg(PipelineTask.total_duration))\
                .filter(PipelineTask.status == 'completed')
            if creator_id:
                avg_duration = avg_duration.filter(PipelineTask.creator_id == creator_id)
            avg_duration = avg_duration.scalar() or 0
            
            return {
                'pipeline': {
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'failed': failed_tasks,
                    'running': running_tasks,
                    'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                },
                'publish': {
                    'total': publish_total,
                    'success': publish_success,
                    'failed': publish_failed,
                    'success_rate': (publish_success / publish_total * 100) if publish_total > 0 else 0
                },
                'avg_duration_seconds': round(avg_duration, 2)
            }


# ============ 全局实例管理 ============

db_manager: Optional[DatabaseManager] = None

def init_database(db_url: Optional[str] = None):
    """初始化数据库"""
    global db_manager
    db_manager = DatabaseManager(db_url)
    return db_manager

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global db_manager
    if not db_manager:
        db_manager = init_database()
    return db_manager