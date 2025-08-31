# Pipeline 开发规范指南

## 概述

本文档定义了账号驱动自动发布系统中 Pipeline 的开发规范。所有新开发的 Pipeline 都必须遵循这些规范，以确保与自动发布系统的无缝集成。

## 1. Pipeline 类型分类

### 1.1 内容生成型 Pipeline
生成完整的内容（视频、文章、图片等）
- **示例**：StoryPipelineV3（故事生成）、ComicPipeline（漫画生成）
- **特点**：执行时间长、资源消耗大、输出完整内容

### 1.2 内容处理型 Pipeline
处理或转换已有内容
- **示例**：VideoMergePipeline（视频合并）、ThumbnailGenerator（缩略图生成）
- **特点**：依赖输入内容、执行时间中等、输出处理后的内容

### 1.3 元数据型 Pipeline
仅生成元数据或配置信息
- **示例**：YouTubeMetadataGenerator（生成标题、描述、标签）
- **特点**：执行快速、资源消耗小、输出JSON格式数据

### 1.4 下载型 Pipeline
下载或采集外部资源
- **示例**：VideoDownloader、TranscriptFetcher
- **特点**：网络依赖、需要重试机制、输出文件或数据

## 2. Pipeline 接口规范

### 2.1 必需的类结构

```python
class YourPipeline:
    """Pipeline 类文档说明"""
    
    def __init__(self, config: dict = None):
        """
        初始化 Pipeline
        
        Args:
            config: Pipeline配置参数（来自自动发布系统）
                - 通用参数会自动传入
                - Pipeline特定参数需要在config_schema中定义
        """
        self.config = config or {}
        # 初始化Pipeline所需的资源
        self._init_resources()
    
    def execute(self, params: dict) -> dict:
        """
        执行Pipeline - 自动发布系统标准接口【必需实现】
        
        Args:
            params: 执行参数（来自调度系统）
        
        Returns:
            dict: 标准返回格式
        """
        # 实现执行逻辑
        pass
    
    def run(self, **kwargs) -> Any:
        """
        执行Pipeline - 命令行接口【可选】
        
        用于命令行直接调用和测试
        """
        # 实现命令行执行逻辑
        pass
```

### 2.2 execute 方法规范

#### 输入参数 (params)

**通用参数**（系统自动传入）：
```python
{
    'task_id': str,          # 任务ID
    'account_id': str,       # 账号ID
    'config_id': str,        # 配置ID
    'scheduled_time': str,   # 计划执行时间
    'metadata': dict         # 其他元数据
}
```

**Pipeline特定参数**（根据类型定义）：
```python
# 内容生成型
{
    'video_id': str,         # YouTube视频ID
    'duration': int,         # 目标时长（秒）
    'language': str,         # 语言设置
    'style': str            # 风格设置
}

# 元数据型
{
    'content_path': str,     # 内容文件路径
    'platform': str,         # 目标平台
    'optimize_for': str      # 优化目标（如'engagement'）
}
```

#### 返回格式 (标准)

**成功返回**：
```python
{
    'success': True,
    
    # 内容输出（根据Pipeline类型选择）
    'video_path': str,       # 视频文件路径
    'audio_path': str,       # 音频文件路径
    'image_path': str,       # 图片文件路径
    'text_path': str,        # 文本文件路径
    'output_dir': str,       # 输出目录路径
    
    # 发布元数据（用于发布）
    'title': str,            # 标题
    'description': str,      # 描述
    'tags': List[str],       # 标签列表
    'thumbnail': str,        # 缩略图路径
    'category': str,         # 分类
    
    # 附加信息
    'metadata': {
        'pipeline_type': str,     # Pipeline类型标识
        'pipeline_version': str,  # Pipeline版本
        'execution_time': float,  # 执行时间（秒）
        'resource_usage': dict,   # 资源使用情况
        # Pipeline特定的元数据
    }
}
```

