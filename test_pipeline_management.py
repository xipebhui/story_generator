#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Pipeline管理功能
"""

import json
from pipeline_registry import get_pipeline_registry

def test_pipeline_management():
    """测试Pipeline管理功能"""
    registry = get_pipeline_registry()
    
    # 1. 注册一个测试Pipeline
    test_pipeline_id = "youtube_story_v3"
    test_pipeline = {
        "pipeline_id": test_pipeline_id,
        "pipeline_name": "YouTube故事生成V3",
        "pipeline_type": "content_generation",
        "pipeline_class": "story_pipeline_v3_runner.StoryPipelineV3",
        "config_schema": {
            "type": "object",
            "properties": {
                "video_id": {
                    "type": "string",
                    "description": "视频ID",
                    "required": True
                },
                "image_library": {
                    "type": "string",
                    "description": "图库名称",
                    "default": "default_library",
                    "required": False
                },
                "duration_per_image": {
                    "type": "number",
                    "description": "单张图片持续时间（秒）",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3,
                    "required": False
                },
                "enable_subtitles": {
                    "type": "boolean",
                    "description": "是否启用字幕",
                    "default": True,
                    "required": False
                }
            },
            "required": ["video_id"]
        },
        "supported_platforms": ["youtube"],
        "version": "1.0.0",
        "metadata": {
            "author": "system",
            "created_date": "2025-01-01",
            "description": "YouTube故事生成Pipeline第三版"
        }
    }
    
    print("1. 注册Pipeline...")
    success = registry.register_pipeline(**test_pipeline)
    if success:
        print(f"   ✅ 成功注册Pipeline: {test_pipeline_id}")
    else:
        print(f"   ⚠️ Pipeline已存在: {test_pipeline_id}")
    
    # 2. 添加更多测试Pipeline
    additional_pipelines = [
        {
            "pipeline_id": "youtube_metadata_v1",
            "pipeline_name": "YouTube元数据生成V1",
            "pipeline_type": "metadata",
            "pipeline_class": "pipeline_steps_youtube_metadata.generate_youtube_metadata",
            "config_schema": {
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "required": True},
                    "target_audience": {"type": "string", "default": "general"}
                },
                "required": ["video_id"]
            },
            "supported_platforms": ["youtube"],
            "version": "1.0.0"
        },
        {
            "pipeline_id": "youtube_postprocess_v1",
            "pipeline_name": "YouTube后处理V1",
            "pipeline_type": "processing",
            "pipeline_class": "story_pipeline_v3_runner.StoryPipelineV3",  # 使用存在的类
            "config_schema": {
                "type": "object",
                "properties": {
                    "video_path": {"type": "string", "required": True},
                    "optimize_quality": {"type": "boolean", "default": True}
                },
                "required": ["video_path"]
            },
            "supported_platforms": ["youtube"],
            "version": "1.0.0"
        }
    ]
    
    for pipeline in additional_pipelines:
        success = registry.register_pipeline(**pipeline)
        if success:
            print(f"   ✅ 成功注册Pipeline: {pipeline['pipeline_id']}")
        else:
            print(f"   ⚠️ Pipeline已存在: {pipeline['pipeline_id']}")
    
    # 3. 列出所有Pipeline
    print("\n2. 列出所有活跃的Pipeline...")
    pipelines = registry.list_pipelines(status="active")
    print(f"   找到 {len(pipelines)} 个活跃的Pipeline:")
    for p in pipelines:
        print(f"   - {p.pipeline_id}: {p.pipeline_name} ({p.pipeline_type})")
    
    # 4. 获取单个Pipeline详情
    print(f"\n3. 获取Pipeline详情: {test_pipeline_id}")
    pipeline = registry.get_pipeline(test_pipeline_id)
    if pipeline:
        print(f"   名称: {pipeline.pipeline_name}")
        print(f"   类型: {pipeline.pipeline_type}")
        print(f"   版本: {pipeline.version}")
        print(f"   状态: {pipeline.status}")
        print(f"   支持平台: {pipeline.supported_platforms}")
    
    # 5. 更新Pipeline
    print(f"\n4. 更新Pipeline: {test_pipeline_id}")
    update_data = {
        "version": "1.0.1",
        "metadata": {
            "author": "system",
            "updated_date": "2025-01-02",
            "description": "YouTube故事生成Pipeline第三版 - 更新版"
        }
    }
    success = registry.update_pipeline(test_pipeline_id, update_data)
    if success:
        print("   ✅ 成功更新Pipeline")
    
    print("\n✅ Pipeline管理功能测试完成!")
    print("   请访问 http://localhost:51083/auto-publish?tab=pipeline 查看Pipeline管理界面")

if __name__ == "__main__":
    test_pipeline_management()