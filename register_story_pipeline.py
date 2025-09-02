#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册YouTube故事生成Pipeline示例
"""

import requests
import json
from datetime import datetime

# API配置
API_URL = "http://localhost:51082"
API_KEY = "your_api_key_here"  # 替换为你的API密钥

def register_story_pipeline():
    """注册故事生成Pipeline"""
    
    # Pipeline注册信息
    pipeline_data = {
        "pipeline_id": "youtube_story_v3",
        "pipeline_name": "YouTube故事生成V3",
        "pipeline_type": "content_generation",
        "pipeline_class": "story_pipeline_v3_runner.StoryPipelineV3Runner",
        "config_schema": {
            "video_id": {
                "type": "string",
                "description": "YouTube视频ID",
                "required": True
            },
            "image_library": {
                "type": "string", 
                "description": "图库名称",
                "default": "default",
                "required": False
            },
            "image_duration": {
                "type": "integer",
                "description": "单个图片持续时长(秒)",
                "default": 5,
                "minimum": 3,
                "maximum": 10,
                "required": False
            },
            "gender": {
                "type": "integer",
                "description": "语音性别 (1=男性, 2=女性)",
                "default": 1,
                "required": False
            },
            "duration": {
                "type": "integer",
                "description": "故事总时长(秒)",
                "default": 120,
                "minimum": 60,
                "maximum": 600,
                "required": False
            }
        },
        "supported_platforms": ["youtube", "bilibili"],
        "version": "3.0.0"
    }
    
    # 发送注册请求
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/auto-publish/pipelines/register",
            json=pipeline_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Pipeline注册成功！")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        else:
            print(f"❌ 注册失败: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def create_pipeline_instance_example():
    """创建Pipeline实例的示例"""
    
    print("\n" + "="*50)
    print("Pipeline使用示例")
    print("="*50)
    
    # 示例1：使用默认参数
    config1 = {
        "video_id": "dQw4w9WgXcQ"
    }
    print("\n1. 使用默认参数:")
    print(json.dumps(config1, indent=2, ensure_ascii=False))
    
    # 示例2：自定义图库和时长
    config2 = {
        "video_id": "dQw4w9WgXcQ",
        "image_library": "nature",  # 使用自然风景图库
        "image_duration": 7,        # 每张图片显示7秒
        "duration": 300,           # 总时长5分钟
        "gender": 2                # 使用女声
    }
    print("\n2. 自定义图库和时长:")
    print(json.dumps(config2, indent=2, ensure_ascii=False))
    
    # 示例3：快节奏短视频
    config3 = {
        "video_id": "dQw4w9WgXcQ",
        "image_library": "cartoon",  # 使用卡通图库
        "image_duration": 3,         # 每张图片显示3秒（快节奏）
        "duration": 60,             # 总时长1分钟
        "gender": 1                 # 使用男声
    }
    print("\n3. 快节奏短视频:")
    print(json.dumps(config3, indent=2, ensure_ascii=False))

def test_pipeline_execution():
    """测试Pipeline执行"""
    
    print("\n" + "="*50)
    print("测试Pipeline执行")
    print("="*50)
    
    # 创建执行任务
    task_data = {
        "config_id": "test_config_001",
        "group_id": "default_group",
        "account_id": "yt_001_novel",
        "pipeline_id": "youtube_story_v3",
        "pipeline_config": {
            "video_id": "dQw4w9WgXcQ",
            "image_library": "nature",
            "image_duration": 5,
            "duration": 120,
            "gender": 1
        }
    }
    
    print("\n执行任务配置:")
    print(json.dumps(task_data, indent=2, ensure_ascii=False))
    
    # 这里可以调用执行API
    # response = requests.post(f"{API_URL}/api/auto-publish/tasks/create", ...)

def list_registered_pipelines():
    """列出已注册的Pipeline"""
    
    print("\n" + "="*50)
    print("查询已注册的Pipeline")
    print("="*50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{API_URL}/api/auto-publish/pipelines",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            pipelines = result.get('pipelines', [])
            
            print(f"\n找到 {len(pipelines)} 个已注册的Pipeline:")
            for p in pipelines:
                print(f"\n- ID: {p['pipeline_id']}")
                print(f"  名称: {p['pipeline_name']}")
                print(f"  类型: {p['pipeline_type']}")
                print(f"  版本: {p['version']}")
                print(f"  状态: {p['status']}")
                
            return pipelines
        else:
            print(f"❌ 查询失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

if __name__ == "__main__":
    print("YouTube故事生成Pipeline注册示例")
    print("="*50)
    
    # 1. 注册Pipeline
    print("\n步骤1: 注册Pipeline")
    # register_story_pipeline()  # 取消注释以执行注册
    
    # 2. 查询已注册的Pipeline
    print("\n步骤2: 查询已注册的Pipeline")
    # list_registered_pipelines()  # 取消注释以查询
    
    # 3. 显示使用示例
    create_pipeline_instance_example()
    
    # 4. 测试执行
    test_pipeline_execution()
    
    print("\n" + "="*50)
    print("提示：")
    print("1. 请先确保API服务运行在 http://localhost:51082")
    print("2. 替换 API_KEY 为你的实际密钥")
    print("3. 取消注释相应的函数调用来执行操作")
    print("4. 图库名称可以是: default, nature, cartoon, abstract等")
    print("5. 图片持续时长建议3-10秒，太短会显得急促，太长会显得拖沓")