**失败返回**：
```python
{
    'success': False,
    'error': str,            # 错误信息
    'error_code': str,       # 错误代码（可选）
    'retry_able': bool,      # 是否可重试（可选）
    'partial_result': dict   # 部分结果（可选）
}
```

## 3. Pipeline 注册规范

### 3.1 注册信息定义

```python
# 在 pipeline_registry.py 中注册
registry.register_pipeline(
    pipeline_id="your_pipeline_v1",          # 唯一标识符
    pipeline_name="Your Pipeline Name",       # 显示名称
    pipeline_type="content_generation",       # 类型分类
    pipeline_class="module.YourPipeline",     # 类路径
    config_schema={                          # 配置架构
        "type": "object",
        "properties": {
            "video_id": {
                "type": "string",
                "description": "YouTube视频ID"
            },
            "duration": {
                "type": "integer",
                "default": 120,
                "description": "目标时长（秒）"
            }
        },
        "required": ["video_id"]
    },
    supported_platforms=["youtube", "bilibili"],  # 支持的平台
    version="1.0.0",                             # 版本号
    description="Pipeline功能描述",               # 功能描述
    author="作者名",                              # 作者
    tags=["video", "story", "ai"]                # 标签
)
```

### 3.2 配置架构 (config_schema)

使用 JSON Schema 定义配置参数：

```python
config_schema = {
    "type": "object",
    "properties": {
        # 必需参数
        "required_param": {
            "type": "string",
            "description": "必需参数说明"
        },
        
        # 可选参数（带默认值）
        "optional_param": {
            "type": "integer",
            "default": 100,
            "minimum": 1,
            "maximum": 1000,
            "description": "可选参数说明"
        },
        
        # 枚举参数
        "style": {
            "type": "string",
            "enum": ["casual", "formal", "creative"],
            "default": "casual",
            "description": "风格选择"
        },
        
        # 复杂参数
        "advanced_config": {
            "type": "object",
            "properties": {
                "sub_param": {"type": "string"}
            }
        }
    },
    "required": ["required_param"]  # 必需参数列表
}
```

## 4. 最佳实践

### 4.1 错误处理

```python
def execute(self, params: dict) -> dict:
    try:
        # 参数验证
        if not self._validate_params(params):
            return {
                'success': False,
                'error': 'Invalid parameters',
                'retry_able': False
            }
        
        # 执行逻辑
        result = self._process(params)
        
        return {
            'success': True,
            **result
        }
        
    except NetworkError as e:
        # 网络错误可重试
        return {
            'success': False,
            'error': str(e),
            'retry_able': True
        }
    
    except Exception as e:
        # 其他错误
        logger.error(f"Pipeline执行失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'retry_able': False
        }
```

### 4.2 资源管理

```python
class YourPipeline:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._init_resources()
    
    def _init_resources(self):
        """初始化资源（延迟加载）"""
        self._api_client = None
        self._model = None
    
    @property
    def api_client(self):
        """延迟加载API客户端"""
        if self._api_client is None:
            self._api_client = APIClient(
                api_key=self.config.get('api_key')
            )
        return self._api_client
    
    def cleanup(self):
        """清理资源"""
        if self._model:
            self._model.cleanup()
        if self._api_client:
            self._api_client.close()
```

### 4.3 日志记录

```python
import logging

logger = logging.getLogger(__name__)

class YourPipeline:
    def execute(self, params: dict) -> dict:
        task_id = params.get('task_id', 'unknown')
        
        logger.info(f"[{task_id}] 开始执行Pipeline")
        logger.debug(f"[{task_id}] 参数: {params}")
        
        try:
            # 执行逻辑
            result = self._process(params)
            logger.info(f"[{task_id}] Pipeline执行成功")
            return result
            
        except Exception as e:
            logger.error(f"[{task_id}] Pipeline执行失败: {e}")
            raise
```

### 4.4 进度报告

