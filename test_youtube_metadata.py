#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试YouTube元数据生成
"""

import sys
import io
import json
from pathlib import Path

# Fix encoding issue for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_context_v3 import PipelineContextV3
from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
from gemini_client import GeminiClient

def test_youtube_metadata():
    """测试YouTube元数据生成"""
    
    print("="*60)
    print("测试YouTube元数据生成")
    print("="*60)
    
    # 创建测试上下文
    video_id = "aSiVP7rJsqQ"
    context = PipelineContextV3(
        video_id=video_id,
        creator_name="test",
        cache_dir=Path("story_result/test") / video_id
    )
    context.save_intermediate = True  # Enable saving intermediate results
    
    # 加载已有的数据
    try:
        # 加载framework
        framework_file = context.cache_dir / "processing" / "framework_v3.json"
        if framework_file.exists():
            with open(framework_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                context.framework_v3_json = data.get('json', {})
                print(f"✅ 加载framework成功")
        
        # 加载故事
        story_file = context.cache_dir / "final" / "story.txt"
        if story_file.exists():
            with open(story_file, 'r', encoding='utf-8') as f:
                context.final_story = f.read()
                print(f"✅ 加载故事成功，长度: {len(context.final_story)}")
        
        # 加载视频信息
        video_info_file = context.cache_dir / "raw" / "video_info.json"
        if video_info_file.exists():
            with open(video_info_file, 'r', encoding='utf-8') as f:
                context.video_info = json.load(f)
                print(f"✅ 加载视频信息成功")
        
        # 设置segment数量
        parsed_file = context.cache_dir / "processing" / "parsed_segments.json"
        if parsed_file.exists():
            with open(parsed_file, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)
                context.segment_count = parsed_data.get('segment_count', 0)
                print(f"✅ Segment数量: {context.segment_count}")
        
    except Exception as e:
        print(f"❌ 加载数据失败: {e}")
        return False
    
    # 创建Gemini客户端
    gemini_client = GeminiClient(api_key="sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu")
    
    # 创建步骤
    step = GenerateYouTubeMetadataStep(gemini_client)
    
    # 执行
    print("\n开始生成YouTube元数据...")
    result = step.execute(context)
    
    if result.success:
        print(f"✅ 生成成功")
        
        # 检查文件
        metadata_json = context.cache_dir / "final" / "youtube_metadata.json"
        metadata_md = context.cache_dir / "final" / "youtube_metadata.md"
        
        if metadata_json.exists():
            print(f"✅ JSON文件已生成: {metadata_json}")
        else:
            print(f"❌ JSON文件未生成")
        
        if metadata_md.exists():
            print(f"✅ Markdown文件已生成: {metadata_md}")
            # 显示部分内容
            with open(metadata_md, 'r', encoding='utf-8') as f:
                content = f.read()
                print("\n" + "="*60)
                print("生成的内容预览:")
                print("="*60)
                print(content[:1000])
                print("...")
        else:
            print(f"❌ Markdown文件未生成")
    else:
        print(f"❌ 生成失败")
    
    return result.success

if __name__ == "__main__":
    success = test_youtube_metadata()
    sys.exit(0 if success else 1)