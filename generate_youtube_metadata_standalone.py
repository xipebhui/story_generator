#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立运行YouTube元数据生成
用于为已经生成的故事补充YouTube元数据
"""

import sys
import json
import logging
from pathlib import Path
import argparse

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_context_v3 import PipelineContextV3
from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
from gemini_client import GeminiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_youtube_metadata(video_id: str, creator_name: str = "test"):
    """
    为已有的故事生成YouTube元数据
    
    Args:
        video_id: 视频ID
        creator_name: 创作者名称
    """
    
    logger.info(f"🎬 为视频 {video_id} 生成YouTube元数据")
    
    # 创建上下文
    context = PipelineContextV3(
        video_id=video_id,
        creator_name=creator_name,
        cache_dir=Path("story_result") / creator_name / video_id
    )
    
    # 检查必要文件是否存在
    if not context.cache_dir.exists():
        logger.error(f"❌ 目录不存在: {context.cache_dir}")
        return False
    
    # 加载已有数据
    try:
        # 1. 加载framework
        framework_file = context.cache_dir / "processing" / "framework_v3.json"
        if framework_file.exists():
            with open(framework_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                context.framework_v3_json = data.get('json', {})
                logger.info(f"✅ 加载framework成功")
        else:
            logger.error(f"❌ Framework文件不存在: {framework_file}")
            return False
        
        # 2. 加载最终故事
        story_file = context.cache_dir / "final" / "story.txt"
        if story_file.exists():
            with open(story_file, 'r', encoding='utf-8') as f:
                context.final_story = f.read()
                logger.info(f"✅ 加载故事成功，长度: {len(context.final_story)} 字符")
        else:
            logger.warning(f"⚠️ 故事文件不存在: {story_file}")
        
        # 3. 加载视频信息
        video_info_file = context.cache_dir / "raw" / "video_info.json"
        if video_info_file.exists():
            with open(video_info_file, 'r', encoding='utf-8') as f:
                context.video_info = json.load(f)
                logger.info(f"✅ 加载视频信息: {context.video_info.get('title', 'N/A')}")
        
        # 4. 加载segment信息
        parsed_file = context.cache_dir / "processing" / "parsed_segments.json"
        if parsed_file.exists():
            with open(parsed_file, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)
                context.segment_count = parsed_data.get('segment_count', 0)
                context.segment_tasks = parsed_data.get('segment_tasks', [])
                logger.info(f"✅ Segment数量: {context.segment_count}")
        
    except Exception as e:
        logger.error(f"❌ 加载数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 创建Gemini客户端
    api_key = "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu"
    gemini_client = GeminiClient(api_key=api_key)
    
    # 创建并执行步骤
    logger.info("🤖 开始生成YouTube元数据...")
    step = GenerateYouTubeMetadataStep(gemini_client)
    result = step.execute(context)
    
    if result.success:
        logger.info("✅ YouTube元数据生成成功")
        
        # 验证文件
        metadata_json = context.cache_dir / "final" / "youtube_metadata.json"
        metadata_md = context.cache_dir / "final" / "youtube_metadata.md"
        
        if metadata_json.exists():
            logger.info(f"📁 JSON文件: {metadata_json}")
            
            # 显示部分内容
            with open(metadata_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print("\n" + "="*60)
                print("生成的标题建议:")
                print("="*60)
                
                # 中文标题
                if 'titles' in data and 'chinese' in data['titles']:
                    print("\n中文标题:")
                    for i, title in enumerate(data['titles']['chinese'], 1):
                        print(f"  {i}. {title}")
                
                # 英文标题
                if 'titles' in data and 'english' in data['titles']:
                    print("\n英文标题:")
                    for i, title in enumerate(data['titles']['english'], 1):
                        print(f"  {i}. {title}")
        
        if metadata_md.exists():
            logger.info(f"📁 Markdown文件: {metadata_md}")
            print("\n" + "="*60)
            print(f"完整的YouTube发布建议已保存到:")
            print(f"  {metadata_md}")
            print("="*60)
        
        return True
    else:
        logger.error("❌ YouTube元数据生成失败")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='为已生成的故事添加YouTube元数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_youtube_metadata_standalone.py aSiVP7rJsqQ
  python generate_youtube_metadata_standalone.py VIDEO_ID --creator myname
        """
    )
    
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('--creator', default='test', help='创作者名称（默认: test）')
    
    args = parser.parse_args()
    
    # 执行生成
    success = generate_youtube_metadata(args.video_id, args.creator)
    
    if success:
        print("\n✅ YouTube元数据生成完成!")
    else:
        print("\n❌ 生成失败，请检查日志")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()