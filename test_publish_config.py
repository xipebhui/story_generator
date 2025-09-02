#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布配置管理功能
"""

import json
import requests
import time
from datetime import datetime

API_BASE = "http://localhost:51082"
API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_publish_config():
    """测试发布配置管理的完整流程"""
    
    print("=" * 60)
    print("发布配置管理功能测试")
    print("=" * 60)
    
    # 1. 创建发布配置
    print("\n1. 创建发布配置...")
    config_data = {
        "config_name": "测试视频定时发布",
        "group_id": "default_group",
        "pipeline_id": "story_v3",
        "trigger_type": "scheduled",
        "trigger_config": {
            "schedule_type": "daily",
            "time": "10:00",
            "timezone": "Asia/Shanghai"
        },
        "strategy_id": None,
        "priority": 80
    }
    
    response = requests.post(
        f"{API_BASE}/api/auto-publish/publish-configs",
        headers=headers,
        json=config_data
    )
    
    if response.status_code == 200:
        created_config = response.json()
        config_id = created_config["config_id"]
        print(f"   ✅ 配置创建成功！")
        print(f"   配置ID: {config_id}")
        print(f"   配置名称: {created_config['config_name']}")
        print(f"   原始响应: {json.dumps(created_config, indent=2, ensure_ascii=False)}")
    else:
        print(f"   ❌ 创建失败: {response.json()}")
        return
    
    # 2. 获取配置列表
    print("\n2. 获取配置列表...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/publish-configs",
        headers=headers
    )
    
    if response.status_code == 200:
        configs = response.json()["configs"]
        print(f"   ✅ 获取成功！共有 {len(configs)} 个配置")
        for cfg in configs[:3]:  # 只显示前3个
            print(f"   - {cfg['config_name']} ({cfg['trigger_type']}) - {'启用' if cfg['is_active'] else '禁用'}")
    else:
        print(f"   ❌ 获取失败: {response.json()}")
    
    # 3. 获取单个配置详情
    print(f"\n3. 获取配置详情 ({config_id})...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        config = response.json()
        print(f"   ✅ 获取成功！")
        print(f"   配置名称: {config['config_name']}")
        print(f"   Pipeline: {config['pipeline_id']}")
        print(f"   触发方式: {config['trigger_type']}")
        print(f"   优先级: {config['priority']}")
        print(f"   状态: {'启用' if config['is_active'] else '禁用'}")
    else:
        print(f"   ❌ 获取失败: {response.json()}")
    
    # 4. 更新配置
    print("\n4. 更新配置...")
    update_data = {
        "config_name": "更新后的视频发布配置",
        "group_id": "default_group",
        "pipeline_id": "story_v3",
        "trigger_type": "scheduled",
        "trigger_config": {
            "schedule_type": "weekly",
            "days": [1, 3, 5],  # 周一、周三、周五
            "time": "14:00",
            "timezone": "Asia/Shanghai"
        },
        "strategy_id": "round_robin",
        "priority": 90
    }
    
    response = requests.put(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}",
        headers=headers,
        json=update_data
    )
    
    if response.status_code == 200:
        updated_config = response.json()
        print(f"   ✅ 更新成功！")
        print(f"   新名称: {updated_config['config_name']}")
        print(f"   新优先级: {updated_config['priority']}")
    else:
        print(f"   ❌ 更新失败: {response.json()}")
    
    # 5. 切换配置状态
    print("\n5. 切换配置状态...")
    response = requests.patch(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}/toggle",
        headers=headers
    )
    
    if response.status_code == 200:
        toggled_config = response.json()
        print(f"   ✅ 状态切换成功！")
        print(f"   当前状态: {'启用' if toggled_config['is_active'] else '禁用'}")
    else:
        print(f"   ❌ 切换失败: {response.json()}")
    
    # 6. 获取配置关联的任务
    print(f"\n6. 获取配置关联的任务...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}/tasks",
        headers=headers,
        params={"limit": 5}
    )
    
    if response.status_code == 200:
        result = response.json()
        tasks = result.get("tasks", [])
        print(f"   ✅ 获取成功！共有 {len(tasks)} 个任务")
        if tasks:
            for task in tasks[:3]:
                print(f"   - 任务 {task['task_id']}: {task['status']} ({task['account_name']})")
        else:
            print("   暂无执行任务")
    else:
        print(f"   ❌ 获取失败: {response.json()}")
    
    # 7. 获取配置统计
    print(f"\n7. 获取配置统计...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}/stats",
        headers=headers,
        params={"period": "week"}
    )
    
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ 获取成功！")
        print(f"   总任务数: {stats['total_tasks']}")
        print(f"   成功数: {stats['success_count']}")
        print(f"   失败数: {stats['failed_count']}")
        print(f"   成功率: {stats['success_rate']}%")
        print(f"   平均耗时: {stats['avg_duration']}秒")
    else:
        print(f"   ❌ 获取失败: {response.json()}")
    
    # 8. 测试搜索和筛选
    print("\n8. 测试搜索和筛选...")
    response = requests.get(
        f"{API_BASE}/api/auto-publish/publish-configs",
        headers=headers,
        params={
            "search": "视频",
            "is_active": True
        }
    )
    
    if response.status_code == 200:
        configs = response.json()["configs"]
        print(f"   ✅ 搜索成功！找到 {len(configs)} 个匹配的配置")
    else:
        print(f"   ❌ 搜索失败: {response.json()}")
    
    # 9. 删除配置（可选）
    print(f"\n9. 删除测试配置 ({config_id})...")
    response = requests.delete(
        f"{API_BASE}/api/auto-publish/publish-configs/{config_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"   ✅ 删除成功！")
    else:
        print(f"   ❌ 删除失败: {response.json()}")
    
    print("\n" + "=" * 60)
    print("✅ 发布配置管理功能测试完成！")
    print("=" * 60)
    
    print("\n提示:")
    print("1. 访问 http://localhost:51083/auto-publish?tab=configs 查看发布配置管理界面")
    print("2. 可以在界面上创建、编辑、删除配置")
    print("3. 支持定时触发、手动触发、事件触发等多种方式")
    print("4. 支持查看配置的执行统计和任务历史")

if __name__ == "__main__":
    test_publish_config()