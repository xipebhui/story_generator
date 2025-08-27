#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布历史接口
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from publish_service import get_publish_service
import json
from datetime import datetime

def test_publish_history():
    """测试发布历史接口功能"""
    
    # 获取发布服务实例
    publish_service = get_publish_service(use_mock=False)
    
    print("="*60)
    print("测试发布历史接口")
    print("="*60)
    
    # 获取所有发布历史
    print("\n1. 获取所有发布历史:")
    history = publish_service.get_publish_history(limit=5)
    
    if history:
        print(f"   找到 {len(history)} 条发布记录")
        
        for i, task in enumerate(history, 1):
            print(f"\n   记录 {i}:")
            print(f"     发布ID: {task.get('publish_id')}")
            print(f"     任务ID: {task.get('task_id')}")
            print(f"     账号ID: {task.get('account_id')}")
            print(f"     账号名称: {task.get('account_name')}")  # 新增字段
            print(f"     YouTube频道: {task.get('youtube_channel_name')}")  # 新增字段
            print(f"     视频标题: {task.get('video_title')}")
            print(f"     状态: {task.get('status')}")
            print(f"     YouTube链接: {task.get('youtube_video_url', 'N/A')}")
            print(f"     创建时间: {task.get('created_at')}")
            print(f"     完成时间: {task.get('upload_completed_at', 'N/A')}")  # 新增字段
            
            if task.get('error_message'):
                print(f"     错误信息: {task.get('error_message')}")
    else:
        print("   没有找到发布记录")
    
    # 测试按状态筛选
    print("\n2. 按状态筛选 (status=success):")
    success_history = publish_service.get_publish_history(status='success', limit=3)
    print(f"   找到 {len(success_history)} 条成功的发布记录")
    
    for task in success_history:
        print(f"   - {task.get('account_name')} | {task.get('youtube_channel_name')} | {task.get('youtube_video_url')}")
    
    # 测试按账号筛选
    print("\n3. 按账号筛选 (account_id=bearreddit):")
    account_history = publish_service.get_publish_history(account_id='bearreddit', limit=3)
    print(f"   找到 {len(account_history)} 条该账号的发布记录")
    
    for task in account_history:
        print(f"   - {task.get('video_title')} | {task.get('status')} | {task.get('upload_completed_at', 'N/A')}")
    
    # 显示数据结构示例
    if history:
        print("\n4. 返回数据结构示例 (JSON):")
        example = history[0] if history else {}
        # 只显示关键字段
        simplified = {
            'publish_id': example.get('publish_id'),
            'account_name': example.get('account_name'),
            'youtube_channel_name': example.get('youtube_channel_name'),
            'video_title': example.get('video_title'),
            'status': example.get('status'),
            'youtube_video_url': example.get('youtube_video_url'),
            'upload_completed_at': example.get('upload_completed_at'),
            'created_at': example.get('created_at')
        }
        print(json.dumps(simplified, ensure_ascii=False, indent=2))
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_publish_history()