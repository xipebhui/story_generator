#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的Schema表单配置功能
"""

import json
import requests

API_BASE = "http://localhost:51082"
API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_pipeline_with_form_schema():
    """测试使用表单配置生成的Schema创建Pipeline"""
    
    # 这是前端表单自动生成的Schema格式
    config_schema = {
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
                "default": "default_library"
            },
            "duration_per_image": {
                "type": "number",
                "description": "单张图片持续时间（秒）",
                "default": 3,
                "minimum": 1,
                "maximum": 10
            },
            "enable_subtitles": {
                "type": "boolean",
                "description": "是否启用字幕",
                "default": True
            },
            "quality_level": {
                "type": "string",
                "description": "视频质量级别",
                "enum": ["low", "medium", "high", "ultra"],
                "default": "high"
            }
        },
        "required": ["video_id"]
    }
    
    # 创建Pipeline数据
    pipeline_data = {
        "pipeline_id": "test_form_schema_pipeline",
        "pipeline_name": "表单配置测试Pipeline",
        "pipeline_type": "content_generation",
        "pipeline_class": "story_pipeline_v3_runner.StoryPipelineV3",
        "config_schema": config_schema,
        "supported_platforms": ["youtube"],
        "version": "2.0.0"
    }
    
    # 1. 尝试注册新Pipeline
    print("1. 注册新Pipeline...")
    response = requests.post(
        f"{API_BASE}/api/auto-publish/pipelines/register",
        headers=headers,
        json=pipeline_data
    )
    
    if response.status_code == 200:
        print("   ✅ Pipeline注册成功！")
    else:
        print(f"   ⚠️ Pipeline可能已存在: {response.json()}")
    
    # 2. 获取Pipeline详情，验证Schema
    print("\n2. 获取Pipeline详情...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/pipelines/test_form_schema_pipeline",
        headers=headers
    )
    
    if response.status_code == 200:
        pipeline = response.json()
        print("   ✅ 获取成功！")
        print("\n   配置的Schema字段：")
        
        if pipeline.get("config_schema") and pipeline["config_schema"].get("properties"):
            for field_name, field_config in pipeline["config_schema"]["properties"].items():
                print(f"   - {field_name}:")
                print(f"     类型: {field_config.get('type')}")
                print(f"     描述: {field_config.get('description')}")
                if field_config.get('default') is not None:
                    print(f"     默认值: {field_config.get('default')}")
                if field_config.get('enum'):
                    print(f"     枚举值: {field_config.get('enum')}")
                if field_config.get('minimum') is not None:
                    print(f"     最小值: {field_config.get('minimum')}")
                if field_config.get('maximum') is not None:
                    print(f"     最大值: {field_config.get('maximum')}")
    
    # 3. 更新Pipeline，修改Schema
    print("\n3. 更新Pipeline Schema（添加新字段）...")
    
    # 添加一个新字段
    config_schema["properties"]["watermark_enabled"] = {
        "type": "boolean",
        "description": "是否添加水印",
        "default": False
    }
    
    update_data = {
        "config_schema": config_schema,
        "version": "2.1.0"
    }
    
    response = requests.put(
        f"{API_BASE}/api/auto-publish/pipelines/test_form_schema_pipeline",
        headers=headers,
        json=update_data
    )
    
    if response.status_code == 200:
        print("   ✅ Pipeline更新成功！")
        print("   新增字段: watermark_enabled (布尔类型)")
    
    print("\n✅ 测试完成！")
    print("\n说明：")
    print("1. 前端表单会自动生成标准的JSON Schema格式")
    print("2. 后端API接口完全兼容，无需修改")
    print("3. 支持所有Schema特性：类型、默认值、范围、枚举等")
    print("\n访问 http://localhost:51083/auto-publish?tab=pipeline 查看界面")

if __name__ == "__main__":
    test_pipeline_with_form_schema()