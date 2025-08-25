#!/usr/bin/env python3
"""
配置管理系统
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class TTSConfig(BaseModel):
    """TTS配置"""
    service: str = "edge_tts"  # 可选: edge_tts, azure_tts, etc.
    voice: str = "zh-CN-XiaoxiaoNeural"  # 默认中文女声
    rate: str = "+0%"  # 语速调整
    pitch: str = "+0Hz"  # 音调调整
    volume: str = "+0%"  # 音量调整
    
    # 备选声音
    voice_alternatives: Dict[str, str] = Field(default_factory=lambda: {
        "female": "zh-CN-XiaoxiaoNeural",
        "male": "zh-CN-YunxiNeural",
        "child": "zh-CN-XiaoyiNeural"
    })


class NarrationConfig(BaseModel):
    """文案生成配置"""
    words_per_second: float = 2.5  # 每秒字数（用于估算时长）
    min_words_per_image: int = 30  # 每张图最少字数
    max_words_per_image: int = 80  # 每张图最多字数
    default_words_per_image: int = 50  # 默认字数
    
    # 连接词库
    transition_words: list = Field(default_factory=lambda: [
        "接着", "随后", "与此同时", "这时", "突然",
        "紧接着", "片刻后", "不久", "正当", "就在这时"
    ])
    
    # 语言风格
    narration_style: str = "生动活泼"  # 可选: 生动活泼, 严肃正式, 幽默风趣, 悬疑紧张
    use_idioms: bool = True  # 是否使用成语
    use_metaphors: bool = True  # 是否使用比喻


class SceneDurationConfig(BaseModel):
    """场景时长配置"""
    action: tuple = (3, 5)  # 动作场景时长范围
    dialog: tuple = (5, 8)  # 对话场景时长范围
    transition: tuple = (2, 3)  # 过渡场景时长范围
    climax: tuple = (8, 10)  # 高潮场景时长范围
    static: tuple = (3, 4)  # 静态场景时长范围
    
    @validator('*', pre=True)
    def validate_tuple(cls, v):
        if isinstance(v, list):
            return tuple(v)
        return v


class GeminiConfig(BaseModel):
    """Gemini API配置 - 使用NewAPI服务"""
    model: str = "gemini-2.5-flash"  # NewAPI使用的模型
    temperature: float = 0.7
    max_output_tokens: int = 2048
    timeout: int = 30  # 请求超时时间（秒）
    # API密钥和URL从环境变量读取，不在配置文件中设置


class PipelineConfig(BaseModel):
    """Pipeline执行配置"""
    cache_enabled: bool = True  # 是否启用缓存
    cache_dir: str = ".cache/comic_pipeline"  # 缓存目录
    parallel_processing: bool = True  # 是否并行处理
    max_workers: int = 4  # 最大并行数
    
    # 输出配置
    output_dir: str = "output/comic_videos"
    keep_intermediate_files: bool = True  # 是否保留中间文件
    
    # 重试配置
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 重试延迟（秒）


class ComicPipelineConfig(BaseModel):
    """漫画Pipeline总配置"""
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    narration: NarrationConfig = Field(default_factory=NarrationConfig)
    scene_durations: SceneDurationConfig = Field(default_factory=SceneDurationConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    
    # 项目路径配置
    project_root: str = Field(default_factory=lambda: str(Path(__file__).parent.parent.parent))
    prompts_dir: str = "prompts/comic"
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "ComicPipelineConfig":
        """从YAML文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ComicPipelineConfig":
        """从字典加载配置"""
        return cls(**config_dict)
    
    def to_yaml(self, output_path: str):
        """保存配置到YAML文件"""
        config_dict = self.dict()
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
    
    def get_prompt_path(self, prompt_name: str) -> Path:
        """获取提示词文件路径"""
        return Path(self.project_root) / self.prompts_dir / f"{prompt_name}.md"
    
    def get_cache_path(self, *parts) -> Path:
        """获取缓存文件路径"""
        cache_dir = Path(self.pipeline.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / Path(*parts)
    
    def get_output_path(self, *parts) -> Path:
        """获取输出文件路径"""
        output_dir = Path(self.pipeline.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / Path(*parts)


def create_default_config() -> ComicPipelineConfig:
    """创建默认配置"""
    return ComicPipelineConfig()


def load_or_create_config(config_path: Optional[str] = None) -> ComicPipelineConfig:
    """加载或创建配置"""
    if config_path and Path(config_path).exists():
        return ComicPipelineConfig.from_yaml(config_path)
    
    # 尝试从默认位置加载
    default_paths = [
        "comic_config.yaml",
        "config/comic_pipeline.yaml",
        "webtoon/comic_config.yaml"
    ]
    
    for path in default_paths:
        if Path(path).exists():
            return ComicPipelineConfig.from_yaml(path)
    
    # 创建默认配置
    return create_default_config()