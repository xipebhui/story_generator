#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V3 Pipeline 测试脚本
用于快速测试新的Pipeline功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from story_pipeline_v3_runner import StoryPipelineV3Runner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def test_pipeline(video_id: str, creator_name: str = "test"):
    """测试V3 Pipeline"""
    
    print("\n" + "="*60)
    print("🧪 V3 Pipeline 测试")
    print("="*60)
    print(f"视频ID: {video_id}")
    print(f"创作者: {creator_name}")
    print("="*60 + "\n")
    
    try:
        # 创建运行器
        runner = StoryPipelineV3Runner()
        
        # 运行Pipeline
        success = runner.run(
            video_id=video_id,
            creator_name=creator_name
        )
        
        if success:
            print("\n✅ 测试成功!")
            
            # 显示输出文件
            output_dir = Path("story_result") / creator_name / video_id / "final"
            if output_dir.exists():
                print("\n📁 输出文件:")
                for file in output_dir.iterdir():
                    print(f"  - {file.name} ({file.stat().st_size} bytes)")
            
            return True
        else:
            print("\n❌ 测试失败!")
            return False
            
    except Exception as e:
        print(f"\n💥 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='测试V3 Pipeline',
        epilog='示例: python test_v3_pipeline.py YOUR_VIDEO_ID'
    )
    
    parser.add_argument(
        'video_id',
        nargs='?',
        default='dQw4w9WgXcQ',  # 默认测试视频
        help='YouTube视频ID (默认: 测试视频)'
    )
    
    parser.add_argument(
        '--creator',
        default='test',
        help='创作者名称 (默认: test)'
    )
    
    args = parser.parse_args()
    
    # 运行测试
    success = test_pipeline(args.video_id, args.creator)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()