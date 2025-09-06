#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复Pipeline的config_schema为标准格式
"""

from pipeline_registry import get_pipeline_registry
import json

def fix_story_v3_schema():
    """修复story_v3的配置模式为标准JSON Schema格式"""
    
    registry = get_pipeline_registry()
    
    # 标准的JSON Schema格式
    proper_schema = {
        "type": "object",
        "properties": {
            "video_id": {
                "type": "string",
                "description": "YouTube视频ID"
            },
            "creator_name": {
                "type": "string", 
                "description": "创作者名称"
            },
            "cache_dir": {
                "type": "string",
                "description": "缓存目录路径"
            },
            "save_intermediate": {
                "type": "integer",
                "description": "是否保存中间结果(0或1)",
                "default": 1
            },
            "image_library": {
                "type": "string",
                "description": "图库名称",
                "default": "default",
                "enum": ["default", "nature", "cartoon", "abstract"]
            },
            "image_duration": {
                "type": "integer",
                "description": "单张图片持续时长(秒)",
                "default": 5,
                "minimum": 3,
                "maximum": 10
            },
            "voice_speed": {
                "type": "number",
                "description": "语音速度",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0
            },
            "gender": {
                "type": "integer",
                "description": "语音性别(0=女声,1=男声)",
                "default": 0,
                "enum": [0, 1]
            },
            "duration": {
                "type": "integer",
                "description": "总时长限制(秒)",
                "minimum": 60,
                "maximum": 600
            }
        },
        "required": ["video_id", "creator_name"]
    }
    
    # 更新Pipeline的配置模式
    success = registry.update_pipeline(
        pipeline_id="story_v3",
        update_data={
            "config_schema": proper_schema
        }
    )
    
    if success:
        print("✅ story_v3 Pipeline配置模式已修复")
        
        # 验证更新
        pipeline = registry.get_pipeline("story_v3")
        if pipeline:
            print("\n更新后的配置模式:")
            print(json.dumps(pipeline.config_schema, indent=2, ensure_ascii=False))
    else:
        print("❌ 更新失败")
    
    return success

def fix_youtube_story_v3_schema():
    """修复youtube_story_v3的配置模式"""
    
    registry = get_pipeline_registry()
    
    # 标准的JSON Schema格式
    proper_schema = {
        "type": "object",
        "properties": {
            "video_id": {
                "type": "string",
                "description": "YouTube视频ID"
            },
            "creator_name": {
                "type": "string",
                "description": "创作者名称"
            },
            "image_library": {
                "type": "string",
                "description": "图库名称",
                "default": "default",
                "enum": ["default", "nature", "cartoon", "abstract"]
            },
            "image_duration": {
                "type": "integer",
                "description": "单张图片持续时长(秒)",
                "default": 5,
                "minimum": 3,
                "maximum": 10
            },
            "gender": {
                "type": "integer",
                "description": "语音性别(0=女声,1=男声)",
                "default": 0,
                "enum": [0, 1]
            },
            "duration": {
                "type": "integer",
                "description": "总时长限制(秒)",
                "minimum": 60,
                "maximum": 600
            }
        },
        "required": ["video_id"]
    }
    
    # 更新Pipeline的配置模式
    success = registry.update_pipeline(
        pipeline_id="youtube_story_v3", 
        update_data={
            "config_schema": proper_schema
        }
    )
    
    if success:
        print("✅ youtube_story_v3 Pipeline配置模式已修复")
        
        # 验证更新
        pipeline = registry.get_pipeline("youtube_story_v3")
        if pipeline:
            print("\n更新后的配置模式:")
            print(json.dumps(pipeline.config_schema, indent=2, ensure_ascii=False))
    else:
        print("❌ 更新失败")
    
    return success

def list_all_schemas():
    """列出所有Pipeline的schema"""
    registry = get_pipeline_registry()
    pipelines = registry.list_pipelines()
    
    print("\n所有Pipeline的配置模式:")
    print("="*50)
    
    for p in pipelines:
        print(f"\nPipeline: {p.pipeline_id} ({p.pipeline_name})")
        print(f"Schema: {json.dumps(p.config_schema, indent=2, ensure_ascii=False)}")
        print("-"*30)

if __name__ == "__main__":
    print("修复Pipeline配置模式")
    print("="*50)
    
    # 先列出当前的schema
    print("\n当前状态:")
    list_all_schemas()
    
    # 修复story_v3
    print("\n修复story_v3:")
    fix_story_v3_schema()
    
    # 修复youtube_story_v3
    print("\n修复youtube_story_v3:")
    fix_youtube_story_v3_schema()
    
    # 再次列出所有schema
    print("\n修复后的状态:")
    list_all_schemas()
    
    print("\n✅ 修复完成!")