#!/usr/bin/env python3
"""
独立的剪映草稿生成测试脚本
可用于调试草稿生成，支持多种参数配置
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from draft_gen.generateDraftService import DraftGeneratorService


def analyze_draft(draft_path: str):
    """分析生成的草稿内容"""
    draft_content_path = Path(draft_path) / "draft_content.json"
    
    if not draft_content_path.exists():
        print(f"草稿文件不存在: {draft_content_path}")
        return
    
    with open(draft_content_path, 'r', encoding='utf-8') as f:
        draft_data = json.load(f)
    
    print("\n" + "=" * 60)
    print("草稿内容分析")
    print("=" * 60)
    
    # 文件大小
    file_size = draft_content_path.stat().st_size
    print(f"JSON文件大小: {file_size / 1024:.2f} KB")
    
    # 材料统计
    materials = draft_data.get('materials', {})
    print("\n材料统计:")
    print(f"  - 图片: {len(materials.get('images', []))} 个")
    print(f"  - 视频: {len(materials.get('videos', []))} 个")
    print(f"  - 音频: {len(materials.get('audios', []))} 个")
    print(f"  - 文字: {len(materials.get('texts', []))} 个")
    print(f"  - 特效: {len(materials.get('video_effects', []))} 个")
    print(f"  - 转场: {len(materials.get('transitions', []))} 个")
    
    # 轨道信息
    tracks = draft_data.get('tracks', [])
    print("\n轨道信息:")
    for track in tracks:
        track_type = track.get('type')
        segments = track.get('segments', [])
        print(f"  - {track_type}轨道: {len(segments)} 个片段")
        
        if track_type == 'video':
            # 统计视频轨道的材料引用
            material_ids = set(seg.get('material_id') for seg in segments)
            print(f"    引用材料数: {len(material_ids)}")
            
            # 计算总时长
            total_duration = sum(seg.get('target', {}).get('duration', 0) for seg in segments)
            print(f"    总时长: {total_duration / 1000000:.2f} 秒")
        
        elif track_type == 'text':
            # 字幕轨道信息
            print(f"    字幕片段数: {len(segments)}")
            if segments:
                # 统计字幕内容长度
                total_text_length = 0
                for seg in segments:
                    material_id = seg.get('material_id')
                    for text in materials.get('texts', []):
                        if text.get('id') == material_id:
                            content = text.get('content', '')
                            if isinstance(content, str):
                                content_dict = json.loads(content) if content else {}
                            else:
                                content_dict = content
                            text_content = content_dict.get('text', '')
                            total_text_length += len(text_content)
                print(f"    总字符数: {total_text_length}")
    
    # 画布配置
    canvas = draft_data.get('canvas_config', {})
    print(f"\n画布配置: {canvas.get('width', 0)}x{canvas.get('height', 0)} ({canvas.get('ratio', 'unknown')})")
    
    # 总时长
    duration = draft_data.get('duration', 0)
    print(f"视频总时长: {duration / 1000000:.2f} 秒")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='剪映草稿生成测试工具')
    
    # 必需参数
    parser.add_argument('--images_dir', '-i', type=str, required=True,
                       help='图片目录路径')
    parser.add_argument('--audio', '-a', type=str, required=True,
                       help='音频文件路径')
    
    # 可选参数
    parser.add_argument('--output_dir', '-o', type=str, default='./test_drafts',
                       help='输出目录路径（默认: ./test_drafts）')
    parser.add_argument('--title', '-t', type=str, default=None,
                       help='视频标题（默认: test_draft_时间戳）')
    parser.add_argument('--duration', '-d', type=float, default=60.0,
                       help='每张图片显示时长（秒，默认: 60）')
    
    # 字幕相关参数
    parser.add_argument('--srt', type=str, default=None,
                       help='字幕文件路径（不指定则不添加字幕）')
    parser.add_argument('--enable_subtitle', action='store_true',
                       help='启用字幕（会自动查找同名srt文件）')
    
    # 效果参数
    parser.add_argument('--no_transitions', action='store_true',
                       help='禁用转场效果')
    parser.add_argument('--no_effects', action='store_true',
                       help='禁用视频特效')
    parser.add_argument('--no_keyframes', action='store_true',
                       help='禁用关键帧动画')
    parser.add_argument('--scale', type=float, default=1.8,
                       help='图片缩放比例（默认: 1.8）')
    
    # 调试参数
    parser.add_argument('--seed', type=int, default=None,
                       help='随机种子（用于复现结果）')
    parser.add_argument('--analyze', action='store_true',
                       help='分析生成的草稿内容')
    parser.add_argument('--debug', action='store_true',
                       help='调试模式（减少输出内容）')
    
    # 特殊用途：使用已有的音频和图片
    parser.add_argument('--use_existing', action='store_true',
                       help='使用现有的测试数据（cid和vid）')
    parser.add_argument('--cid', type=str, default='test',
                       help='Creator ID（配合--use_existing使用）')
    parser.add_argument('--vid', type=str, default='test_video',
                       help='Video ID（配合--use_existing使用）')
    
    args = parser.parse_args()
    
    # 如果使用现有数据
    if args.use_existing:
        images_dir = f"./output/drafts/{args.cid}_{args.vid}_story/materials"
        audio_path = f"./output/{args.cid}_{args.vid}_story.mp3"
        
        # 如果没有找到，尝试其他路径
        if not Path(images_dir).exists():
            images_dir = "./output/images"
            if not Path(images_dir).exists():
                images_dir = "X:/picture_source"
        
        if not Path(audio_path).exists():
            # 查找任何可用的音频文件
            audio_files = list(Path("./output").glob("*.mp3"))
            if audio_files:
                audio_path = str(audio_files[0])
    else:
        images_dir = args.images_dir
        audio_path = args.audio
    
    # 生成标题
    if args.title:
        title = args.title
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = f"test_draft_{timestamp}"
    
    # 处理字幕
    srt_path = None
    if args.srt:
        srt_path = args.srt
    elif args.enable_subtitle:
        # 自动查找同名srt文件
        audio_stem = Path(audio_path).stem
        srt_path = Path(audio_path).parent / f"{audio_stem}.srt"
        if not srt_path.exists():
            print(f"警告：未找到字幕文件: {srt_path}")
            srt_path = None
    
    # 打印配置信息
    print("=" * 60)
    print("剪映草稿生成测试")
    print("=" * 60)
    print(f"图片目录: {images_dir}")
    print(f"音频文件: {audio_path}")
    print(f"输出目录: {args.output_dir}")
    print(f"视频标题: {title}")
    print(f"图片时长: {args.duration} 秒")
    print(f"字幕文件: {srt_path if srt_path else '不添加字幕'}")
    print(f"转场效果: {'禁用' if args.no_transitions else '启用'}")
    print(f"视频特效: {'禁用' if args.no_effects else '启用'}")
    print(f"关键帧动画: {'禁用' if args.no_keyframes else '启用'}")
    print(f"图片缩放: {args.scale}x")
    print(f"随机种子: {args.seed if args.seed else '随机'}")
    print(f"调试模式: {'是' if args.debug else '否'}")
    print("=" * 60)
    
    # 验证输入
    if not Path(images_dir).exists():
        print(f"错误：图片目录不存在: {images_dir}")
        return 1
    
    if not Path(audio_path).exists():
        print(f"错误：音频文件不存在: {audio_path}")
        return 1
    
    # 创建输出目录
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建服务实例
    service = DraftGeneratorService()
    
    try:
        print("\n开始生成草稿...")
        
        # 生成草稿
        draft_dir = service.generate_draft(
            images_dir=images_dir,
            audio_path=audio_path,
            image_duration_seconds=args.duration,
            video_title=title,
            output_dir=args.output_dir,
            srt_path=srt_path,  # 传递字幕路径
            enable_transitions=not args.no_transitions,
            enable_effects=not args.no_effects,
            enable_keyframes=not args.no_keyframes,
            image_scale=args.scale,
            random_seed=args.seed
        )
        
        print(f"\n✅ 草稿生成成功: {draft_dir}")
        
        # 如果需要分析
        if args.analyze:
            analyze_draft(draft_dir)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())