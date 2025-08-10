#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
命令行工具：生成故事片段的SD图片提示词
支持单个、批量或全部片段的处理
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from image_prompt_generator import ImagePromptGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='生成故事片段的SD图片提示词',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成单个segment的提示词
  python generate_image_prompts.py --creator test --video Xya-j50aqjM --segment 1
  
  # 生成多个指定segment的提示词
  python generate_image_prompts.py --creator test --video Xya-j50aqjM --segments 1,5,9
  
  # 生成所有segment的提示词
  python generate_image_prompts.py --creator test --video Xya-j50aqjM --all
  
  # 指定每个片段生成2张图片
  python generate_image_prompts.py --creator test --video Xya-j50aqjM --all --images_per_segment 2
        """
    )
    
    # 必需参数
    parser.add_argument('--creator', required=True, help='创作者名称')
    parser.add_argument('--video', required=True, help='视频ID')
    
    # 片段选择（三选一）
    segment_group = parser.add_mutually_exclusive_group(required=True)
    segment_group.add_argument('--segment', type=int, help='单个片段编号')
    segment_group.add_argument('--segments', help='多个片段编号，逗号分隔 (如: 1,5,9)')
    segment_group.add_argument('--all', action='store_true', help='处理所有片段')
    
    # 可选参数
    parser.add_argument('--images_per_segment', type=int, default=1, 
                       help='每个片段生成的图片数量 (默认: 1)')
    parser.add_argument('--generator_type', choices=['sd', 'jimeng'], default='jimeng',
                       help='生成器类型: jimeng(默认) 或 sd')
    parser.add_argument('--art_style', 
                       choices=[
                           '超写实风格', '写实摄影风格',
                           '梦幻唯美风格', '童话风格',
                           '赛博朋克风格', '蒸汽朋克风格',
                           '中国水墨画风格', '工笔画风格',
                           '油画风格', '水彩画风格',
                           '动漫风格', '二次元风格',
                           '极简主义风格', '现代艺术风格',
                           '复古怀旧风格', '老照片风格',
                           '暗黑哥特风格', '末世废土风格'
                       ],
                       help='统一的艺术风格，确保整个故事视觉一致性')
    parser.add_argument('--prompt_file', default='prompts/sd_image_generator_v2.md',
                       help='SD提示词模板文件 (默认: prompts/sd_image_generator_v2.md)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 初始化生成器
        logger.info(f"🚀 初始化图片提示词生成器...")
        logger.info(f"   创作者: {args.creator}")
        logger.info(f"   视频ID: {args.video}")
        logger.info(f"   生成器类型: {args.generator_type}")
        logger.info(f"   每片段图片数: {args.images_per_segment}")
        if args.art_style:
            logger.info(f"   艺术风格: {args.art_style}")
        
        generator = ImagePromptGenerator(
            creator_name=args.creator,
            video_id=args.video,
            generator_type=args.generator_type,
            sd_prompt_file=args.prompt_file,
            images_per_segment=args.images_per_segment,
            art_style=args.art_style
        )
        
        # 根据参数决定处理哪些segment
        if args.segment:
            # 处理单个segment
            logger.info(f"📝 处理单个片段: {args.segment}")
            result = generator.generate_for_segment(args.segment)
            generator.save_results(result, single=True)
            
            # 显示统计信息
            if "prompts" in result:
                prompt_type = "即梦" if args.generator_type == 'jimeng' else "SD"
                logger.info(f"✨ 成功生成 {len(result['prompts'])} 个{prompt_type}提示词")
                logger.info(f"📁 结果已保存到: {generator.final_dir}")
            
        elif args.segments:
            # 处理指定的多个segments
            segment_ids = [int(s.strip()) for s in args.segments.split(',')]
            logger.info(f"📝 处理指定片段: {segment_ids}")
            
            results = generator.generate_for_segments(segment_ids)
            generator.save_results(results)
            
            # 显示统计信息
            total_prompts = results.get("total_prompts", 0)
            prompt_type = "即梦" if args.generator_type == 'jimeng' else "SD"
            logger.info(f"✨ 成功生成 {total_prompts} 个{prompt_type}提示词")
            logger.info(f"📁 结果已保存到: {generator.final_dir}")
            
        elif args.all:
            # 处理所有segments
            logger.info(f"📝 处理所有片段...")
            
            results = generator.generate_for_segments()
            generator.save_results(results)
            
            # 显示统计信息
            total_segments = results.get("total_segments", 0)
            total_prompts = results.get("total_prompts", 0)
            prompt_type = "即梦" if args.generator_type == 'jimeng' else "SD"
            logger.info(f"✨ 处理了 {total_segments} 个片段，生成 {total_prompts} 个{prompt_type}提示词")
            logger.info(f"📁 结果已保存到: {generator.final_dir}")
            
            # 显示错误统计
            if "segments" in results:
                errors = [k for k, v in results["segments"].items() if "error" in v]
                if errors:
                    logger.warning(f"⚠️ {len(errors)} 个片段处理失败: {errors}")
        
        logger.info("🎉 处理完成！")
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件或目录不存在: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()