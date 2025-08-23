#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一Pipeline执行脚本
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# 加载环境变量
from config_loader import load_env_file
load_env_file()

from pipeline_core import VideoPipeline
from models import PipelineRequest, Gender, TaskStatus


def validate_prerequisites():
    """验证执行先决条件"""
    missing = []
    
    # 检查必要的目录
    required_dirs = [
        Path("voice_gen"),
        Path("draft_gen"),
    ]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            missing.append(f"目录不存在: {dir_path}")
    
    # 检查必要的脚本
    required_scripts = [
        Path("story_pipeline_v3_runner.py"),
        Path("voice_gen/tts_client.py"),
        Path("draft_gen/generateDraftService.py"),
    ]
    
    for script_path in required_scripts:
        if not script_path.exists():
            missing.append(f"脚本不存在: {script_path}")
    
    return missing


def main():
    """主函数"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        description="视频创作Pipeline - 串联故事生成、语音生成、剪映草稿生成"
    )
    
    # 必需参数
    parser.add_argument(
        '--videoid',
        type=str,
        required=True,
        help='YouTube视频ID'
    )
    
    parser.add_argument(
        '--creatorid', '-c',
        type=str,
        required=True,
        help='创作者ID'
    )
    
    # 可选参数
    parser.add_argument(
        '--gender', '-g',
        type=int,
        choices=[0, 1],
        default=0,
        help='语音性别 (0=女声, 1=男声, 默认: 0)'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=120,
        help='每张图片展示时长，单位秒 (默认: 120)'
    )
    
    parser.add_argument(
        '--image_dir', '-i',
        type=str,
        help='图库目录路径 (可选)'
    )
    
    # 控制参数
    parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='仅检查先决条件，不执行'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='不使用缓存，强制重新执行所有步骤'
    )
    
    # 解析参数
    args = parser.parse_args()
    
    print("视频创作Pipeline系统 v1.0.0")
    print("="*60)
    
    # 检查先决条件
    print("检查执行环境...")
    
    missing = validate_prerequisites()
    if missing:
        print("✗ 缺失以下必要组件:")
        for item in missing:
            print(f"  - {item}")
        return 1
    
    if args.check:
        print("✓ 所有先决条件满足")
        return 0
    
    # 创建请求对象
    try:
        request = PipelineRequest(
            video_id=args.videoid,
            creator_id=args.creatorid,
            gender=Gender(args.gender),
            duration=args.duration,
            image_dir=args.image_dir
        )
    except Exception as e:
        print(f"✗ 参数验证失败: {e}")
        return 1
    
    # 显示执行参数
    print("\n执行参数:")
    print(f"  视频ID: {request.video_id}")
    print(f"  创作者: {request.creator_id}")
    print(f"  语音: {'男声' if request.gender == Gender.MALE else '女声'}")
    print(f"  图片时长: {request.duration}秒")
    if request.image_dir:
        print(f"  图库目录: {request.image_dir}")
    
    # 创建Pipeline实例
    pipeline = VideoPipeline(request, verbose=args.verbose, use_cache=not args.no_cache)
    
    # 执行Pipeline
    print("\n开始执行Pipeline...")
    print("="*60)
    
    try:
        response = pipeline.execute_sync()
        
        # 打印摘要
        print("\n" + "="*60)
        print("执行摘要")
        print("="*60)
        
        # 基本信息
        print(f"状态: {response.status.value}")
        print(f"视频ID: {response.video_id}")
        print(f"创作者: {response.creator_id}")
        
        if response.total_duration:
            minutes = int(response.total_duration // 60)
            seconds = response.total_duration % 60
            print(f"总耗时: {minutes}分{seconds:.1f}秒")
        
        # 输出文件
        print("\n输出文件:")
        if response.story_path:
            print(f"  故事文本: {response.story_path}")
        if response.audio_path:
            print(f"  音频文件: {response.audio_path}")
        if response.draft_path:
            print(f"  剪映草稿: {response.draft_path}")
        
        # 阶段执行情况
        if response.stages:
            print("\n阶段执行:")
            for stage in response.stages:
                duration_str = f"({stage.duration:.1f}秒)" if stage.duration else ""
                print(f"  {stage.name}: {stage.status.value} {duration_str}")
        
        # 错误信息
        if response.error_message:
            print(f"\n错误信息:")
            print(f"  {response.error_message}")
        
        # 返回状态码
        if response.status == TaskStatus.COMPLETED:
            print("\n✓ Pipeline执行成功!")
            return 0
        else:
            print("\n✗ Pipeline执行失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠ 用户中断执行")
        return 130
    except Exception as e:
        print(f"\n✗ 执行出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
