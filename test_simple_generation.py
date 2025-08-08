#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试简化版故事生成流程
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from youtube_story_creator_v2 import YouTubeStoryCreatorV2

def test_framework_parsing():
    """测试框架解析功能"""
    print("=" * 80)
    print("测试框架解析功能")
    print("=" * 80)
    
    # 创建实例
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        target_length=30000
    )
    
    # 测试框架文本（模拟新格式）
    test_framework = """
# 测试故事 - 故事蓝图与争议策略

## A. 改编策略总览
- **目标受众：** 年轻成年人
- **核心改编理念：** 将平淡的日常故事改编为充满争议的情感大戏
- **"槽点"放大策略：**
    - **识别出的核心槽点：** 主角过于圣母，总是牺牲自己
    - **放大方案：** 让主角的圣母心在关键时刻造成灾难性后果

## B. 故事蓝图 (9步上瘾结构)

- **1. 钩子开场 (Hook)：**
    - **情节规划：** 主角因为救助陌生人而错过重要面试
    - **节奏与字数：** 快节奏，悬念丛生。约 700 字。

- **2. 角色与动机 (Setup)：**
    - **情节规划：** 展现主角的圣母性格如何形成
    - **节奏与字数：** 中等节奏，人物刻画。约 1000 字。

## C. 核心角色视觉设计
- **角色1：[艾拉]**
  - **身份定位：** 主角
  - **性别/年龄感/体型等：** 女性，25岁，瘦弱
  - **"槽点"的视觉表现：** 总是带着伪善的微笑
"""
    
    # 测试提取框架摘要
    print("\n1. 测试 extract_framework_summary:")
    summary = creator.extract_framework_summary(test_framework)
    print(summary)
    
    # 测试解析9步结构
    print("\n2. 测试 parse_nine_steps:")
    nine_steps = creator.parse_nine_steps(test_framework)
    for step, content in nine_steps.items():
        print(f"  - {step}: {content}")
    
    # 测试片段任务映射
    print("\n3. 测试 extract_segment_tasks:")
    tasks = creator.extract_segment_tasks(test_framework)
    # 只显示前3个片段
    for i in range(1, 4):
        if i in tasks:
            print(f"  片段{i}: {tasks[i]}")
    
    print("\n[OK] 框架解析测试完成")

def test_input_building():
    """测试输入构建功能"""
    print("\n" + "=" * 80)
    print("测试输入构建功能")
    print("=" * 80)
    
    # 创建实例
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        target_length=30000
    )
    
    # 测试数据
    framework_summary = "- **核心改编理念：** 测试理念\n- **槽点策略：** 放大圣母心"
    previous_text = "这是上一段的结尾，主角正在思考人生的意义..."
    segment_task = {
        'chapter': '钩子开场',
        'task': '展现主角的圣母心导致的第一个灾难',
        'rhythm': '快节奏，悬念丛生。约700字'
    }
    
    # 构建输入
    input_text = creator.build_segment_input_simple(
        segment_num=1,
        framework_summary=framework_summary,
        previous_text="",  # 第一段没有前文
        segment_task=segment_task
    )
    
    print("\n构建的输入文本（前500字）:")
    print(input_text[:500])
    print("...")
    print(f"\n总长度: {len(input_text)} 字符")
    
    print("\n[OK] 输入构建测试完成")

def main():
    """主测试函数"""
    print("开始测试简化版故事生成流程")
    
    # 运行测试
    test_framework_parsing()
    test_input_building()
    
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)
    
    print("\n提示：")
    print("1. 新的简化版本使用 phase3_generate_segments_simple")
    print("2. 每个片段都是独立的API调用，只传递前500字")
    print("3. 框架摘要只在开始时提取一次")
    print("4. 完全手动控制上下文，便于调试")

if __name__ == "__main__":
    main()