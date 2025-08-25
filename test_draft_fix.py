#!/usr/bin/env python3
"""
测试剪映草稿生成问题修复
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from draft_gen.generateDraftService import DraftGeneratorService

def test_draft_generation():
    """测试草稿生成"""
    print("=" * 60)
    print("测试剪映草稿生成")
    print("=" * 60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 准备测试数据
        images_dir = Path("output/drafts/test_P3hKojLuG1c_story/materials")
        audio_path = Path("output/test_P3hKojLuG1c_story.mp3")
        output_dir = Path(temp_dir) / "test_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查测试文件是否存在
        if not images_dir.exists():
            print(f"错误：图片目录不存在: {images_dir}")
            # 尝试其他可能的路径
            images_dir = Path("X:/picture_source")
            if not images_dir.exists():
                print(f"错误：备选图片目录也不存在: {images_dir}")
                return
        
        if not audio_path.exists():
            print(f"错误：音频文件不存在: {audio_path}")
            # 尝试查找任何可用的音频文件
            audio_files = list(Path("output").glob("*.mp3"))
            if audio_files:
                audio_path = audio_files[0]
                print(f"使用备选音频文件: {audio_path}")
            else:
                print("错误：找不到任何音频文件")
                return
        
        print(f"图片目录: {images_dir}")
        print(f"音频文件: {audio_path}")
        print(f"输出目录: {output_dir}")
        
        # 创建服务实例
        service = DraftGeneratorService()
        
        # 生成草稿（测试两次以验证是否有累积问题）
        for i in range(2):
            print(f"\n--- 第 {i+1} 次生成 ---")
            
            try:
                draft_dir = service.generate_draft(
                    images_dir=str(images_dir),
                    audio_path=str(audio_path),
                    image_duration_seconds=60.0,
                    video_title=f"test_draft_{i+1}",
                    output_dir=str(output_dir),
                    enable_transitions=True,
                    enable_effects=True,
                    enable_keyframes=True,
                    random_seed=42  # 使用固定种子以便重现
                )
                
                print(f"草稿生成成功: {draft_dir}")
                
                # 检查生成的草稿内容
                draft_content_path = Path(draft_dir) / "draft_content.json"
                if draft_content_path.exists():
                    with open(draft_content_path, 'r', encoding='utf-8') as f:
                        draft_data = json.load(f)
                    
                    # 分析草稿内容
                    print("\n草稿分析:")
                    
                    # 检查材料
                    materials = draft_data.get('materials', {})
                    print(f"  图片数量: {len(materials.get('images', []))}")
                    print(f"  视频数量: {len(materials.get('videos', []))}")
                    print(f"  音频数量: {len(materials.get('audios', []))}")
                    print(f"  特效数量: {len(materials.get('video_effects', []))}")
                    print(f"  转场数量: {len(materials.get('transitions', []))}")
                    
                    # 检查轨道
                    tracks = draft_data.get('tracks', [])
                    for track in tracks:
                        track_type = track.get('type')
                        segments = track.get('segments', [])
                        print(f"  {track_type}轨道: {len(segments)} 个片段")
                        
                        # 如果是视频轨道，检查每个片段引用的材料
                        if track_type == 'video' and segments:
                            material_ids = set()
                            for seg in segments:
                                material_ids.add(seg.get('material_id'))
                            print(f"    引用了 {len(material_ids)} 个不同的材料")
                            
                            # 检查时间覆盖
                            total_time = 0
                            for seg in segments:
                                target = seg.get('target', {})
                                duration = target.get('duration', 0)
                                total_time += duration
                            print(f"    总时长: {total_time / 1000000:.2f} 秒")
                    
                    # 检查特效是否重复
                    if len(materials.get('video_effects', [])) > 1:
                        print("\n⚠️ 警告：发现多个特效，可能存在累积问题！")
                    
                    # 检查图片是否正确加载
                    image_count = len(materials.get('images', []))
                    video_segment_count = sum(1 for t in tracks if t.get('type') == 'video' for _ in t.get('segments', []))
                    if image_count < video_segment_count:
                        print(f"\n⚠️ 警告：图片数量({image_count})少于视频片段数量({video_segment_count})！")
                
            except Exception as e:
                print(f"生成失败: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    test_draft_generation()