#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布任务创建修复
验证video_tags和video_description字段的处理
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from publish_service import get_publish_service
from database import get_db_manager
import json
import uuid

def test_publish_with_complex_data():
    """测试带有复杂数据的发布任务创建"""
    
    # 获取服务实例
    publish_service = get_publish_service(use_mock=False)
    db = get_db_manager()
    
    print("="*60)
    print("测试发布任务创建 - 复杂数据处理")
    print("="*60)
    
    # 1. 创建一个测试的Pipeline任务
    test_task_id = f"test_complex_{uuid.uuid4().hex[:8]}"
    
    # 模拟复杂的YouTube元数据
    complex_metadata = {
        'title': 'Test Video with Complex Characters',
        'description': """This is a test description with:
        Special characters: & < > " ' \x00
        Emoji: 😀 🎬 
        Very long text that exceeds normal limits...
        """ + "x" * 2000,  # 超长文本
        'tags': {
            'chinese': ['测试', '中文标签'],
            'english': ['test', 'english tag'],
            'mixed': ['混合tag', 'mixed tag', '😀emoji']
        }
    }
    
    # 创建测试Pipeline任务
    pipeline_task_data = {
        'task_id': test_task_id,
        'video_id': 'test_video_123',
        'creator_id': 'test_creator',
        'status': 'completed',
        'video_path': '/test/video.mp4',
        'youtube_metadata': json.dumps(complex_metadata, ensure_ascii=False)
    }
    
    try:
        pipeline_task = db.create_task(pipeline_task_data)
        print(f"\n✅ 创建测试Pipeline任务: {test_task_id}")
    except Exception as e:
        print(f"\n❌ 创建Pipeline任务失败: {e}")
        return
    
    # 2. 测试创建发布任务 - 使用复杂的tags（字典格式）
    print("\n测试1: 使用字典格式的tags")
    try:
        publish_task1 = publish_service.create_publish_task(
            task_id=test_task_id,
            account_id='test_account_001',
            video_tags={
                'chinese': ['中文1', '中文2'],
                'english': ['english1', 'english2'],
                'mixed': ['mix1', 'mix2']
            }
        )
        if publish_task1:
            print(f"  ✅ 成功创建发布任务: {publish_task1['publish_id']}")
            print(f"  Tags: {publish_task1.get('video_tags')}")
        else:
            print("  ❌ 创建失败")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    
    # 3. 测试创建发布任务 - 使用列表格式的tags
    print("\n测试2: 使用列表格式的tags")
    try:
        publish_task2 = publish_service.create_publish_task(
            task_id=test_task_id,
            account_id='test_account_002',
            video_tags=['tag1', 'tag2', '标签3', 'tag with spaces']
        )
        if publish_task2:
            print(f"  ✅ 成功创建发布任务: {publish_task2['publish_id']}")
            print(f"  Tags: {publish_task2.get('video_tags')}")
        else:
            print("  ❌ 创建失败")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    
    # 4. 测试超长description
    print("\n测试3: 使用超长description")
    long_desc = "这是一个超长的描述文本 " * 200  # 创建超长文本
    try:
        publish_task3 = publish_service.create_publish_task(
            task_id=test_task_id,
            account_id='test_account_003',
            video_description=long_desc
        )
        if publish_task3:
            print(f"  ✅ 成功创建发布任务: {publish_task3['publish_id']}")
            desc_len = len(publish_task3.get('video_description', ''))
            print(f"  Description长度: {desc_len} 字符")
            if desc_len <= 1000:
                print(f"  ✅ Description已被正确截断")
        else:
            print("  ❌ 创建失败")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    
    # 5. 测试特殊字符description
    print("\n测试4: 使用特殊字符description")
    special_desc = "Description with special chars: \x00 \r\n < > & \" ' 😀"
    try:
        publish_task4 = publish_service.create_publish_task(
            task_id=test_task_id,
            account_id='test_account_004',
            video_description=special_desc
        )
        if publish_task4:
            print(f"  ✅ 成功创建发布任务: {publish_task4['publish_id']}")
            print(f"  Description: {publish_task4.get('video_description')}")
        else:
            print("  ❌ 创建失败")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    
    # 6. 清理测试数据
    print("\n清理测试数据...")
    with db.get_session() as session:
        # 删除测试发布任务
        from database import PublishTask, PipelineTask
        session.query(PublishTask).filter_by(task_id=test_task_id).delete()
        # 删除测试Pipeline任务
        session.query(PipelineTask).filter_by(task_id=test_task_id).delete()
        session.commit()
        print("  ✅ 测试数据已清理")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_publish_with_complex_data()