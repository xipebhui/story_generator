#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pipeline Architecture for Story Generation
解耦提示词和业务逻辑的架构设计
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


# ============= 数据模型 =============

@dataclass
class PipelineContext:
    """Pipeline上下文，在整个流程中传递数据"""
    # 输入数据
    video_id: str
    creator_name: str
    target_length: int = 30000
    num_segments: int = 9
    
    # 原始数据
    video_info: Dict[str, Any] = field(default_factory=dict)
    comments: List[Dict] = field(default_factory=list)
    subtitles: str = ""
    
    # 处理结果
    story_dna: str = ""
    framework: str = ""
    segments: List[str] = field(default_factory=list)
    draft_story: str = ""
    final_story: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 缓存管理
    cache_dir: Optional[Path] = None
    
    def get(self, key: str, default=None):
        """获取上下文数据"""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        setattr(self, key, value)
    
    def update(self, **kwargs):
        """批量更新上下文"""
        for key, value in kwargs.items():
            self.set(key, value)


@dataclass
class StepResult:
    """步骤执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============= 提示词管理器 =============

class PromptTemplate:
    """提示词模板类"""
    
    def __init__(self, template: str, variables: List[str] = None):
        self.template = template
        self.variables = variables or []
        
    def format(self, **kwargs) -> str:
        """格式化提示词"""
        return self.template.format(**kwargs)
    
    def validate_variables(self, **kwargs) -> bool:
        """验证必需的变量是否提供"""
        return all(var in kwargs for var in self.variables)


class PromptManager:
    """提示词管理器 - 集中管理所有提示词"""
    
    def __init__(self, prompts_dir: Path = None):
        self.prompts_dir = prompts_dir or Path("prompts")
        self.templates: Dict[str, PromptTemplate] = {}
        self.prompt_configs: Dict[str, Dict] = {}
        
    def load_prompt(self, name: str, file_path: Optional[str] = None) -> PromptTemplate:
        """加载提示词模板"""
        if name in self.templates:
            return self.templates[name]
            
        if file_path:
            path = Path(file_path)
        else:
            path = self.prompts_dir / f"{name}.md"
            
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析变量（查找 {variable} 格式）
            import re
            variables = re.findall(r'\{(\w+)\}', content)
            
            template = PromptTemplate(content, variables)
            self.templates[name] = template
            logger.info(f"Loaded prompt template: {name}")
            return template
        else:
            raise FileNotFoundError(f"Prompt file not found: {path}")
    
    def load_config(self, config_path: str):
        """加载提示词配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for name, settings in config.items():
            self.prompt_configs[name] = settings
            if 'file' in settings:
                self.load_prompt(name, settings['file'])
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """获取格式化的提示词"""
        if name not in self.templates:
            self.load_prompt(name)
        
        template = self.templates[name]
        if not template.validate_variables(**kwargs):
            missing = [v for v in template.variables if v not in kwargs]
            raise ValueError(f"Missing variables for prompt '{name}': {missing}")
        
        return template.format(**kwargs)
    
    def register_template(self, name: str, template: str, variables: List[str] = None):
        """注册自定义提示词模板"""
        self.templates[name] = PromptTemplate(template, variables)


# ============= Pipeline基础架构 =============

