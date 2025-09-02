#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline注册表模块
管理所有Pipeline的注册、发现和实例化
"""

import logging
import importlib
import json
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from database import get_db_manager
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)
Base = declarative_base()


class PipelineStatus(Enum):
    """Pipeline状态枚举"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    DISABLED = "disabled"


@dataclass
class PipelineMetadata:
    """Pipeline元数据"""
    pipeline_id: str
    pipeline_name: str
    pipeline_type: str
    pipeline_class: str
    config_schema: Dict[str, Any]
    supported_platforms: List[str]
    version: str = "1.0.0"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PipelineRegistryModel(Base):
    """Pipeline注册表数据模型"""
    __tablename__ = 'pipeline_registry'
    
    pipeline_id = Column(String(50), primary_key=True)
    pipeline_name = Column(String(100), nullable=False)
    pipeline_type = Column(String(50), nullable=False)
    pipeline_class = Column(String(200), nullable=False)
    config_schema = Column(JSON)
    supported_platforms = Column(JSON, default=["youtube"])
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="active")
    extra_metadata = Column('metadata', JSON)  # 使用不同的属性名，但映射到同一个数据库列
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PipelineRegistry:
    """Pipeline注册表管理器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self._cache: Dict[str, PipelineMetadata] = {}
        self._class_cache: Dict[str, Type] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """加载Pipeline缓存"""
        try:
            with self.db.get_session() as session:
                pipelines = session.query(PipelineRegistryModel).filter_by(
                    status=PipelineStatus.ACTIVE.value
                ).all()
                
                for p in pipelines:
                    metadata = PipelineMetadata(
                        pipeline_id=p.pipeline_id,
                        pipeline_name=p.pipeline_name,
                        pipeline_type=p.pipeline_type,
                        pipeline_class=p.pipeline_class,
                        config_schema=p.config_schema or {},
                        supported_platforms=p.supported_platforms or ["youtube"],
                        version=p.version,
                        status=p.status,
                        metadata=p.extra_metadata,  # 使用 extra_metadata
                        created_at=p.created_at,
                        updated_at=p.updated_at
                    )
                    self._cache[p.pipeline_id] = metadata
                    
            logger.info(f"加载了 {len(self._cache)} 个活跃Pipeline")
        except Exception as e:
            logger.error(f"加载Pipeline缓存失败: {e}")
    
    def register_pipeline(
        self,
        pipeline_id: str,
        pipeline_name: str,
        pipeline_type: str,
        pipeline_class: str,
        config_schema: Dict[str, Any],
        supported_platforms: List[str] = None,
        version: str = "1.0.0",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        注册新Pipeline
        
        Args:
            pipeline_id: Pipeline唯一标识
            pipeline_name: Pipeline名称
            pipeline_type: Pipeline类型
            pipeline_class: Pipeline类路径
            config_schema: 配置模式
            supported_platforms: 支持的平台列表
            version: 版本号
            metadata: 额外元数据
        
        Returns:
            是否注册成功
        """
        try:
            with self.db.get_session() as session:
                # 检查是否已存在
                existing = session.query(PipelineRegistryModel).filter_by(
                    pipeline_id=pipeline_id
                ).first()
                
                if existing:
                    logger.warning(f"Pipeline {pipeline_id} 已存在")
                    return False
                
                # 验证类是否可以加载
                if not self._validate_pipeline_class(pipeline_class):
                    logger.error(f"无法加载Pipeline类: {pipeline_class}")
                    return False
                
                # 创建新记录
                pipeline = PipelineRegistryModel(
                    pipeline_id=pipeline_id,
                    pipeline_name=pipeline_name,
                    pipeline_type=pipeline_type,
                    pipeline_class=pipeline_class,
                    config_schema=config_schema,
                    supported_platforms=supported_platforms or ["youtube"],
                    version=version,
                    status=PipelineStatus.ACTIVE.value,
                    extra_metadata=metadata  # 使用 extra_metadata
                )
                
                session.add(pipeline)
                session.commit()
                
                # 更新缓存
                self._cache[pipeline_id] = PipelineMetadata(
                    pipeline_id=pipeline_id,
                    pipeline_name=pipeline_name,
                    pipeline_type=pipeline_type,
                    pipeline_class=pipeline_class,
                    config_schema=config_schema,
                    supported_platforms=supported_platforms or ["youtube"],
                    version=version,
                    status=PipelineStatus.ACTIVE.value,
                    metadata=metadata
                )
                
                logger.info(f"成功注册Pipeline: {pipeline_id}")
                return True
                
        except Exception as e:
            logger.error(f"注册Pipeline失败: {e}")
            return False
    
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineMetadata]:
        """
        获取Pipeline元数据
        
        Args:
            pipeline_id: Pipeline ID
        
        Returns:
            Pipeline元数据
        """
        # 先查缓存
        if pipeline_id in self._cache:
            return self._cache[pipeline_id]
        
        # 查询数据库
        try:
            with self.db.get_session() as session:
                pipeline = session.query(PipelineRegistryModel).filter_by(
                    pipeline_id=pipeline_id
                ).first()
                
                if pipeline:
                    metadata = PipelineMetadata(
                        pipeline_id=pipeline.pipeline_id,
                        pipeline_name=pipeline.pipeline_name,
                        pipeline_type=pipeline.pipeline_type,
                        pipeline_class=pipeline.pipeline_class,
                        config_schema=pipeline.config_schema or {},
                        supported_platforms=pipeline.supported_platforms or ["youtube"],
                        version=pipeline.version,
                        status=pipeline.status,
                        metadata=pipeline.extra_metadata,
                        created_at=pipeline.created_at,
                        updated_at=pipeline.updated_at
                    )
                    
                    # 更新缓存
                    if pipeline.status == PipelineStatus.ACTIVE.value:
                        self._cache[pipeline_id] = metadata
                    
                    return metadata
                    
        except Exception as e:
            logger.error(f"获取Pipeline失败: {e}")
        
        return None
    
    def list_pipelines(
        self,
        pipeline_type: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[PipelineMetadata]:
        """
        列出Pipeline
        
        Args:
            pipeline_type: 筛选类型
            platform: 筛选平台
            status: 筛选状态
        
        Returns:
            Pipeline列表
        """
        try:
            with self.db.get_session() as session:
                query = session.query(PipelineRegistryModel)
                
                if pipeline_type:
                    query = query.filter_by(pipeline_type=pipeline_type)
                
                if status:
                    query = query.filter_by(status=status)
                
                pipelines = query.all()
                
                # 平台筛选
                result = []
                for p in pipelines:
                    if platform and platform not in (p.supported_platforms or []):
                        continue
                    
                    result.append(PipelineMetadata(
                        pipeline_id=p.pipeline_id,
                        pipeline_name=p.pipeline_name,
                        pipeline_type=p.pipeline_type,
                        pipeline_class=p.pipeline_class,
                        config_schema=p.config_schema or {},
                        supported_platforms=p.supported_platforms or ["youtube"],
                        version=p.version,
                        status=p.status,
                        metadata=p.extra_metadata,  # 使用 extra_metadata
                        created_at=p.created_at,
                        updated_at=p.updated_at
                    ))
                
                return result
                
        except Exception as e:
            logger.error(f"列出Pipeline失败: {e}")
            return []
    
    def create_instance(
        self,
        pipeline_id: str,
        config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        创建Pipeline实例
        
        Args:
            pipeline_id: Pipeline ID
            config: Pipeline配置
        
        Returns:
            Pipeline实例
        """
        metadata = self.get_pipeline(pipeline_id)
        if not metadata:
            logger.error(f"Pipeline不存在: {pipeline_id}")
            return None
        
        # 验证配置
        if not self._validate_config(metadata.config_schema, config):
            logger.error(f"配置验证失败: {pipeline_id}")
            return None
        
        # 获取或加载类
        pipeline_class = self._get_pipeline_class(metadata.pipeline_class)
        if not pipeline_class:
            logger.error(f"无法加载Pipeline类: {metadata.pipeline_class}")
            return None
        
        try:
            # 创建实例
            instance = pipeline_class(**config)
            logger.info(f"成功创建Pipeline实例: {pipeline_id}")
            return instance
            
        except Exception as e:
            logger.error(f"创建Pipeline实例失败: {e}")
            return None
    
    def update_pipeline_status(
        self,
        pipeline_id: str,
        status: str
    ) -> bool:
        """
        更新Pipeline状态
        
        Args:
            pipeline_id: Pipeline ID
            status: 新状态
        
        Returns:
            是否更新成功
        """
        try:
            with self.db.get_session() as session:
                pipeline = session.query(PipelineRegistryModel).filter_by(
                    pipeline_id=pipeline_id
                ).first()
                
                if not pipeline:
                    logger.error(f"Pipeline不存在: {pipeline_id}")
                    return False
                
                pipeline.status = status
                pipeline.updated_at = datetime.now()
                session.commit()
                
                # 更新缓存
                if pipeline_id in self._cache:
                    self._cache[pipeline_id].status = status
                    self._cache[pipeline_id].updated_at = datetime.now()
                
                logger.info(f"更新Pipeline状态: {pipeline_id} -> {status}")
                return True
                
        except Exception as e:
            logger.error(f"更新Pipeline状态失败: {e}")
            return False
    
    def _validate_pipeline_class(self, class_path: str) -> bool:
        """验证Pipeline类是否可以加载"""
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            pipeline_class = getattr(module, class_name)
            return callable(pipeline_class)
        except Exception as e:
            logger.error(f"验证Pipeline类失败: {e}")
            return False
    
    def _get_pipeline_class(self, class_path: str) -> Optional[Type]:
        """获取Pipeline类"""
        # 查缓存
        if class_path in self._class_cache:
            return self._class_cache[class_path]
        
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            pipeline_class = getattr(module, class_name)
            
            # 缓存
            self._class_cache[class_path] = pipeline_class
            return pipeline_class
            
        except Exception as e:
            logger.error(f"加载Pipeline类失败: {e}")
            return None
    
    def _validate_config(
        self,
        schema: Dict[str, Any],
        config: Dict[str, Any]
    ) -> bool:
        """验证配置是否符合模式"""
        if not schema:
            return True
        
        try:
            # 简单验证必需字段
            for field, field_type in schema.items():
                if field not in config:
                    logger.error(f"缺少必需字段: {field}")
                    return False
                
                # 简单类型检查
                if field_type == "string" and not isinstance(config[field], str):
                    logger.error(f"字段类型错误: {field} 应为 string")
                    return False
                elif field_type == "integer" and not isinstance(config[field], int):
                    logger.error(f"字段类型错误: {field} 应为 integer")
                    return False
                elif field_type == "array" and not isinstance(config[field], list):
                    logger.error(f"字段类型错误: {field} 应为 array")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证配置失败: {e}")
            return False
    
    def get_supported_platforms(self, pipeline_id: str) -> List[str]:
        """
        获取Pipeline支持的平台
        
        Args:
            pipeline_id: Pipeline ID
        
        Returns:
            支持的平台列表
        """
        metadata = self.get_pipeline(pipeline_id)
        if metadata:
            return metadata.supported_platforms
        return []
    
    def refresh_cache(self) -> None:
        """刷新缓存"""
        self._cache.clear()
        self._class_cache.clear()
        self._load_cache()
        logger.info("Pipeline缓存已刷新")
    
    def update_pipeline(
        self,
        pipeline_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        更新Pipeline信息
        
        Args:
            pipeline_id: Pipeline ID
            update_data: 更新数据
        
        Returns:
            是否更新成功
        """
        try:
            with self.db.get_session() as session:
                pipeline = session.query(PipelineRegistryModel).filter_by(
                    pipeline_id=pipeline_id
                ).first()
                
                if not pipeline:
                    logger.error(f"Pipeline不存在: {pipeline_id}")
                    return False
                
                # 更新允许的字段
                allowed_fields = [
                    'pipeline_name', 'pipeline_type', 'pipeline_class',
                    'config_schema', 'supported_platforms', 'version',
                    'status', 'metadata'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields:
                        if field == 'metadata':
                            # 使用 extra_metadata 而不是 metadata
                            setattr(pipeline, 'extra_metadata', value)
                        else:
                            setattr(pipeline, field, value)
                
                pipeline.updated_at = datetime.now()
                session.commit()
                
                # 更新缓存
                if pipeline_id in self._cache:
                    for field, value in update_data.items():
                        if field in allowed_fields and hasattr(self._cache[pipeline_id], field):
                            setattr(self._cache[pipeline_id], field, value)
                    self._cache[pipeline_id].updated_at = datetime.now()
                
                logger.info(f"成功更新Pipeline: {pipeline_id}")
                return True
                
        except Exception as e:
            logger.error(f"更新Pipeline失败: {e}")
            return False
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """
        删除Pipeline
        
        Args:
            pipeline_id: Pipeline ID
        
        Returns:
            是否删除成功
        """
        try:
            with self.db.get_session() as session:
                pipeline = session.query(PipelineRegistryModel).filter_by(
                    pipeline_id=pipeline_id
                ).first()
                
                if not pipeline:
                    logger.error(f"Pipeline不存在: {pipeline_id}")
                    return False
                
                # 软删除：将状态设置为DISABLED
                pipeline.status = PipelineStatus.DISABLED.value
                pipeline.updated_at = datetime.now()
                session.commit()
                
                # 从缓存中移除
                if pipeline_id in self._cache:
                    del self._cache[pipeline_id]
                if pipeline.pipeline_class in self._class_cache:
                    del self._class_cache[pipeline.pipeline_class]
                
                logger.info(f"成功删除Pipeline: {pipeline_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除Pipeline失败: {e}")
            return False


# 全局实例
_pipeline_registry = None


def get_pipeline_registry() -> PipelineRegistry:
    """获取Pipeline注册表实例"""
    global _pipeline_registry
    if _pipeline_registry is None:
        _pipeline_registry = PipelineRegistry()
    return _pipeline_registry


# 便捷函数
def register_pipeline(
    pipeline_id: str,
    pipeline_name: str,
    pipeline_type: str,
    pipeline_class: str,
    config_schema: Dict[str, Any],
    **kwargs
) -> bool:
    """注册Pipeline便捷函数"""
    registry = get_pipeline_registry()
    return registry.register_pipeline(
        pipeline_id=pipeline_id,
        pipeline_name=pipeline_name,
        pipeline_type=pipeline_type,
        pipeline_class=pipeline_class,
        config_schema=config_schema,
        **kwargs
    )


def create_pipeline_instance(
    pipeline_id: str,
    config: Dict[str, Any]
) -> Optional[Any]:
    """创建Pipeline实例便捷函数"""
    registry = get_pipeline_registry()
    return registry.create_instance(pipeline_id, config)