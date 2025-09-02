#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接注册Pipeline示例（不通过API）
"""

from pipeline_registry import get_pipeline_registry
from story_pipeline_v3_runner import StoryPipelineV3Runner
import json

def register_story_pipeline_direct():
    """直接注册故事生成Pipeline到数据库"""
    
    # 获取Pipeline注册表实例
    registry = get_pipeline_registry()
    
    # 定义Pipeline配置模式
    config_schema = {
        "video_id": "string",           # YouTube视频ID（必需）
        "image_library": "string",      # 图库名称（可选）
        "image_duration": "integer",    # 单个图片持续时长（可选）
        "gender": "integer",            # 语音性别（可选）
        "duration": "integer"           # 总时长（可选）
    }
    
    # 注册Pipeline
    success = registry.register_pipeline(
        pipeline_id="youtube_story_v3",
        pipeline_name="YouTube故事生成V3（图库增强版）",
        pipeline_type="content_generation",
        pipeline_class="story_pipeline_v3_runner.StoryPipelineV3Runner",
        config_schema=config_schema,
        supported_platforms=["youtube", "bilibili"],
        version="3.0.0",
        metadata={
            "description": "基于YouTube视频生成故事内容，支持自定义图库和图片时长",
            "author": "Auto-Publish System",
            "features": [
                "自动提取视频字幕",
                "AI故事改写",
                "多图库支持",
                "可调节图片时长",
                "语音合成",
                "自动配乐"
            ],
            "default_config": {
                "image_library": "default",
                "image_duration": 5,
                "gender": 1,
                "duration": 120
            }
        }
    )
    
    if success:
        print("✅ Pipeline注册成功！")
        
        # 获取注册的Pipeline信息
        pipeline = registry.get_pipeline("youtube_story_v3")
        if pipeline:
            print("\n注册的Pipeline信息:")
            print(f"ID: {pipeline.pipeline_id}")
            print(f"名称: {pipeline.pipeline_name}")
            print(f"类型: {pipeline.pipeline_type}")
            print(f"类: {pipeline.pipeline_class}")
            print(f"版本: {pipeline.version}")
            print(f"支持平台: {', '.join(pipeline.supported_platforms)}")
            print(f"配置模式: {json.dumps(pipeline.config_schema, indent=2, ensure_ascii=False)}")
            if pipeline.metadata:
                print(f"元数据: {json.dumps(pipeline.metadata, indent=2, ensure_ascii=False)}")
    else:
        print("❌ Pipeline注册失败")
    
    return success

def test_create_instance():
    """测试创建Pipeline实例"""
    
    print("\n" + "="*50)
    print("测试创建Pipeline实例")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    # 配置1：基础配置
    config1 = {
        "video_id": "dQw4w9WgXcQ"
    }
    
    print("\n1. 创建基础配置实例:")
    print(json.dumps(config1, indent=2, ensure_ascii=False))
    
    instance1 = registry.create_instance("youtube_story_v3", config1)
    if instance1:
        print("✅ 实例创建成功")
        print(f"   类型: {type(instance1).__name__}")
    else:
        print("❌ 实例创建失败")
    
    # 配置2：自定义图库配置
    config2 = {
        "video_id": "dQw4w9WgXcQ",
        "image_library": "nature",     # 自然风景图库
        "image_duration": 7,           # 每张图片7秒
        "duration": 180,              # 总时长3分钟
        "gender": 2                    # 女声
    }
    
    print("\n2. 创建自定义图库配置实例:")
    print(json.dumps(config2, indent=2, ensure_ascii=False))
    
    instance2 = registry.create_instance("youtube_story_v3", config2)
    if instance2:
        print("✅ 实例创建成功")
        print(f"   类型: {type(instance2).__name__}")
        
        # 测试执行
        print("\n测试执行Pipeline...")
        try:
            result = instance2.execute({
                "video_id": config2["video_id"],
                "account_id": "test_account"
            })
            print(f"执行结果: {result}")
        except Exception as e:
            print(f"执行出错: {e}")
    else:
        print("❌ 实例创建失败")

def list_all_pipelines():
    """列出所有已注册的Pipeline"""
    
    print("\n" + "="*50)
    print("所有已注册的Pipeline")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    # 列出所有Pipeline
    pipelines = registry.list_pipelines()
    
    print(f"\n共找到 {len(pipelines)} 个Pipeline:")
    
    for p in pipelines:
        print(f"\n{'='*30}")
        print(f"ID: {p.pipeline_id}")
        print(f"名称: {p.pipeline_name}")
        print(f"类型: {p.pipeline_type}")
        print(f"状态: {p.status}")
        print(f"版本: {p.version}")
        print(f"支持平台: {', '.join(p.supported_platforms)}")
        
    # 按类型分组
    print("\n按类型分组:")
    types = {}
    for p in pipelines:
        if p.pipeline_type not in types:
            types[p.pipeline_type] = []
        types[p.pipeline_type].append(p.pipeline_name)
    
    for t, names in types.items():
        print(f"\n{t}:")
        for name in names:
            print(f"  - {name}")

def update_pipeline_status():
    """更新Pipeline状态示例"""
    
    print("\n" + "="*50)
    print("更新Pipeline状态")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    # 更新状态为测试中
    success = registry.update_pipeline_status("youtube_story_v3", "testing")
    if success:
        print("✅ 状态更新为: testing")
    
    # 更新回活跃状态
    success = registry.update_pipeline_status("youtube_story_v3", "active")
    if success:
        print("✅ 状态更新为: active")

def get_supported_platforms():
    """获取Pipeline支持的平台"""
    
    print("\n" + "="*50)
    print("获取Pipeline支持的平台")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    platforms = registry.get_supported_platforms("youtube_story_v3")
    if platforms:
        print(f"youtube_story_v3 支持的平台: {', '.join(platforms)}")
    else:
        print("未找到Pipeline或平台信息")

if __name__ == "__main__":
    print("Pipeline直接注册示例")
    print("="*50)
    
    # 1. 注册Pipeline
    print("\n步骤1: 注册Pipeline")
    register_story_pipeline_direct()
    
    # 2. 列出所有Pipeline
    print("\n步骤2: 列出所有Pipeline")
    list_all_pipelines()
    
    # 3. 测试创建实例
    print("\n步骤3: 测试创建实例")
    test_create_instance()
    
    # 4. 获取支持的平台
    print("\n步骤4: 获取支持的平台")
    get_supported_platforms()
    
    # 5. 更新状态（可选）
    # print("\n步骤5: 更新Pipeline状态")
    # update_pipeline_status()
    
    print("\n" + "="*50)
    print("完成！")
    print("\n图库配置说明:")
    print("- image_library: 图库名称，如 'default', 'nature', 'cartoon', 'abstract'")
    print("- image_duration: 单个图片持续时长（秒），建议3-10秒")
    print("  * 3-4秒: 快节奏，适合短视频")
    print("  * 5-7秒: 标准节奏，适合大多数内容")
    print("  * 8-10秒: 慢节奏，适合深度内容")
    print("\n注意：实际的图库需要在系统中配置相应的图片资源")