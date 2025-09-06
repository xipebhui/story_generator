#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建间隔调度配置示例
通过API正确创建带时间槽的调度配置
"""

import requests
import json
import sys
from datetime import datetime

# API配置
API_BASE_URL = "http://localhost:51082"
API_ENDPOINT = f"{API_BASE_URL}/api/auto-publish/publish-configs"

def create_interval_config(
    config_name: str,
    group_id: str,
    pipeline_id: str,
    interval: int,
    interval_unit: str = "hours",
    priority: int = 50
):
    """创建间隔调度配置"""
    
    config_data = {
        "config_name": config_name,
        "group_id": group_id,
        "pipeline_id": pipeline_id,
        "trigger_type": "scheduled",
        "trigger_config": {
            "schedule_type": "interval",
            "schedule_interval": interval,
            "schedule_interval_unit": interval_unit
        },
        "priority": priority,
        "pipeline_params": {}  # 可以添加Pipeline参数
    }
    
    print(f"\n创建配置: {config_name}")
    print(f"间隔: {interval} {interval_unit}")
    print(f"组ID: {group_id}")
    print(f"Pipeline: {pipeline_id}")
    
    try:
        # 发送请求
        response = requests.post(
            API_ENDPOINT,
            json=config_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 配置创建成功!")
            print(f"  配置ID: {result.get('config_id')}")
            print(f"  触发类型: {result.get('trigger_type')}")
            print(f"  优先级: {result.get('priority')}")
            return result
        else:
            print(f"✗ 创建失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到API服务")
        print("  请确保API服务正在运行: python api_server.py")
        return None
    except Exception as e:
        print(f"✗ 创建失败: {e}")
        return None


def list_configs():
    """列出现有配置"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/auto-publish/publish-configs")
        if response.status_code == 200:
            data = response.json()
            configs = data.get('configs', [])
            
            print("\n现有配置列表:")
            print("-" * 60)
            
            scheduled_configs = [c for c in configs if c['trigger_type'] == 'scheduled']
            manual_configs = [c for c in configs if c['trigger_type'] == 'manual']
            
            if scheduled_configs:
                print("\n定时配置:")
                for config in scheduled_configs:
                    trigger_cfg = config.get('trigger_config', {})
                    schedule_type = trigger_cfg.get('schedule_type', 'unknown')
                    if schedule_type == 'interval':
                        interval = trigger_cfg.get('schedule_interval', 0)
                        unit = trigger_cfg.get('schedule_interval_unit', 'hours')
                        print(f"  - {config['config_name']} (每{interval}{unit})")
                    else:
                        print(f"  - {config['config_name']} ({schedule_type})")
            
            if manual_configs:
                print("\n手动配置:")
                for config in manual_configs:
                    print(f"  - {config['config_name']}")
            
            if not configs:
                print("  没有配置")
                
    except Exception as e:
        print(f"获取配置列表失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("间隔调度配置创建工具")
    print("=" * 60)
    
    # 先列出现有配置
    list_configs()
    
    # 示例配置参数（需要根据实际情况修改）
    print("\n" + "=" * 60)
    print("创建新的间隔调度配置")
    print("=" * 60)
    
    # 这里需要替换为实际的group_id和pipeline_id
    # 可以从数据库查询获取
    
    print("\n示例1: 创建6小时间隔配置")
    create_interval_config(
        config_name=f"6小时自动发布_{datetime.now().strftime('%m%d')}",
        group_id="default_group",  # 需要替换为实际的group_id
        pipeline_id="story_gen_v5",  # 需要替换为实际的pipeline_id
        interval=6,
        interval_unit="hours",
        priority=60
    )
    
    print("\n" + "-" * 40)
    print("\n示例2: 创建30分钟间隔配置（测试用）")
    create_interval_config(
        config_name=f"30分钟测试_{datetime.now().strftime('%H%M')}",
        group_id="default_group",  # 需要替换为实际的group_id
        pipeline_id="story_gen_v5",  # 需要替换为实际的pipeline_id
        interval=30,
        interval_unit="minutes",
        priority=40
    )
    
    print("\n" + "=" * 60)
    print("配置创建完成")
    print("=" * 60)
    print("\n说明:")
    print("1. 配置创建后会自动生成时间槽")
    print("2. account_driven_executor会自动检查并执行到期的槽位")
    print("3. 多个相同间隔的配置会自动错开执行时间")
    print("4. 可以通过API手动触发测试:")
    print("   curl -X POST http://localhost:51082/api/auto-publish/publish-configs/{config_id}/trigger")


if __name__ == "__main__":
    main()