class PipelineStep(ABC):
    """Pipeline步骤基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.prompt_manager: Optional[PromptManager] = None
        
    def set_prompt_manager(self, manager: PromptManager):
        """设置提示词管理器"""
        self.prompt_manager = manager
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> StepResult:
        """执行步骤"""
        pass
    
    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        return True
    
    def should_skip(self, context: PipelineContext) -> bool:
        """判断是否跳过此步骤"""
        return False
    
    def load_cache(self, context: PipelineContext) -> Optional[Any]:
        """加载缓存"""
        if not context.cache_dir:
            return None
        
        cache_file = context.cache_dir / f"{self.name}_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {self.name}: {e}")
        return None
    
    def save_cache(self, context: PipelineContext, data: Any):
        """保存缓存"""
        if not context.cache_dir:
            return
        
        cache_file = context.cache_dir / f"{self.name}_cache.json"
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache for {self.name}: {e}")


class Pipeline:
    """Pipeline主类 - 管理和执行步骤"""
    
    def __init__(self, name: str):
        self.name = name
        self.steps: List[PipelineStep] = []
        self.prompt_manager = PromptManager()
        self.hooks: Dict[str, List[Callable]] = {
            'before_step': [],
            'after_step': [],
            'on_error': [],
            'on_complete': []
        }
        
    def add_step(self, step: PipelineStep):
        """添加步骤"""
        step.set_prompt_manager(self.prompt_manager)
        self.steps.append(step)
        return self
    
    def add_hook(self, event: str, callback: Callable):
        """添加钩子函数"""
        if event in self.hooks:
            self.hooks[event].append(callback)
    
    def execute(self, context: PipelineContext) -> bool:
        """执行Pipeline"""
        logger.info(f"Starting pipeline: {self.name}")
        
        for step in self.steps:
            # 执行前钩子
            for hook in self.hooks['before_step']:
                hook(step, context)
            
            # 检查是否跳过
            if step.should_skip(context):
                logger.info(f"Skipping step: {step.name}")
                continue
            
            # 验证输入
            if not step.validate_input(context):
                logger.error(f"Input validation failed for step: {step.name}")
                for hook in self.hooks['on_error']:
                    hook(step, context, "Input validation failed")
                return False
            
            try:
                logger.info(f"Executing step: {step.name}")
                result = step.execute(context)
                
                if not result.success:
                    logger.error(f"Step failed: {step.name} - {result.error}")
                    for hook in self.hooks['on_error']:
                        hook(step, context, result.error)
                    return False
                
                # 执行后钩子
                for hook in self.hooks['after_step']:
                    hook(step, context, result)
                    
            except Exception as e:
                logger.error(f"Step {step.name} raised exception: {e}")
                for hook in self.hooks['on_error']:
                    hook(step, context, str(e))
                return False
        
        # 完成钩子
        for hook in self.hooks['on_complete']:
            hook(context)
        
        logger.info(f"Pipeline {self.name} completed successfully")
        return True


# ============= 策略模式 - 可替换的处理策略 =============

class ProcessingStrategy(ABC):
    """处理策略基类"""
    
    @abstractmethod
    def process(self, input_data: Any, **kwargs) -> Any:
        """处理数据"""
        pass


class PromptFormattingStrategy(ProcessingStrategy):
    """提示词格式化策略"""
    
    def __init__(self, format_type: str = "default"):
        self.format_type = format_type
    
    def process(self, input_data: Any, **kwargs) -> str:
        """根据不同格式类型处理提示词"""
        if self.format_type == "default":
            return self._format_default(input_data, **kwargs)
        elif self.format_type == "structured":
            return self._format_structured(input_data, **kwargs)
        elif self.format_type == "narrative":
            return self._format_narrative(input_data, **kwargs)
        else:
            raise ValueError(f"Unknown format type: {self.format_type}")
    
    def _format_default(self, input_data: Any, **kwargs) -> str:
        """默认格式化"""
        return str(input_data)
    
    def _format_structured(self, input_data: Any, **kwargs) -> str:
        """结构化格式"""
        sections = kwargs.get('sections', {})
        output = []
        for title, content in sections.items():
            output.append(f"{'='*50}")
            output.append(f"{title}")
            output.append(f"{'='*50}")
            output.append(content)
            output.append("")
        return "\n".join(output)
    
    def _format_narrative(self, input_data: Any, **kwargs) -> str:
        """叙事格式"""
        return f"Story Context:\n{input_data}\n\nTask: {kwargs.get('task', 'Continue the story')}"


# ============= 配置管理 =============

class PipelineConfig:
    """Pipeline配置类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = {}
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def get_pipeline_config(self, pipeline_name: str) -> Dict:
        """获取特定Pipeline的配置"""
        return self.config.get('pipelines', {}).get(pipeline_name, {})
    
    def get_prompt_config(self, prompt_name: str) -> Dict:
        """获取提示词配置"""
        return self.config.get('prompts', {}).get(prompt_name, {})
    
    def get_strategy_config(self, strategy_name: str) -> Dict:
        """获取策略配置"""
        return self.config.get('strategies', {}).get(strategy_name, {})


# ============= 工厂模式 - 创建Pipeline =============

class PipelineFactory:
    """Pipeline工厂类"""
    
    @staticmethod
    def create_story_pipeline(config: Optional[PipelineConfig] = None) -> Pipeline:
        """创建故事生成Pipeline"""
        pipeline = Pipeline("StoryGeneration")
        
        # 这里将添加具体的步骤实现
        # pipeline.add_step(FetchDataStep())
        # pipeline.add_step(ExtractDNAStep())
        # pipeline.add_step(GenerateFrameworkStep())
        # pipeline.add_step(GenerateSegmentsStep())
        # pipeline.add_step(PolishStoryStep())
        
        return pipeline
    
    @staticmethod
    def create_custom_pipeline(name: str, steps: List[PipelineStep]) -> Pipeline:
        """创建自定义Pipeline"""
        pipeline = Pipeline(name)
        for step in steps:
            pipeline.add_step(step)
        return pipeline