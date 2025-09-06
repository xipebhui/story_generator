#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础Pipeline抽象类
所有Pipeline都应该继承这个类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """
    基础Pipeline类，提供标准化的执行接口
    所有Pipeline都应该继承这个类
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Pipeline
        
        Args:
            config: Pipeline配置参数
        """
        self.config = config or {}
        self.start_time = None
        self.end_time = None
        self.stages_results = []
        
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步执行Pipeline（必须实现）
        
        Args:
            params: 执行参数，标准参数包括：
                - account_id: 账号ID
                - video_id: 视频ID（如果适用）
                - creator_id: 创作者ID
                - 其他Pipeline特定参数
        
        Returns:
            dict: 执行结果，标准格式包括：
                - success: 是否成功
                - data: 返回数据（成功时）
                - error: 错误信息（失败时）
                - stages: 各阶段执行结果
                - metadata: 元数据信息
        """
        pass
    
    def validate_params(self, params: Dict[str, Any], required_fields: List[str]) -> tuple[bool, Optional[str]]:
        """
        验证输入参数
        
        Args:
            params: 输入参数
            required_fields: 必需字段列表
        
        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        for field in required_fields:
            if field not in params or params[field] is None:
                return False, f"Missing required parameter: {field}"
        return True, None
    
    def handle_error(self, error: Exception, stage: str) -> Dict[str, Any]:
        """
        统一错误处理
        
        Args:
            error: 异常对象
            stage: 发生错误的阶段
        
        Returns:
            dict: 错误信息字典
        """
        error_msg = str(error)
        logger.error(f"Pipeline error in stage '{stage}': {error_msg}")
        logger.exception("Detailed error:")
        
        return {
            'success': False,
            'error': error_msg,
            'stage': stage,
            'timestamp': datetime.now().isoformat()
        }
    
    def create_stage_result(self, 
                          name: str, 
                          success: bool,
                          data: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None,
                          duration: Optional[float] = None) -> Dict[str, Any]:
        """
        创建标准化的阶段结果
        
        Args:
            name: 阶段名称
            success: 是否成功
            data: 返回数据
            error: 错误信息
            duration: 执行时长（秒）
        
        Returns:
            dict: 阶段结果
        """
        result = {
            'name': name,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if data is not None:
            result['data'] = data
        if error is not None:
            result['error'] = error
        if duration is not None:
            result['duration'] = duration
            
        return result
    
    def get_cache_dir(self, params: Dict[str, Any]) -> Path:
        """
        获取缓存目录路径
        
        Args:
            params: 执行参数
        
        Returns:
            Path: 缓存目录路径
        """
        # 默认使用 outputs/creator_id/account_id/video_id 结构
        creator_id = params.get('creator_id', 'default')
        account_id = params.get('account_id', 'default')
        video_id = params.get('video_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        cache_dir = Path('outputs') / creator_id / account_id / video_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        return cache_dir
    
    def should_skip_stage(self, stage_name: str, cache_dir: Path) -> bool:
        """
        检查阶段是否可以跳过（基于缓存）
        
        Args:
            stage_name: 阶段名称
            cache_dir: 缓存目录
        
        Returns:
            bool: 是否跳过
        """
        # 子类可以覆盖此方法实现具体的缓存检查逻辑
        return False
    
    def collect_outputs(self) -> Dict[str, Any]:
        """
        收集所有阶段的输出
        
        Returns:
            dict: 汇总的输出数据
        """
        outputs = {}
        for stage_result in self.stages_results:
            if stage_result.get('success') and stage_result.get('data'):
                stage_name = stage_result['name']
                outputs[stage_name] = stage_result['data']
        return outputs
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            dict: 执行摘要信息
        """
        total_duration = None
        if self.start_time and self.end_time:
            total_duration = (self.end_time - self.start_time).total_seconds()
        
        successful_stages = sum(1 for s in self.stages_results if s.get('success'))
        failed_stages = sum(1 for s in self.stages_results if not s.get('success'))
        
        return {
            'total_stages': len(self.stages_results),
            'successful_stages': successful_stages,
            'failed_stages': failed_stages,
            'total_duration': total_duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class PipelineStage:
    """
    Pipeline阶段定义
    """
    
    def __init__(self, 
                 name: str, 
                 handler: callable,
                 required: bool = False,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化阶段
        
        Args:
            name: 阶段名称
            handler: 处理函数
            required: 是否必需（必需阶段失败会终止Pipeline）
            config: 阶段配置
        """
        self.name = name
        self.handler = handler
        self.required = required
        self.config = config or {}
        self.result = None
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行阶段
        
        Args:
            context: 执行上下文
        
        Returns:
            dict: 阶段执行结果
        """
        try:
            logger.info(f"Executing stage: {self.name}")
            start_time = datetime.now()
            
            # 执行处理函数
            result_data = await self.handler(context, self.config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.result = {
                'name': self.name,
                'success': True,
                'data': result_data,
                'duration': duration,
                'timestamp': end_time.isoformat()
            }
            
            logger.info(f"Stage '{self.name}' completed successfully in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Stage '{self.name}' failed: {str(e)}")
            self.result = {
                'name': self.name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'required': self.required
            }
        
        return self.result
    
    def is_required(self) -> bool:
        """
        检查阶段是否必需
        
        Returns:
            bool: 是否必需
        """
        return self.required