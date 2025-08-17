#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试YouTube Story Creator V3
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from youtube_story_creator_v3 import YouTubeStoryCreatorV3


def test_v3_creator():
    """测试V3版本"""
    
    # 测试视频ID（可以替换为实际的视频ID）
    video_id = "test_video_id"  # 替换为实际的YouTube视频ID
    
    print("=" * 60)
    print("测试 YouTube Story Creator V3")
    print("=" * 60)
    
    # 创建处理器
    creator = YouTubeStoryCreatorV3(
        video_id=video_id,
        output_dir=f"test_output_v3/{video_id}"
    )
    
    # 运行
    framework = creator.run()
    
    if framework:
        print("\n✅ 测试成功！")
        print(f"输出目录: {creator.output_dir}")
        
        # 如果是JSON格式，打印关键信息
        if isinstance(framework, dict) and 'adaptationAnalysis' in framework:
            analysis = framework['adaptationAnalysis']
            print("\n📊 框架分析结果:")
            print(f"  - 新故事标题: {analysis.get('newStoryTitle', 'N/A')}")
            print(f"  - 核心概念: {analysis.get('coreConcept', 'N/A')}")
            
            # 打印核心体验循环
            if 'coreExperienceLoop' in analysis:
                loop = analysis['coreExperienceLoop']
                print(f"  - 循环模式: {loop.get('loopPattern', 'N/A')}")
                print(f"  - 增强计划: {loop.get('amplificationPlan', 'N/A')}")
            
            # 打印主要角色
            if 'mainCharacters' in analysis:
                print("\n👥 主要角色:")
                for char in analysis['mainCharacters']:
                    print(f"  - {char.get('originalName', 'N/A')} → {char.get('newName', 'N/A')}")
        
        # 如果有故事蓝图
        if isinstance(framework, dict) and 'storyBlueprint' in framework:
            blueprint = framework['storyBlueprint']
            print(f"\n📚 故事蓝图: {len(blueprint)} 个步骤")
            for step in blueprint[:3]:  # 只打印前3步
                print(f"  步骤{step.get('step', 'N/A')}: {step.get('stepTitle', 'N/A')}")
    else:
        print("\n❌ 测试失败")


if __name__ == "__main__":
    # 可以从命令行传入视频ID
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        creator = YouTubeStoryCreatorV3(video_id=video_id)
        creator.run()
    else:
        # 运行测试
        test_v3_creator()