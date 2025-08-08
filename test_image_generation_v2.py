#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试优化版图片生成流程
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from youtube_story_creator_v2 import YouTubeStoryCreatorV2

def test_character_extraction():
    """测试角色特征提取"""
    print("=" * 80)
    print("测试角色特征提取")
    print("=" * 80)
    
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        images_per_segment=2
    )
    
    # 测试框架文本
    test_framework = """
## C. 核心角色视觉设计 (Midjourney/SD友好)
- **角色1：[艾拉]**
  - **身份定位：** 25岁的女性程序员
  - **性别/年龄感/体型等：** 女性，25岁，瘦弱，长发
  - **"槽点"的视觉表现：** 总是带着天真的微笑，眼神过于纯洁

- **角色2：[凯尔]**
  - **身份定位：** 30岁的男性创业者
  - **性别/年龄感/体型等：** 男性，30岁，健壮
  - **"槽点"的视觉表现：** 自信的笑容显得有些傲慢
"""
    
    profiles = creator.extract_character_profiles(test_framework)
    
    print("\n提取到的角色特征：")
    for name, profile in profiles.items():
        print(f"\n角色: {name}")
        print(f"  - 视觉描述: {profile.get('visual_description', '')}")
        print(f"  - SD特征: {profile.get('sd_features', '')}")
    
    print("\n[OK] 角色特征提取测试完成")

def test_scene_extraction():
    """测试场景提取"""
    print("\n" + "=" * 80)
    print("测试场景提取")
    print("=" * 80)
    
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        images_per_segment=3
    )
    
    # 测试片段内容
    test_segment = """
    艾拉站在雨中，看着远处的城市灯火。她的白色连衣裙已经被雨水打湿，
    但她似乎毫不在意。她的眼神中充满了坚定，尽管刚刚失去了工作，
    但她相信明天会更好。
    
    突然，一辆黑色轿车停在她身边。车窗摇下，露出凯尔熟悉的面容。
    "上车吧，"他说，"我们需要谈谈。"
    
    艾拉犹豫了一下，最终还是打开了车门。车内温暖的空气和皮革的味道
    让她感到一丝安慰。她看着凯尔，等待他开口。
    """
    
    scenes = creator.extract_key_scenes_from_segment(test_segment, 1, 2)
    
    print("\n提取到的场景：")
    for idx, scene in enumerate(scenes, 1):
        print(f"\n场景 {idx}:")
        print(f"  描述: {scene.get('description', '')}")
        print(f"  情感: {scene.get('emotion', '')}")
        print(f"  关键元素: {scene.get('key_elements', [])}")
        print(f"  色调: {scene.get('color_mood', '')}")
    
    print("\n[OK] 场景提取测试完成")

def test_sd_prompt_generation():
    """测试SD提示词生成"""
    print("\n" + "=" * 80)
    print("测试SD提示词生成")
    print("=" * 80)
    
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        images_per_segment=1
    )
    
    # 测试数据
    character_profiles = {
        "艾拉": {
            "name": "艾拉",
            "visual_description": "25岁女性，长发，瘦弱",
            "sd_features": "young adult, female, long hair"
        }
    }
    
    scene = {
        "description": "女孩站在雨中看着城市",
        "emotion": "melancholic",
        "key_elements": ["rain", "city lights", "white dress"],
        "color_mood": "blue and grey"
    }
    
    sd_prompt = creator.generate_sd_prompt_for_scene(
        scene, character_profiles, 1, 1
    )
    
    print("\n生成的SD提示词：")
    print(f"正面提示词：\n{sd_prompt['positive']}")
    print(f"\n负面提示词：\n{sd_prompt['negative']}")
    
    print("\n[OK] SD提示词生成测试完成")

def test_complete_flow():
    """测试完整流程（使用模拟数据）"""
    print("\n" + "=" * 80)
    print("测试完整图片生成流程")
    print("=" * 80)
    
    # 创建测试数据目录
    test_dir = Path("story_result/test_creator/test_video")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    processing_dir = test_dir / "processing"
    segments_dir = test_dir / "segments"
    final_dir = test_dir / "final"
    
    for d in [processing_dir, segments_dir, final_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 创建模拟框架文件
    framework_file = processing_dir / "2_framework.txt"
    with open(framework_file, 'w', encoding='utf-8') as f:
        f.write("""
## C. 核心角色视觉设计
- **角色1：[艾拉]**
  - **身份定位：** 主角
  - **性别/年龄感/体型等：** 女性，25岁，瘦弱，长发
""")
    
    # 创建模拟片段文件
    for i in range(1, 4):
        segment_file = segments_dir / f"segment_{i:02d}.txt"
        with open(segment_file, 'w', encoding='utf-8') as f:
            f.write(f"这是第{i}段的内容。主角艾拉正在经历一场冒险...")
    
    # 运行测试
    creator = YouTubeStoryCreatorV2(
        video_id="test_video",
        creator_name="test_creator",
        images_per_segment=2
    )
    
    success = creator.generate_image_prompts_v2()
    
    if success:
        print("\n✅ 图片生成流程测试成功！")
        
        # 检查输出文件
        json_file = final_dir / "sd_prompts_v2.json"
        md_file = final_dir / "sd_prompts_v2.md"
        
        if json_file.exists():
            print(f"  - JSON文件已生成: {json_file}")
        if md_file.exists():
            print(f"  - Markdown文件已生成: {md_file}")
    else:
        print("\n❌ 图片生成流程测试失败")
    
    print("\n[OK] 完整流程测试完成")

def main():
    """主测试函数"""
    print("开始测试优化版图片生成流程")
    
    # 运行各项测试
    test_character_extraction()
    test_scene_extraction()
    test_sd_prompt_generation()
    test_complete_flow()
    
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)
    
    print("\n使用提示：")
    print("1. 新的图片生成使用 generate_image_prompts_v2()")
    print("2. 支持从框架提取角色特征，保持视觉一致性")
    print("3. 每个片段可生成多张图片（通过 --images-per-segment 参数控制）")
    print("4. 输出包含JSON和Markdown两种格式")

if __name__ == "__main__":
    main()