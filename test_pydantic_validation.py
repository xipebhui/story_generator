#!/usr/bin/env python3
"""测试 Pydantic 校验日志"""

import requests
import json

# API 基础URL
BASE_URL = "http://localhost:51082"

# 测试数据 - 故意包含一些错误的字段来触发校验
test_configs = [
    {
        "name": "测试1 - 缺少必填字段",
        "data": {
            "config_name": "测试配置1",
            # 缺少 group_id, pipeline_id, trigger_type, trigger_config
        }
    },
    {
        "name": "测试2 - 无效的触发类型",
        "data": {
            "config_name": "测试配置2",
            "group_id": "group_001",
            "pipeline_id": "pipeline_001",
            "trigger_type": "invalid_type",  # 无效的触发类型
            "trigger_config": {}
        }
    },
    {
        "name": "测试3 - 优先级超出范围",
        "data": {
            "config_name": "测试配置3",
            "group_id": "group_001",
            "pipeline_id": "pipeline_001",
            "trigger_type": "manual",
            "trigger_config": {},
            "priority": 150  # 超出0-100范围
        }
    },
    {
        "name": "测试4 - pipeline_params是无效的JSON字符串",
        "data": {
            "config_name": "测试配置4",
            "group_id": "group_001",
            "pipeline_id": "pipeline_001",
            "trigger_type": "manual",
            "trigger_config": {},
            "pipeline_params": "{'invalid': 'json'}"  # 无效的JSON
        }
    },
    {
        "name": "测试5 - 正确的配置",
        "data": {
            "config_name": "测试配置5",
            "group_id": "group_001",
            "pipeline_id": "reddit_to_video",
            "trigger_type": "manual",
            "trigger_config": {},
            "pipeline_params": {"video_id": "test_123"},
            "priority": 50
        }
    }
]

def test_validation():
    """测试 Pydantic 校验"""
    print("=" * 60)
    print("开始测试 Pydantic 校验日志")
    print("=" * 60)
    
    # 获取 token（如果需要认证）
    headers = {
        "Content-Type": "application/json"
    }
    
    # 如果需要认证，添加 token
    # headers["Authorization"] = "Bearer your_token_here"
    
    for test in test_configs:
        print(f"\n测试: {test['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auto-publish/publish-configs",
                json=test["data"],
                headers=headers
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 422:
                print("校验失败（预期）:")
                errors = response.json()
                print(json.dumps(errors, indent=2, ensure_ascii=False))
            elif response.status_code == 200 or response.status_code == 201:
                print("校验成功:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            else:
                print(f"其他错误: {response.text}")
                
        except Exception as e:
            print(f"请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成 - 请查看日志文件以查看详细的校验日志")
    print("日志文件: ./logs/app.log")
    print("=" * 60)

if __name__ == "__main__":
    test_validation()