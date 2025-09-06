#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline执行上下文管理器
管理Pipeline执行过程中的状态和数据传递
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class PipelineContext:
    """
    Pipeline执行上下文
    用于在不同阶段之间传递数据和管理状态
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        初始化上下文
        
        Args:
            params: Pipeline执行参数
        """
        self.params = params
        self.outputs = {}
        self.files = {}
        self.metadata = {}
        self.stage_outputs = {}
        
        # 初始化缓存目录
        self.cache_dir = self._init_cache_dir()
        
        # 初始化文件路径
        self.paths = self._init_paths()
        
        logger.info(f"Pipeline context initialized with cache_dir: {self.cache_dir}")
    
    def _init_cache_dir(self) -> Path:
        """
        初始化缓存目录
        
        Returns:
            Path: 缓存目录路径
        """
        # 构建目录结构
        creator_id = self.params.get('creator_id', 'default')
        account_id = self.params.get('account_id', '')
        video_id = self.params.get('video_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        # 如果有account_id，包含在路径中
        if account_id:
            cache_dir = Path('outputs') / creator_id / account_id / video_id
        else:
            cache_dir = Path('outputs') / creator_id / video_id
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (cache_dir / 'story').mkdir(exist_ok=True)
        (cache_dir / 'audio').mkdir(exist_ok=True)
        (cache_dir / 'draft').mkdir(exist_ok=True)
        (cache_dir / 'video').mkdir(exist_ok=True)
        (cache_dir / 'publish').mkdir(exist_ok=True)
        
        return cache_dir
    
    def _init_paths(self) -> Dict[str, Path]:
        """
        初始化标准文件路径
        
        Returns:
            dict: 文件路径映射
        """
        paths = {
            # 故事相关
            'story': self.cache_dir / 'story' / 'story.txt',
            'story_processed': self.cache_dir / 'story' / 'story_processed.txt',
            'story_metadata': self.cache_dir / 'story' / 'metadata.json',
            
            # 音频相关
            'audio': self.cache_dir / 'audio' / 'audio.mp3',
            'srt': self.cache_dir / 'audio' / 'subtitles.srt',
            
            # 草稿相关
            'draft': self.cache_dir / 'draft' / 'draft.jy',
            'draft_folder': self.cache_dir / 'draft' / 'draft_folder',
            
            # 视频相关
            'video': self.cache_dir / 'video' / 'final_video.mp4',
            'preview': self.cache_dir / 'video' / 'preview.mp4',
            'thumbnail': self.cache_dir / 'video' / 'thumbnail.jpg',
            
            # 发布相关
            'youtube_metadata': self.cache_dir / 'publish' / 'youtube_metadata.json',
            'publish_result': self.cache_dir / 'publish' / 'publish_result.json'
        }
        
        return paths
    
    def set_output(self, key: str, value: Any) -> None:
        """
        保存输出数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.outputs[key] = value
        logger.debug(f"Set output: {key}")
    
    def get_output(self, key: str, default: Any = None) -> Any:
        """
        获取输出数据
        
        Args:
            key: 数据键
            default: 默认值
        
        Returns:
            Any: 数据值或默认值
        """
        return self.outputs.get(key, default)
    
    def set_stage_output(self, stage_name: str, output: Dict[str, Any]) -> None:
        """
        保存阶段输出
        
        Args:
            stage_name: 阶段名称
            output: 阶段输出数据
        """
        self.stage_outputs[stage_name] = output
        logger.debug(f"Set stage output for: {stage_name}")
    
    def get_stage_output(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """
        获取阶段输出
        
        Args:
            stage_name: 阶段名称
        
        Returns:
            dict: 阶段输出数据
        """
        return self.stage_outputs.get(stage_name)
    
    def add_file(self, key: str, file_path: Path) -> None:
        """
        添加文件引用
        
        Args:
            key: 文件键
            file_path: 文件路径
        """
        self.files[key] = str(file_path)
        logger.debug(f"Added file: {key} -> {file_path}")
    
    def get_file(self, key: str) -> Optional[Path]:
        """
        获取文件路径
        
        Args:
            key: 文件键
        
        Returns:
            Path: 文件路径或None
        """
        file_path = self.files.get(key)
        return Path(file_path) if file_path else None
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据
        
        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 元数据键
            default: 默认值
        
        Returns:
            Any: 元数据值或默认值
        """
        return self.metadata.get(key, default)
    
    def save_to_file(self, filename: str, data: Any) -> Path:
        """
        保存数据到文件
        
        Args:
            filename: 文件名
            data: 数据
        
        Returns:
            Path: 保存的文件路径
        """
        file_path = self.cache_dir / filename
        
        if isinstance(data, dict) or isinstance(data, list):
            # JSON数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            # 文本数据
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        logger.debug(f"Saved data to: {file_path}")
        return file_path
    
    def load_from_file(self, filename: str) -> Optional[Any]:
        """
        从文件加载数据
        
        Args:
            filename: 文件名
        
        Returns:
            Any: 加载的数据或None
        """
        file_path = self.cache_dir / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 尝试作为JSON加载
                if file_path.suffix == '.json':
                    return json.load(f)
                else:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load file {filename}: {e}")
            return None
    
    def check_file_exists(self, file_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_key: 文件键（在paths中定义）
        
        Returns:
            bool: 文件是否存在
        """
        file_path = self.paths.get(file_key)
        if file_path:
            return file_path.exists()
        return False
    
    def get_story_source_path(self) -> Path:
        """
        获取故事源文件路径（兼容旧版结构）
        
        Returns:
            Path: 故事文件路径
        """
        # 检查旧版路径（story_pipeline_v3_runner.py 输出路径）
        creator_id = self.params.get('creator_id', 'default')
        video_id = self.params.get('video_id', '')
        old_path = Path(f"story_result/{creator_id}/{video_id}/final/story.txt")
        
        if old_path.exists():
            return old_path
            
        # 检查新路径
        if self.paths['story'].exists():
            return self.paths['story']
        
        # 返回预期的旧路径（用于新创建）
        return old_path
    
    def get_audio_output_path(self) -> Path:
        """
        获取音频输出路径（兼容旧版结构）
        
        Returns:
            Path: 音频文件路径
        """
        # 总是返回旧版路径格式（tts_client.py 期望的路径）
        creator_id = self.params.get('creator_id', 'default')
        account_id = self.params.get('account_id', '')
        video_id = self.params.get('video_id', '')
        
        if account_id:
            return Path(f"output/{creator_id}_{account_id}_{video_id}_story.mp3")
        else:
            return Path(f"output/{creator_id}_{video_id}_story.mp3")
    
    def get_draft_output_path(self) -> Path:
        """
        获取草稿输出路径（兼容旧版结构）
        
        Returns:
            Path: 草稿文件路径
        """
        # 总是返回旧版路径格式（generateDraftService.py 期望的路径）
        creator_id = self.params.get('creator_id', 'default')
        account_id = self.params.get('account_id', '')
        video_id = self.params.get('video_id', '')
        
        if account_id:
            return Path(f"output/drafts/{creator_id}_{account_id}_{video_id}_story")
        else:
            return Path(f"output/drafts/{creator_id}_{video_id}_story")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            dict: 上下文数据字典
        """
        return {
            'params': self.params,
            'outputs': self.outputs,
            'files': self.files,
            'metadata': self.metadata,
            'stage_outputs': self.stage_outputs,
            'cache_dir': str(self.cache_dir)
        }