```python
class YourPipeline:
    def execute(self, params: dict) -> dict:
        total_steps = 5
        
        # 步骤1
        self._report_progress(params, 1, total_steps, "初始化")
        self._init_task()
        
        # 步骤2
        self._report_progress(params, 2, total_steps, "下载资源")
        self._download_resources()
        
        # 继续其他步骤...
    
    def _report_progress(self, params: dict, current: int, 
                        total: int, message: str):
        """报告进度（可选实现）"""
        task_id = params.get('task_id')
        progress = current / total * 100
        
        logger.info(f"[{task_id}] 进度: {progress:.1f}% - {message}")
        
        # 可以将进度写入数据库或发送消息
        # self._update_task_progress(task_id, progress, message)
```

## 5. 示例 Pipeline

### 5.1 极简下载 Pipeline

```python
class SimpleDownloadPipeline:
    """极简的下载Pipeline示例"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
    
    def execute(self, params: dict) -> dict:
        """执行下载"""
        try:
            url = params.get('url')
            if not url:
                return {'success': False, 'error': 'Missing URL'}
            
            # 下载逻辑
            output_path = self._download(url)
            
            return {
                'success': True,
                'output_path': output_path,
                'metadata': {
                    'url': url,
                    'pipeline_type': 'download'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _download(self, url: str) -> str:
        """实际下载逻辑"""
        # 实现下载
        pass
```

### 5.2 元数据生成 Pipeline

```python
class MetadataGeneratorPipeline:
    """YouTube元数据生成Pipeline示例"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._init_ai_client()
    
    def execute(self, params: dict) -> dict:
        """生成元数据"""
        try:
            content_path = params.get('content_path')
            if not content_path:
                return {'success': False, 'error': 'Missing content path'}
            
            # 读取内容
            content = self._read_content(content_path)
            
            # 生成元数据
            metadata = self._generate_metadata(content)
            
            return {
                'success': True,
                'title': metadata['title'],
                'description': metadata['description'],
                'tags': metadata['tags'],
                'metadata': {
                    'pipeline_type': 'metadata_generation',
                    'content_length': len(content)
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

## 6. 测试规范

### 6.1 单元测试

```python
import unittest
from your_pipeline import YourPipeline

class TestYourPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = YourPipeline({'test_mode': True})
    
    def test_execute_success(self):
        """测试成功执行"""
        params = {'video_id': 'test123'}
        result = self.pipeline.execute(params)
        
        self.assertTrue(result['success'])
        self.assertIn('output_path', result)
    
    def test_execute_missing_params(self):
        """测试缺少参数"""
        params = {}
        result = self.pipeline.execute(params)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
```

### 6.2 集成测试

```python
# 测试与自动发布系统的集成
def test_pipeline_registration():
    """测试Pipeline注册"""
    from pipeline_registry import PipelineRegistry
    
    registry = PipelineRegistry()
    pipeline = registry.create_instance('your_pipeline_v1', {})
    
    assert pipeline is not None
    assert hasattr(pipeline, 'execute')
```

## 7. 部署检查清单

- [ ] Pipeline类实现了 `__init__(config)` 方法
- [ ] Pipeline类实现了 `execute(params)` 方法
- [ ] execute方法返回标准格式的字典
- [ ] 所有必需参数都有验证
- [ ] 错误处理完善，返回有意义的错误信息
- [ ] 日志记录充分
- [ ] 在pipeline_registry中注册
- [ ] config_schema定义完整
- [ ] 编写了单元测试
- [ ] 文档说明清晰
- [ ] 资源清理机制完善

## 8. 版本管理

### 版本号规则
- **主版本号**：不兼容的API修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 版本升级策略
1. 保持旧版本Pipeline可用
2. 新版本使用新的pipeline_id（如 `story_v3` → `story_v4`）
3. 在注册表中标记deprecated状态
4. 提供迁移指南

## 总结

遵循这些规范可以确保您的Pipeline能够：
1. 无缝集成到账号驱动自动发布系统
2. 支持自动调度和执行
3. 提供标准化的监控和日志
4. 便于维护和升级
5. 支持A/B测试和策略优化

如有疑问，请参考 `story_pipeline_v3_runner.py` 的实现作为标准示例。