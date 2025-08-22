#!/usr/bin/env python3
"""
统一视频生成Pipeline CLI入口
串联故事二创、语音生成、剪映草稿生成三个阶段
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style

from pipeline_core import VideoPipeline
from models import PipelineRequest, TaskStatus, StageStatus

# 初始化colorama（支持Windows彩色输出）
init(autoreset=True)


def print_header():
    """打印程序头部信息"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{'视频二创统一Pipeline':^60}")
    print(f"{Fore.CYAN}{'='*60}\n")


def print_stage(stage_name: str, status: str = "开始"):
    """打印阶段信息"""
    if status == "开始":
        print(f"\n{Fore.YELLOW}▶ {stage_name} - {status}...")
    elif status == "成功":
        print(f"{Fore.GREEN}✓ {stage_name} - {status}")
    elif status == "失败":
        print(f"{Fore.RED}✗ {stage_name} - {status}")
    else:
        print(f"{Fore.BLUE}ℹ {stage_name} - {status}")


def print_progress(current: int, total: int, stage_name: str):
    """打印进度条"""
    percent = (current / total) * 100
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    print(f"\r{Fore.CYAN}进度: [{bar}] {percent:.1f}% - {stage_name}", end='', flush=True)


def format_duration(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分"


def print_summary(response, pipeline=None):
    """打印执行摘要"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}执行摘要")
    print(f"{Fore.CYAN}{'='*60}")
    
    # 基本信息
    print(f"\n{Fore.WHITE}视频ID: {response.video_id}")
    print(f"创作者ID: {response.creator_id}")
    print(f"总状态: ", end="")
    
    if response.status == TaskStatus.COMPLETED:
        print(f"{Fore.GREEN}{response.status}")
    else:
        print(f"{Fore.RED}{response.status}")
    
    print(f"总耗时: {format_duration(response.total_duration)}")
    
    # 各阶段结果
    print(f"\n{Fore.YELLOW}各阶段执行结果:")
    for i, stage in enumerate(response.stages, 1):
        status_color = Fore.GREEN if stage.status == StageStatus.SUCCESS else Fore.RED
        print(f"  {i}. {stage.name}: {status_color}{stage.status}{Style.RESET_ALL} "
              f"({format_duration(stage.duration)})")
        
        if stage.output_files:
            print(f"     生成文件:")
            for file in stage.output_files:
                print(f"       - {file}")
    
    # 生成的文件
    print(f"\n{Fore.YELLOW}主要输出文件:")
    if response.story_path:
        print(f"  📝 故事文本: {response.story_path}")
    if response.audio_path:
        print(f"  🎵 音频文件: {response.audio_path}")
    if response.draft_path:
        print(f"  📋 剪映草稿: {response.draft_path}")
    if response.video_path:
        print(f"  🎬 视频文件: {response.video_path}")
    
    # 报告信息
    if response.content_report or response.youtube_suggestions:
        print(f"\n{Fore.YELLOW}生成的报告:")
        if response.content_report:
            print(f"  📊 内容分析报告已生成")
            if response.content_report.story_theme:
                print(f"     主题: {response.content_report.story_theme}")
            if response.content_report.keywords:
                print(f"     关键词: {', '.join(response.content_report.keywords[:5])}")
        
        if response.youtube_suggestions:
            print(f"  📺 YouTube发布建议已生成")
            if response.youtube_suggestions.title:
                print(f"     标题建议: 已包含")
            if response.youtube_suggestions.tags:
                print(f"     标签数量: {len(response.youtube_suggestions.tags)}")
    
    # 错误信息
    if response.error_message:
        print(f"\n{Fore.RED}错误信息:")
        print(f"  {response.error_message}")
    
    # 日志文件提示
    if hasattr(pipeline, 'log_file'):
        print(f"\n{Fore.YELLOW}📄 详细日志:")
        print(f"  {pipeline.log_file}")
    
    print(f"\n{Fore.CYAN}{'='*60}\n")


def validate_args(args) -> list:
    """验证命令行参数"""
    errors = []
    
    # 验证视频ID格式（YouTube视频ID通常是11个字符）
    if len(args.videoid) < 10 or len(args.videoid) > 12:
        errors.append(f"视频ID格式可能不正确: {args.videoid}")
    
    # 验证性别参数
    if args.gender not in [0, 1]:
        errors.append(f"性别参数必须是0（女声）或1（男声）: {args.gender}")
    
    # 验证时长参数
    if args.duration < 1 or args.duration > 3600:
        errors.append(f"图片时长必须在1-3600秒之间: {args.duration}")
    
    # 验证图库目录
    if args.image_dir and not Path(args.image_dir).exists():
        errors.append(f"图库目录不存在: {args.image_dir}")
    
    return errors


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='统一视频生成Pipeline - 串联故事二创、语音生成、剪映草稿生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  基础用法:
    python unified_pipeline.py --videoid t54eELXWe4g --creatorid test
  
  完整参数:
    python unified_pipeline.py \\
        --videoid t54eELXWe4g \\
        --creatorid test \\
        --gender 0 \\
        --duration 120 \\
        --image_dir /path/to/images
  
  输出JSON格式:
    python unified_pipeline.py --videoid t54eELXWe4g --creatorid test --json
        """
    )
    
    # 必需参数
    parser.add_argument('--videoid', '-v', required=True, 
                       help='YouTube视频ID')
    parser.add_argument('--creatorid', '-c', required=True,
                       help='创作者ID')
    
    # 可选参数
    parser.add_argument('--gender', '-g', type=int, default=0, choices=[0, 1],
                       help='语音性别 (0=女声, 1=男声, 默认: 0)')
    parser.add_argument('--duration', '-d', type=int, default=120,
                       help='单个图片持续时长(秒, 默认: 120)')
    parser.add_argument('--image_dir', '-i', type=str, default=None,
                       help='剪映草稿图库目录路径')
    
    # 输出选项
    parser.add_argument('--json', action='store_true',
                       help='以JSON格式输出结果')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='静默模式，只输出最终结果')
    parser.add_argument('--check', action='store_true',
                       help='只检查先决条件，不执行')
    parser.add_argument('--verbose', '-V', action='store_true',
                       help='输出详细日志信息')
    
    # 高级选项
    parser.add_argument('--scripts-dir', type=str, default=None,
                       help='脚本所在目录（默认自动检测）')
    parser.add_argument('--log-file', type=str, default=None,
                       help='指定日志文件路径')
    
    args = parser.parse_args()
    
    # 验证参数
    errors = validate_args(args)
    if errors:
        print(f"{Fore.RED}参数验证失败:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # 创建请求对象
    request = PipelineRequest(
        video_id=args.videoid,
        creator_id=args.creatorid,
        gender=args.gender,
        duration=args.duration,
        image_dir=args.image_dir
    )
    
    # 创建Pipeline实例
    pipeline = VideoPipeline(
        request, 
        scripts_base_dir=args.scripts_dir,
        log_file=args.log_file,
        verbose=args.verbose
    )
    
    # 检查先决条件
    if args.check or not args.quiet:
        missing = pipeline.check_prerequisites()
        if missing:
            print(f"{Fore.RED}先决条件检查失败:")
            for item in missing:
                print(f"  - {item}")
            if args.check:
                sys.exit(1)
            else:
                print(f"\n{Fore.YELLOW}警告: 某些先决条件缺失，继续执行可能会失败")
        elif args.check:
            print(f"{Fore.GREEN}所有先决条件检查通过")
            sys.exit(0)
    
    if not args.quiet and not args.json:
        print_header()
        print(f"{Fore.WHITE}配置信息:")
        print(f"  视频ID: {args.videoid}")
        print(f"  创作者ID: {args.creatorid}")
        print(f"  语音性别: {'女声' if args.gender == 0 else '男声'}")
        print(f"  图片时长: {args.duration}秒")
        if args.image_dir:
            print(f"  图库目录: {args.image_dir}")
        print()
    
    try:
        # 执行Pipeline
        if not args.quiet and not args.json:
            print(f"{Fore.CYAN}开始执行Pipeline...")
            print(f"{Fore.CYAN}{'='*60}")
        
        response = pipeline.execute_sync()
        
        # 输出结果
        if args.json:
            # JSON格式输出
            print(json.dumps(response.dict(), indent=2, ensure_ascii=False, default=str))
        elif not args.quiet:
            # 标准格式输出
            print_summary(response, pipeline)
        else:
            # 静默模式只输出状态
            if response.status == TaskStatus.COMPLETED:
                print(f"{Fore.GREEN}SUCCESS")
                sys.exit(0)
            else:
                print(f"{Fore.RED}FAILED: {response.error_message}")
                sys.exit(1)
        
        # 设置退出码
        sys.exit(0 if response.status == TaskStatus.COMPLETED else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断执行")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}执行出错: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()