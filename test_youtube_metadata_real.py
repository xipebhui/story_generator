#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际测试 YouTube Metadata 生成功能（调用真实 API）
"""

import json
import sys
import os
from pathlib import Path
import logging

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from config_loader import load_env_file
load_env_file()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_real_metadata_generation():
    """测试真实的 YouTube metadata 生成"""
    
    from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
    from pipeline_context_v3 import PipelineContextV3
    from gemini_client import GeminiClient
    
    print("=" * 60)
    print("实际测试 YouTube Metadata 生成")
    print("=" * 60)
    
    # 1. 创建真实的 Gemini 客户端
    gemini_api_key = os.getenv("NEWAPI_API_KEY")
    if not gemini_api_key:
        gemini_api_key = "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu"
        logger.warning("使用默认API密钥")
    
    gemini_client = GeminiClient(api_key=gemini_api_key)
    print(f"✓ Gemini 客户端已初始化")
    
    # 2. 创建测试上下文
    test_video_id = "test_metadata_simple"
    test_creator = "test_user"
    
    context = PipelineContextV3(
        video_id=test_video_id,
        creator_name=test_creator,
        cache_dir=Path(f"./test_output/{test_creator}/{test_video_id}")
    )
    
    # 3. 设置测试数据 - 使用一个引人入胜的故事示例
    context.save_intermediate = True
    context.framework_v3_json = {
        'adaptationAnalysis': {
            'newStoryTitle': 'The Midnight Phone Call That Changed Everything',
            'coreConcept': 'A mysterious phone call at 3 AM leads to uncovering a decades-old family secret',
            'mainCharacters': ['Emma Thompson', 'Unknown Caller', 'Detective Harris'],
            'openingReplicationStrategy': {
                'hook': 'The phone rang at exactly 3:17 AM, displaying a number that had been disconnected for 20 years'
            }
        }
    }
    
    context.video_info = {
        'title': 'True Crime Story - The Call That Revealed Everything'
    }
    
    # 创建一个测试故事
    context.final_story = """
    The phone rang at exactly 3:17 AM. Emma Thompson jolted awake, her heart pounding. 
    The caller ID displayed a number she knew by heart - her mother's old phone number. 
    The problem was, her mother had been dead for twenty years, and that line had been 
    disconnected the day after the funeral.
    
    "Hello?" Emma's voice trembled as she answered.
    
    The voice on the other end was barely a whisper, but unmistakable. "Emma, I don't 
    have much time. The truth about what happened that night... it's all in the attic. 
    Behind the blue trunk. Please, you need to know..."
    
    The line went dead.
    
    Emma sat frozen in the darkness, her mind racing. That voice - it couldn't be. 
    But she would recognize her mother's voice anywhere. Against every rational thought, 
    she found herself walking toward the stairs leading to the attic, a place she hadn't 
    visited since childhood.
    
    What she discovered there would not only change everything she believed about her 
    mother's death but would also put her own life in danger. The blue trunk contained 
    documents, photographs, and evidence of a conspiracy that reached deeper than she 
    could have ever imagined.
    
    This is the true story of how one impossible phone call led to uncovering one of 
    the most shocking family secrets ever revealed...
    """ * 3  # 重复3次以增加长度
    
    context.segment_count = 7
    
    # 4. 创建并执行 metadata 生成步骤
    print("\n正在生成 YouTube Metadata...")
    metadata_step = GenerateYouTubeMetadataStep(gemini_client)
    
    try:
        result = metadata_step.execute(context)
        
        if result.success and context.youtube_metadata:
            print("\n✅ 生成成功！")
            print("\n" + "=" * 60)
            print("生成的 YouTube Metadata:")
            print("=" * 60)
            
            metadata = context.youtube_metadata
            
            # 格式化输出
            print(f"\n📝 标题 (Title):")
            print(f"   {metadata.get('title', 'N/A')}")
            
            print(f"\n📄 描述 (Description):")
            desc = metadata.get('description', 'N/A')
            if len(desc) > 200:
                print(f"   {desc[:200]}...")
                print(f"   [总长度: {len(desc)} 字符]")
            else:
                print(f"   {desc}")
            
            print(f"\n🏷️ 标签 (Tags) - 共 {len(metadata.get('tags', []))} 个:")
            tags = metadata.get('tags', [])
            print(f"   {', '.join(tags[:10])}")
            if len(tags) > 10:
                print(f"   ... 还有 {len(tags) - 10} 个标签")
            
            print(f"\n🎨 缩略图提示词 (Image Prompt):")
            image_prompt = metadata.get('image_prompt', 'N/A')
            # 查找 ^ 标记的文字
            import re
            text_overlay = re.findall(r'\^([^\^]+)\^', image_prompt)
            if text_overlay:
                print(f"   文字叠加: {text_overlay[0]}")
            print(f"   提示词预览: {image_prompt[:150]}...")
            print(f"   [总长度: {len(image_prompt)} 字符]")
            
            # 保存到文件
            output_file = Path(f"./test_youtube_metadata_result.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 完整结果已保存到: {output_file}")
            
            # 验证结构
            print("\n" + "=" * 60)
            print("结构验证:")
            print("=" * 60)
            
            required_fields = ['title', 'description', 'tags', 'image_prompt']
            all_valid = True
            
            for field in required_fields:
                if field in metadata:
                    field_type = type(metadata[field]).__name__
                    if field == 'tags':
                        expected = 'list'
                        is_valid = isinstance(metadata[field], list)
                    else:
                        expected = 'str'
                        is_valid = isinstance(metadata[field], str)
                    
                    status = "✓" if is_valid else "✗"
                    print(f"  {status} {field}: {field_type} (期望: {expected})")
                    
                    if not is_valid:
                        all_valid = False
                else:
                    print(f"  ✗ {field}: 缺失")
                    all_valid = False
            
            if all_valid:
                print("\n🎉 所有字段验证通过！新的简化结构工作正常。")
            else:
                print("\n⚠️ 部分字段验证失败，请检查。")
            
        else:
            print("\n❌ 生成失败")
            print(f"错误信息: {result.error if hasattr(result, 'error') else '未知错误'}")
            
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试目录
        import shutil
        if Path("./test_output").exists():
            shutil.rmtree("./test_output")
            print("\n已清理测试输出目录")


if __name__ == "__main__":
    test_real_metadata_generation()